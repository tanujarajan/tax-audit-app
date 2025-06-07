# utils/GUI.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import pandas as pd
import os
import queue
import threading
import matplotlib
# from utils.report_generation import generate_profile_report
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import tkinter as tk
from tkinter import ttk

class ScrollableFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.canvas = tk.Canvas(self)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollable_frame = ttk.Frame(self.canvas)

        # Configure scrollregion when the frame changes size
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Store the window item
        self.window_item = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind("<Enter>", lambda e: self.canvas.focus_set())
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)  # For Linux
        self.canvas.bind("<Button-5>", self._on_mousewheel)  # For Linux

        # Bind canvas configure event to adjust the width of scrollable_frame
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event):
        # When the canvas is resized, update the width of the scrollable_frame
        canvas_width = event.width
        # Set the itemconfig to match the canvas width
        self.canvas.itemconfig(self.window_item, width=canvas_width)

    def _on_mousewheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")
        else:
            if event.num == 4: 
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")


class Application:
    def __init__(self, root):
        self.root = root
        root.title("Event Data Processing Application")
        root.geometry("900x800")

        # Create the scrollable frame and pack it
        self.scrollable_frame = ScrollableFrame(root)
        self.scrollable_frame.pack(fill="both", expand=True)

        # Use the scrollable frame's inner frame to add widgets
        self.main_frame = self.scrollable_frame.scrollable_frame

        # Initialize variables
        self.output_dir = tk.StringVar()
        self.usage_file = tk.StringVar()
        self.usage_data = None
        self.workspace_names = []
        self.selected_workspaces = []
        self.project_names = []
        self.selected_projects = []
        self.event_files = {}
        self.user_props_files = {}
        self.threshold = 90  # Default threshold value
        self.lookback_window = tk.StringVar(value="30")  # Default to 30-day look-back window

        # Progress Bar Variable
        self.progress = tk.DoubleVar()  # Variable to hold progress value

        self.processing_queue = None  # Will be set by main.py

        # Create widgets inside self.main_frame
        self.create_widgets()
    
    def set_processing_queue(self, processing_queue):
        self.processing_queue = processing_queue

    def create_widgets(self):
        # Frame for Output Directory Selection
        output_frame = ttk.LabelFrame(self.main_frame, text="1. Select Output Directory")
        output_frame.pack(fill="both", expand=True, padx=10, pady=5)

        output_dir_entry = ttk.Entry(output_frame, textvariable=self.output_dir, state='readonly')
        output_dir_entry.pack(side="left", padx=5, pady=5, expand=True, fill='x')

        browse_output_btn = ttk.Button(output_frame, text="Browse", command=self.browse_output_directory)
        browse_output_btn.pack(side="left", padx=5, pady=5)
        
        # Frame for Usage Report File Selection
        usage_frame = ttk.LabelFrame(self.main_frame, text="2. Select Usage Report File")
        usage_frame.pack(fill="x", expand=True, padx=10, pady=5)

        usage_file_entry = ttk.Entry(usage_frame, textvariable=self.usage_file, state='readonly')
        usage_file_entry.pack(side="left", padx=5, pady=5, expand=True, fill='x')

        browse_usage_btn = ttk.Button(usage_frame, text="Browse", command=self.browse_usage_file)
        browse_usage_btn.pack(side="left", padx=5, pady=5)
        
        # Frame for Workspace Selection
        workspace_frame = ttk.LabelFrame(self.main_frame, text="3. Select Workspace(s)")
        workspace_frame.pack(fill="x", expand=True, padx=10, pady=5)
        
        # Scrollable Listbox for Multi-Select Workspaces
        self.workspace_listbox = tk.Listbox(workspace_frame, selectmode="multiple", height=5)
        self.workspace_listbox.pack(side="left", padx=5, pady=5, fill='both', expand=True)
        
        workspace_scrollbar = ttk.Scrollbar(workspace_frame, orient="vertical", command=self.workspace_listbox.yview)
        workspace_scrollbar.pack(side="left", fill="y")
        self.workspace_listbox.config(yscrollcommand=workspace_scrollbar.set)
        
        # Button to confirm workspace selection
        confirm_workspaces_btn = ttk.Button(workspace_frame, text="Confirm Selection", command=self.confirm_workspace_selection)
        confirm_workspaces_btn.pack(side="left", padx=5, pady=5)
        
        # Frame for Project Selection
        project_frame = ttk.LabelFrame(self.main_frame, text="4. Select Project(s)")
        project_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.project_listbox = tk.Listbox(project_frame, selectmode="multiple", height=10)
        self.project_listbox.pack(side="left", padx=5, pady=5, fill='both', expand=True)
        
        project_scrollbar = ttk.Scrollbar(project_frame, orient="vertical", command=self.project_listbox.yview)
        project_scrollbar.pack(side="left", fill="y")
        self.project_listbox.config(yscrollcommand=project_scrollbar.set)
        
        # Button to confirm project selection
        confirm_projects_btn = ttk.Button(project_frame, text="Confirm Selection", command=self.confirm_project_selection)
        confirm_projects_btn.pack(side="left", padx=5, pady=5)
        
        # Frame for Look-Back Window Selection
        lookback_frame = ttk.LabelFrame(self.main_frame, text="Select Look-Back Window for Event Analysis")
        lookback_frame.pack(fill="x", expand=True, padx=10, pady=5)

        self.lookback_window = tk.StringVar(value="30")  # Default to 30 days

        lookback_label = ttk.Label(lookback_frame, text="Look-Back Window (Days):")
        lookback_label.pack(side="left", padx=5, pady=5)

        lookback_dropdown = ttk.Combobox(
            lookback_frame,
            textvariable=self.lookback_window,
            values=["30", "90", "180", "270", "365"],
            state="readonly"
        )
        lookback_dropdown.pack(side="left", padx=5, pady=5)
        lookback_dropdown.current(0)  # Set default to 30 days

        # Frame for Threshold Selection
        threshold_frame = ttk.LabelFrame(self.main_frame, text="5. Set Matching Threshold")
        threshold_frame.pack(fill="x", expand=True, padx=10, pady=5)
        
        # Threshold Label
        self.threshold_label = ttk.Label(threshold_frame, text=f"Threshold: {self.threshold}")
        self.threshold_label.pack(pady=5)
        
        # Explanation Label
        self.explanation_label = ttk.Label(threshold_frame, text=self.get_explanation(self.threshold), wraplength=800)
        self.explanation_label.pack(pady=5)
        
        # Slider
        self.slider = ttk.Scale(
            threshold_frame,
            from_=0,
            to=100,
            orient='horizontal',
            command=self.on_threshold_change
        )
        self.slider.set(self.threshold)
        self.slider.pack(fill='both', padx=10, pady=10)
        
        # Confirm Button
        confirm_threshold_btn = ttk.Button(threshold_frame, text="Confirm Threshold", command=self.confirm_threshold)
        confirm_threshold_btn.pack(pady=5)
        
        # Frame for Event and User Properties File Selection
        event_files_container = ttk.LabelFrame(self.main_frame, text="6. Select Event and User Properties File(s) for Each Project")
        event_files_container.pack(fill="both", padx=10, pady=5, expand=True)

        self.event_files_frame = ScrollableFrame(event_files_container)
        self.event_files_frame.pack(fill="both", expand=True)

        # Frame for Start Processing Button and Progress Bar
        start_frame = ttk.Frame(self.main_frame)
        start_frame.pack(fill="x", expand=True, padx=10, pady=10)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(start_frame, variable=self.progress, maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=5)

        # Start Processing Button
        self.start_btn = ttk.Button(start_frame, text="Start Processing", command=self.start_processing)
        self.start_btn.pack(side="right", padx=5)
    
    def browse_output_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir.set(directory)
            messagebox.showinfo("Output Directory Selected", f"Output directory set to:\n{directory}")
    
    def browse_usage_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Usage Report CSV File",
            filetypes=[("CSV Files", "*.csv")]
        )
        if file_path:
            self.usage_file.set(file_path)
            try:
                self.usage_data = pd.read_csv(file_path, parse_dates=['First Seen', 'Last Seen'])
                self.populate_workspaces()
                messagebox.showinfo("Usage Report Loaded", "Usage report loaded successfully.")
            except Exception as e:
                messagebox.showerror("Error Loading CSV", f"An error occurred while loading the usage report:\n{e}")
    
    def populate_workspaces(self):
        if self.usage_data is not None:
            self.workspace_names = self.usage_data['Workspace Name'].dropna().unique().tolist()
            self.workspace_listbox.delete(0, tk.END)
            for workspace in self.workspace_names:
                self.workspace_listbox.insert(tk.END, workspace)
            if self.workspace_names:
                # Optionally, select all by default
                for i in range(len(self.workspace_names)):
                    self.workspace_listbox.select_set(i)
                messagebox.showinfo("Workspace Selection", "All workspaces have been selected by default. You can modify your selection.")
        else:
            self.workspace_listbox.delete(0, tk.END)
    
    def confirm_workspace_selection(self):
        selected_indices = self.workspace_listbox.curselection()
        self.selected_workspaces = [self.workspace_listbox.get(i) for i in selected_indices]
        
        # Clear project listbox
        self.project_listbox.delete(0, tk.END)
        
        if not self.selected_workspaces:
            messagebox.showwarning("No Workspaces Selected", "Please select at least one workspace.")
            return
        
        # Aggregate projects from all selected workspaces
        projects = self.usage_data[self.usage_data['Workspace Name'].isin(self.selected_workspaces)]['Project Name'].dropna().unique().tolist()
        self.project_listbox.delete(0, tk.END)
        for project in projects:
            self.project_listbox.insert(tk.END, project)
        messagebox.showinfo("Project List Updated", f"Projects from selected workspace(s) have been loaded.")
    
    def confirm_project_selection(self):
        selected_indices = self.project_listbox.curselection()
        self.selected_projects = [self.project_listbox.get(i) for i in selected_indices]
        
        # Clear any existing event and user properties file selectors
        for widget in self.event_files_frame.scrollable_frame.winfo_children():
            widget.destroy()
        
        if not self.selected_projects:
            messagebox.showwarning("No Projects Selected", "Please select at least one project.")
            return
        
        # Create file selectors for each selected project
        for project in self.selected_projects:
            frame = ttk.Frame(self.event_files_frame.scrollable_frame)
            frame.pack(fill="both", expand=True, padx=5, pady=2)
            
            # Event File Selector
            event_label = ttk.Label(frame, text=f"{project} - Event File")
            event_label.grid(row=0, column=0, padx=5, pady=2, sticky='ew')
            
            event_file_var = tk.StringVar()
            event_entry = ttk.Entry(frame, textvariable=event_file_var, state='readonly')
            event_entry.grid(row=0, column=1, padx=5, pady=2, sticky='ew')
            
            event_browse_btn = ttk.Button(frame, text="Browse", command=lambda p=project, v=event_file_var: self.browse_event_file(p, v))
            event_browse_btn.grid(row=0, column=2, padx=5, pady=2)
            
            # User Properties File Selector
            user_props_label = ttk.Label(frame, text=f"{project} - User Properties File")
            user_props_label.grid(row=1, column=0, padx=5, pady=2, sticky='ew')
            
            user_props_file_var = tk.StringVar()
            user_props_entry = ttk.Entry(frame, textvariable=user_props_file_var, state='readonly')
            user_props_entry.grid(row=1, column=1, padx=5, pady=2, sticky='ew')
            
            user_props_browse_btn = ttk.Button(frame, text="Browse", command=lambda p=project, v=user_props_file_var: self.browse_user_props_file(p, v))
            user_props_browse_btn.grid(row=1, column=2, padx=5, pady=2)
            
            # Configure grid weights
            frame.columnconfigure(1, weight=1)

    
    def browse_event_file(self, project, event_file_var):
        file_path = filedialog.askopenfilename(
            title=f"Select Event File for {project}",
            filetypes=[("CSV Files", "*.csv")]
        )
        if file_path:
            event_file_var.set(file_path)
            self.event_files[project] = file_path
            messagebox.showinfo("Event File Selected", f"Event file for '{project}' set to:\n{file_path}")
    
    def browse_user_props_file(self, project, user_props_file_var):
        file_path = filedialog.askopenfilename(
            title=f"Select User Properties File for {project}",
            filetypes=[("CSV Files", "*.csv")]
        )
        if file_path:
            user_props_file_var.set(file_path)
            self.user_props_files[project] = file_path
            messagebox.showinfo(
                "User Properties File Selected",
                f"User Properties file for '{project}' set to:\n{file_path}"
            )
    
    def get_explanation(self, value):
        if value >= 85:
            return "Good results for close to exact matches."
        elif value >= 70:
            return "Use for moderate matches and grouping opportunities."
        else:
            return "Use lower values for higher verbosity or consolidation opportunities."
    
    def on_threshold_change(self, value):
        value = int(float(value))
        self.threshold_label.config(text=f"Threshold: {value}")
        self.explanation_label.config(text=self.get_explanation(value))
    
    def confirm_threshold(self):
        self.threshold = int(float(self.slider.get()))
        messagebox.showinfo("Threshold Confirmed", f"Threshold set to: {self.threshold}")
    
    def update_progress(self, value):
        # Update the progress variable
        self.progress.set(value)
        # Optional: Force the GUI to update the progress bar immediately
        self.root.update_idletasks()
    
    def start_processing(self):
        # Validate all selections
        if not self.output_dir.get():
            messagebox.showwarning("Output Directory Missing", "Please select an output directory.")
            return
        
        if not self.usage_file.get():
            messagebox.showwarning("Usage Report Missing", "Please select a usage report CSV file.")
            return
        
        if not self.selected_workspaces:
            messagebox.showwarning("No Workspaces Selected", "Please select at least one workspace.")
            return
        
        if not self.selected_projects:
            messagebox.showwarning("No Projects Selected", "Please select at least one project.")
            return
        
        missing_event_files = [proj for proj in self.selected_projects if proj not in self.event_files]
        if missing_event_files:
            messagebox.showwarning("Missing Event Files", f"Please select event files for the following projects:\n{', '.join(missing_event_files)}")
            return

        missing_user_props_files = [proj for proj in self.selected_projects if proj not in self.user_props_files]
        if missing_user_props_files:
            messagebox.showwarning("Missing User Properties Files", f"Please select user properties files for the following projects:\n{', '.join(missing_user_props_files)}")
            return

        # Reset the progress bar
        self.progress.set(0)

        # Disable the Start Processing button
        self.start_btn.config(state='disabled')

        # Prepare parameters for data processing
        params = {
            'threshold': self.threshold,
            'lookback_window': int(self.lookback_window.get()),  # Lookback window for analysis
            'usage_file': self.usage_file.get(),  # Ensure the usage report file is passed
            'event_files': self.event_files,
            'user_props_files': self.user_props_files,
            'selected_workspaces': self.selected_workspaces,
            'selected_projects': self.selected_projects,
            'output_dir': self.output_dir.get()
        }

        # Send a message to the processing queue to start processing
        self.processing_queue.put({'type': 'start_processing', 'params': params})


    def update_results(self, results):
        # Re-enable the Start Processing button
        self.start_btn.config(state='normal')

        counts_dfs = results.get('counts_dfs', {})
        event_props_counts = results.get('event_props_counts', {})
        user_props_counts = results.get('user_props_counts', {})
        event_names = results.get('event_names', {})
        dedup_dfs = results.get('dedup_dfs', {})
        user_props_data = results.get('user_props_data', {})
        params = results.get('params', {})
        output_dir = params.get('output_dir', '')

        # Define the columns for each profile type
        event_name_cols = [
            'Object Type',
            'Object Name',
            'Event Display Name',
            'Object Owner',
            'Object Description',
            'Event Category',
            'Tags',
            'Event Schema Status',
            'Event Activity',
            'Event Source'
        ]

        event_props_cols = [
            'Property Type',
            'Property Group Names',
            'Property Description',
            'Property Value Type',
            'Property Schema Status',
            'Property Required',
            'Property Is Array',
            'Property First Seen',
            'Property Last Seen'
        ]

        user_props_cols = [
            'Property Type',
            'Property Name',
            'Property Description',
            'Property Value Type',
            'Property Schema Status',
            'Property First Seen',
            'Property Last Seen'
        ]

        # Generate three profile reports per project, if data is available
        for project in event_names.keys():
            project_output_dir = os.path.join(output_dir, project)

            # Removing the following functionality for now as it is causing too many errors, will work on bringing back soem of this functionality in a future itiration
            # # 1) Events Data Profile
            # events_df = event_names[project].copy()
            # events_df = events_df[event_name_cols]
            # events_data_profile_path = os.path.join(project_output_dir, f"{project}_events_data_profile.html")
            # generate_profile_report(events_df, events_data_profile_path)

            # # 2) Event Properties Data Profile
            # if project in dedup_dfs:
            #     dedup_df = dedup_dfs[project].copy()
            #     # Filter down to the defined columns for event properties
            #     dedup_df = dedup_df[event_props_cols]
            #     event_properties_data_profile_path = os.path.join(project_output_dir, f"{project}_event_properties_data_profile.html")
            #     generate_profile_report(dedup_df, event_properties_data_profile_path)

            # # 3) User Properties Data Profile
            # if project in user_props_data and not user_props_data[project].empty:
            #     user_props_df = user_props_data[project].copy()
            #     user_props_df = user_props_df[user_props_cols]
            #     user_properties_data_profile_path = os.path.join(project_output_dir, f"{project}_user_properties_data_profile.html")
            #     generate_profile_report(user_props_df, user_properties_data_profile_path)

        # Proceed with the existing logic to show results in the GUI
        if not counts_dfs and not event_props_counts and not user_props_counts:
            messagebox.showinfo("Processing Complete", "Data processing is complete. No results to display.")
            return

        if hasattr(self, 'results_window') and self.results_window.winfo_exists():
            self.results_window.destroy()

        self.results_window = tk.Toplevel(self.root)
        self.results_window.title("Processed Results")
        self.results_window.geometry("900x600")
        self.center_window(self.results_window, 900, 600)

        main_notebook = ttk.Notebook(self.results_window)
        main_notebook.pack(fill="both", expand=True)

        # 1) Events Tab
        events_tab = ttk.Frame(main_notebook)
        main_notebook.add(events_tab, text="Events")

        if counts_dfs:
            events_notebook = ttk.Notebook(events_tab)
            events_notebook.pack(fill="both", expand=True)
            for project, cdf in counts_dfs.items():
                pframe = ttk.Frame(events_notebook)
                events_notebook.add(pframe, text=project)
                self.create_counts_table(pframe, cdf)
                self.create_counts_chart(pframe, cdf, project, status_column='Event Schema Status')
        else:
            tk.Label(events_tab, text="No Events data available").pack()

        # 2) Event Properties Tab
        event_props_tab = ttk.Frame(main_notebook)
        main_notebook.add(event_props_tab, text="Event Properties")

        if event_props_counts:
            ep_notebook = ttk.Notebook(event_props_tab)
            ep_notebook.pack(fill="both", expand=True)
            for project, epcdf in event_props_counts.items():
                pframe = ttk.Frame(ep_notebook)
                ep_notebook.add(pframe, text=project)
                self.create_counts_table(pframe, epcdf)
                self.create_counts_chart(pframe, epcdf, project, status_column='Property Schema Status')
        else:
            tk.Label(event_props_tab, text="No Event Properties data available").pack()

        # 3) User Properties Tab
        user_props_tab = ttk.Frame(main_notebook)
        main_notebook.add(user_props_tab, text="User Properties")

        if user_props_counts:
            up_notebook = ttk.Notebook(user_props_tab)
            up_notebook.pack(fill="both", expand=True)
            for project, upcdf in user_props_counts.items():
                pframe = ttk.Frame(up_notebook)
                up_notebook.add(pframe, text=project)
                self.create_counts_table(pframe, upcdf)
                self.create_counts_chart(pframe, upcdf, project, status_column='Property Schema Status')
        else:
            tk.Label(user_props_tab, text="No User Properties data available").pack()

        # Word Clouds Tab
        wordcloud_tab = ttk.Frame(main_notebook)
        main_notebook.add(wordcloud_tab, text="Word Clouds")

        wc_notebook = ttk.Notebook(wordcloud_tab)
        wc_notebook.pack(fill="both", expand=True)

        for project in event_names.keys():
            project_frame = ttk.Frame(wc_notebook)
            wc_notebook.add(project_frame, text=project)
            
            # Create a ScrollableFrame inside the project tab
            project_scrollable = ScrollableFrame(project_frame)
            project_scrollable.pack(fill="both", expand=True)
            
            # Project output directory
            project_output_dir = os.path.join(output_dir, project)

            wc_files = [
                ("Event Display Name", "wordclouds/events_display_name_wordcloud.png"),
                # ("Event Description", "wordclouds/events_description_wordcloud.png"),
                ("Event Property Name", "wordclouds/event_props_name_wordcloud.png"),
                # ("Event Property Description", "wordclouds/event_props_description_wordcloud.png"),
                ("User Property Name", "wordclouds/user_props_name_wordcloud.png")
                # ("User Property Description", "wordclouds/user_props_description_wordcloud.png")
            ]

            for title, wc_file in wc_files:
                wc_path = os.path.join(project_output_dir, wc_file)
                img_frame = ttk.Labelframe(project_scrollable.scrollable_frame, text=title)
                img_frame.pack(fill="x", padx=10, pady=10)  # Stacks vertically
                
                if os.path.exists(wc_path):
                    img = Image.open(wc_path)
                    tk_img = ImageTk.PhotoImage(img)

                    img_label = ttk.Label(img_frame, image=tk_img)
                    img_label.image = tk_img  # Keep a reference to prevent garbage collection
                    img_label.pack(fill="both", expand=True)
                else:
                    ttk.Label(img_frame, text="No wordcloud generated").pack(fill="x", padx=5, pady=5)

        messagebox.showinfo("Processing Complete", "Data processing is complete. Results are displayed in a new window.")


    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')


    def export_results(self, counts_dfs):
        """
        Exports the combined counts DataFrames to a CSV or Excel file.
        
        Parameters:
        - counts_dfs: A dictionary containing counts DataFrames for each project.
        """
        # Ask user to select a directory and filename
        file_path = filedialog.asksaveasfilename(
            title="Save Results As",
            defaultextension='.csv',
            filetypes=[('CSV files', '*.csv'), ('Excel files', '*.xlsx')]
        )
        if file_path:
            # Combine all counts_dfs into a single DataFrame
            combined_df = pd.concat(counts_dfs.values(), keys=counts_dfs.keys(), names=['Project'])
            # Reset index to make 'Project' a column
            combined_df = combined_df.reset_index(level='Project').reset_index(drop=True)
            # Check the file extension to determine the format
            if file_path.endswith('.csv'):
                combined_df.to_csv(file_path, index=False)
            elif file_path.endswith('.xlsx'):
                combined_df.to_excel(file_path, index=False)
            else:
                messagebox.showerror("Invalid File Extension", "Please select a .csv or .xlsx file extension.")
                return
            messagebox.showinfo("Export Successful", f"Results exported to {file_path}")

    
    def create_counts_table(self, parent_frame, counts_df):
        # Create Treeview
        tree_frame = ttk.Frame(parent_frame)
        tree_frame.pack(side='left', fill='both', expand=True)

        columns = counts_df.columns.tolist()
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=10)

        # Format percentage values only once if present
        if 'Percentage' in counts_df.columns:
            # Ensure Percentage is numeric, if not, convert it
            if counts_df['Percentage'].dtype == object:
                # Try converting string percentages back to float if needed
                counts_df['Percentage'] = pd.to_numeric(counts_df['Percentage'], errors='coerce')
            counts_df['Percentage'] = counts_df['Percentage'].map("{:.2f}%".format)

        # Define headings and columns
        for col in columns:
            tree.heading(col, text=col, command=lambda _col=col: self.sort_column(tree, _col, False))
            if col in ['Counts', 'Percentage']:
                tree.column(col, width=100, anchor='e')
            else:
                tree.column(col, width=150, anchor='w')

        # Insert data into Treeview with alternating row colors
        for index, row in counts_df.iterrows():
            values = [row[col] for col in columns]
            tag = 'evenrow' if index % 2 == 0 else 'oddrow'
            tree.insert('', tk.END, values=values, tags=(tag,))

        # Define styles for tags
        tree.tag_configure('evenrow', background='lightgray')
        tree.tag_configure('oddrow', background='white')

        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)

    def sort_column(self, tree, col, reverse):
        # Get all values in the column
        data_list = [(tree.set(child, col), child) for child in tree.get_children('')]

        # Try to convert data to float for numerical sorting
        try:
            data_list = [(float(item[0].replace('%', '')), item[1]) for item in data_list]
        except ValueError:
            pass  # Keep data as strings if conversion fails

        # Sort data
        data_list.sort(reverse=reverse)

        # Rearrange items in the treeview
        for index, (val, child) in enumerate(data_list):
            tree.move(child, '', index)

        # Reverse sort next time
        tree.heading(col, command=lambda: self.sort_column(tree, col, not reverse))

    def create_counts_chart(self, parent_frame, counts_df, project_name, status_column='Event Schema Status'):
        """
        Creates a bar chart displaying counts for a given project and status column.

        Parameters:
        - parent_frame: The Tkinter frame where the chart will be embedded.
        - counts_df (pd.DataFrame): A DataFrame containing 'Counts' and a status column 
        (either 'Event Schema Status' or 'Property Schema Status').
        - project_name (str): The name of the project (used in the chart title).
        - status_column (str): The column name used for the x-axis categories. 
        Default is 'Event Schema Status', but can be 'Property Schema Status' for properties.

        This function will:
        - Extract the categories (statuses) and their counts.
        - Create a bar chart, adding data labels above each bar.
        - Adjust layout for readability.
        - Embed the resulting chart into the specified parent frame.
        """

        # Create a figure and axis for the chart
        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)

        # Extract data for plotting
        statuses = counts_df[status_column]
        counts = counts_df['Counts']

        # Handle the case when only one category is present
        if len(statuses) == 1:
            bar_width = 0.4  # Adjust the bar width for a single category
            bars = ax.bar(statuses, counts, color='skyblue', edgecolor='black', width=bar_width)
            # Set the x-ticks to the single category if needed
            ax.set_xticks([0])
        else:
            bars = ax.bar(statuses, counts, color='skyblue', edgecolor='black')

        # Add data labels on top of each bar
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height + 0.1,
                f'{int(height)}',
                ha='center',
                va='bottom',
                fontsize=9
            )

        # Set chart title and axes labels
        ax.set_title(f"{status_column} Counts for {project_name}", fontsize=12)
        ax.set_xlabel(status_column, fontsize=10)
        ax.set_ylabel('Counts', fontsize=10)

        # Rotate x-axis labels if necessary for readability
        ax.set_xticks(range(len(statuses)))
        ax.set_xticklabels(statuses, rotation=45, ha='right')

        # Adjust the layout to prevent clipping of tick-labels
        fig.tight_layout()

        # Embed the chart into the GUI using FigureCanvasTkAgg
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side='right', fill='both', expand=True)

    
    def show_error(self, message):
        # Show an error message to the user
        messagebox.showerror("Error", message)
        # Re-enable the Start Processing button
        self.start_btn.config(state='normal')

def main():
    root = tk.Tk()
    app = Application(root)
    root.mainloop()

if __name__ == '__main__':
    main()