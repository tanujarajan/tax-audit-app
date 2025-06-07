# main.py
# Entry point of the application

import os
import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from utils.gui_qt import AuditAppWindow 
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from utils.file_utils import write_safe_excel 
from utils.setup import initialize_environment
from utils.analysis import (
    create_event_wordclouds,
    create_event_props_wordcloud,
    create_user_props_wordcloud,
    event_counts, matcher, 
    event_properties_counts, 
    user_properties_counts,
    generate_pii_report,
    get_top_duplicate_events_by_volume,
    event_properties_status_counts,
    user_properties_status_counts
)
from utils.report_generation import (
    generate_old_events_properties_report,
    generate_syntax_report,
    generate_unused_events_report,
    generate_missing_categories_descriptions_report,
    generate_duplicate_events_report,
    generate_user_property_misclassification_report
)
from utils.data_processing import (
    load_data,
    load_events_data,
    process_events,
    ff_empties,
    rm_blocked_deleted,
    fill_prop_status,
    split_prune_df,
    preprocess,
    fill_property_schema_status,
    rm_blocked_deleted_properties,
    prune_user_properties_df,
    schema_status_agg,
    identify_stale_and_single_day_events, 
    identify_stale_and_single_day_properties, 
    identify_stale_and_single_day_user_properties,
    profile_naming_syntax,
    identify_unused_events,
    identify_missing_categories_descriptions,
    identify_duplicate_events, 
    identify_event_properties_as_user_properties
)
from utils.pdf_generation import (
    generate_project_pdf, 
    get_exact_duplicate_counts_matrix
)
import pandas as pd

def main():
    # Initialize logging and environment
    logger = initialize_environment()
    logger.info("Starting Taxonomy Audit Helper application")
    
    try:
        app = QApplication(sys.argv)
        window = AuditAppWindow()
        window.show()
        logger.info("Application GUI initialized successfully")
        return_code = app.exec()
        logger.info("Application shutting down")
        sys.exit(return_code)
    except Exception as e:
        logger.exception("Fatal error in main application")
        sys.exit(1)

def run_data_processing(params, app):
    logger = logging.getLogger("TaxonomyAudit")
    logger.info("Starting data processing with parameters: %s", str(params))
    
    try:
        threshold = params['threshold']
        events_files = params['event_files']
        user_props_files = params['user_props_files']
        selected_workspaces = params['selected_workspaces']
        selected_projects = params['selected_projects']
        output_dir = params['output_dir']

        event_names = {}
        event_props = {}
        counts_dfs = {}
        user_props_data = {}
        event_props_counts_data = {}
        user_props_counts_data = {}

        # <--- NEW: Declare these dicts at the start
        all_events_matched = {}
        all_event_props_matched = {}
        all_user_props_matched = {}
        all_event_pii = {}
        all_user_pii = {}
        all_counts_dfs = {}
        all_event_props_counts = {}
        all_user_props_counts = {}
        all_syntax_summaries = {}
        all_missing_summary = {}
        all_top_unused_events = {}
        all_bottom_unused_events = {}
        all_flagged_summary = {}
        all_stale_events = {}
        all_stale_event_props = {}
        all_stale_user_props = {}
        all_single_day_events = {}
        all_single_day_event_props = {}
        all_single_day_user_props = {}


        # Initialize a dictionary to hold deduped event props DataFrames
        dedup_dfs = {}

        total_projects = len(selected_projects)
        processed_projects = 0

        # Retrieve the selected lookback window
        lookback_window = params.get("lookback_window", 30)  # Default to 30 days if not set

        # Load usage report
        usage_file_path = params.get("usage_file")
        if not usage_file_path:
            print("No usage file selected. Skipping unused event analysis.")
        else:
            try:
                usage_df = pd.read_csv(usage_file_path)

                # Generate the unused events report inside each project's directory
                for project in selected_projects:
                    project_output_dir = os.path.join(output_dir, project)
                    os.makedirs(project_output_dir, exist_ok=True)  # Ensure project directory exists
                    
                    # Filter the usage report for the current project
                    project_usage_df = usage_df[usage_df["Project Name"] == project]

                    # Identify unused events **specific to this project**
                    top_unused_events, bottom_unused_events = identify_unused_events(project_usage_df, lookback_window)

                    # Generate report only if there are flagged events
                    if not top_unused_events.empty or not bottom_unused_events.empty:
                        generate_unused_events_report(top_unused_events, bottom_unused_events, project_output_dir, lookback_window)

                    all_top_unused_events[project] = top_unused_events
                    all_bottom_unused_events[project] = bottom_unused_events
                    
                    # Identify duplicate events using the correct data source
                    duplicate_events_df = identify_duplicate_events(project_usage_df, lookback_window)

                    # Generate report if any duplicate events are found
                    if not duplicate_events_df.empty:
                        generate_duplicate_events_report(duplicate_events_df, project_output_dir, lookback_window)

            except Exception as e:
                print(f"Error loading usage report: {e}")


        for project, event_file_path in events_files.items():
            user_props_file_path = user_props_files.get(project)

            event_pii = pd.DataFrame()
            user_pii = pd.DataFrame()
            syntax_summary_df = pd.DataFrame()
            summary_df = pd.DataFrame()

            events_df = load_events_data(event_file_path)
            if events_df is None:
                print(f"Failed to load events data for project '{project}'. Skipping.")
                continue

            user_props_df = None
            if user_props_file_path:
                try:
                    user_props_df = pd.read_csv(user_props_file_path)
                    print(f"User Properties data loaded for project '{project}'.")

                    user_props_df = fill_property_schema_status(user_props_df)
                    user_props_df = rm_blocked_deleted_properties(user_props_df)
                    user_props_df = prune_user_properties_df(user_props_df)
                    user_props_data[project] = user_props_df

                except Exception as e:
                    print(f"Failed to load or process User Properties data for project '{project}': {e}")
                    continue

            print(f"Processing project '{project}'.")

            events_df = process_events(events_df)
            events_df = ff_empties(events_df, ['Object Name', 'Event Display Name', 'Event Schema Status'])
            events_df = rm_blocked_deleted(events_df)
            events_df = fill_prop_status(events_df)

            events_only, props_only = split_prune_df(events_df)
            event_names[project] = preprocess(events_only, table_type='event')
            event_props[project] = props_only
            event_names[project]['Category'] = 'Event'
            event_names[project]['Orig Index'] = event_names[project].index
            event_names[project] = matcher(event_names[project], 'Orig Index', 'Preprocessed Name', threshold)

            counts_df = event_counts(event_names[project], name=project)
            if counts_df is not None:
                counts_dfs[project] = counts_df

            try:
                project_output_dir = os.path.join(output_dir, project)
                os.makedirs(project_output_dir, exist_ok=True)

                # Define the subfolder for support files
                support_files_dir = os.path.join(project_output_dir, "Support Files")
                os.makedirs(support_files_dir, exist_ok=True)  # Ensure subfolder exists

                # Remove the 'Dataset Name' column if it exists
                if "Dataset Name" in counts_df.columns:
                    counts_df.drop(columns=["Dataset Name"], inplace=True)

                counts_csv_path = os.path.join(support_files_dir, f"{project}_event_counts.csv")
                counts_df.to_csv(counts_csv_path, index=False)
                counts_df1 = counts_df
                counts_df2 = counts_df

                props_csv_path = os.path.join(support_files_dir, f"{project}_event_properties.csv")
                event_props[project].to_csv(props_csv_path, index=False)

                # Compute dedup of Event Properties
                dedup_df = event_props[project].groupby('Event Property Name', as_index=False).agg({
                    'Property Type': 'first',
                    'Property Group Names': 'first',
                    'Property Description': 'first',
                    'Property Value Type': 'first',
                    'Property Schema Status': schema_status_agg,
                    'Property Required': 'first',
                    'Property Is Array': 'first',
                    'Property First Seen': 'min',
                    'Property Last Seen': 'max'
                })

                dedup_file = os.path.join(support_files_dir, f"{project}_event_properties_deduplicated.csv")
                dedup_df.to_csv(dedup_file, index=False)

                # Build the new DF
                event_props_status_df = event_properties_status_counts(dedup_df, name=project)

                # Now store it so we can pass it to the PDF
                event_props_counts_data[project] = event_props_status_df

                # Store the dedup_df for later profiling
                dedup_dfs[project] = dedup_df

                if user_props_df is not None:
                    user_props_csv_path = os.path.join(support_files_dir, f"{project}_processed_user_properties.csv")
                    user_props_df.to_csv(user_props_csv_path, index=False)
                    print(f"Processed User Properties data saved for project '{project}'.")
                
                if user_props_df is not None and not user_props_df.empty:
                    # Build the final user-props status DataFrame
                    user_props_status_df = user_properties_status_counts(user_props_df, name=project)

                    # Store this so you can pass it later to generate_project_pdf
                    user_props_counts_data[project] = user_props_status_df

                # Compute event_props_counts and user_props_counts
                if not dedup_df.empty:
                    epcdf = event_properties_counts(dedup_df, name=project)
                    event_props_counts_data[project] = epcdf

                if user_props_df is not None and not user_props_df.empty:
                    upcdf = user_properties_counts(user_props_df, name=project)
                    user_props_counts_data[project] = upcdf

                # Preprocess dedup_df and user_props_df for matching if needed
                dedup_df = preprocess(dedup_df, table_type='event_prop')
                if user_props_df is not None and not user_props_df.empty:
                    user_props_df = preprocess(user_props_df, table_type='user_prop')

                # Combine events, dedup_df, user_props_df for matching
                events_for_match = event_names[project].copy()
                events_for_match['Category'] = 'Event'
                events_for_match['Orig Index'] = events_for_match.index

                dedup_for_match = dedup_df.copy()
                dedup_for_match['Category'] = 'Event Property'
                dedup_for_match['Orig Index'] = dedup_for_match.index + events_for_match['Orig Index'].max() + 1

                user_props_for_match = None
                if user_props_df is not None and not user_props_df.empty:
                    user_props_for_match = user_props_df.copy()
                    user_props_for_match['Category'] = 'User Property'
                    user_props_for_match['Orig Index'] = user_props_for_match.index + dedup_for_match['Orig Index'].max() + 1

                frames_to_combine = [events_for_match, dedup_for_match]
                if user_props_for_match is not None:
                    frames_to_combine.append(user_props_for_match)

                combined_df = pd.concat(frames_to_combine, ignore_index=True)

                # Run matcher on combined_df
                combined_matched = matcher(combined_df, 'Orig Index', 'Preprocessed Name', threshold)

                # Split matched results by Category
                events_matched = combined_matched[combined_matched['Category'] == 'Event'].copy()
                event_props_matched = combined_matched[combined_matched['Category'] == 'Event Property'].copy()
                user_props_matched = combined_matched[combined_matched['Category'] == 'User Property'].copy()

                # Add 'Project' column
                events_matched['Project'] = project
                event_props_matched['Project'] = project
                user_props_matched['Project'] = project

                # Select only the required columns for each sheet
                events_columns = [
                    'Orig Index', 
                    'Object Type', 
                    'Object Name', 
                    'Event Display Name', 
                    'Event Schema Status', 
                    'Match Found', 
                    'Match Score', 
                    'Match Index', 
                    'Match Category',
                    'Project'   # Add this here too if you need Project for events (optional)
                ]

                event_props_columns = [
                    'Orig Index', 
                    'Category', 
                    'Event Property Name', 
                    'Property Schema Status', 
                    'Match Found', 
                    'Match Score', 
                    'Match Index', 
                    'Match Category',
                    'Project'   # Ensure Project is included here
                ]

                user_props_columns = [
                    'Orig Index', 
                    'Category', 
                    'Property Name', 
                    'Property Schema Status', 
                    'Match Found', 
                    'Match Score', 
                    'Match Index', 
                    'Match Category',
                    'Project'   # Ensure Project is included here as well
                ]

                events_matched = events_matched[events_columns]
                event_props_matched = event_props_matched[event_props_columns]
                user_props_matched = user_props_matched[user_props_columns]

                # Write matched results to Excel
                matched_excel = os.path.join(project_output_dir, "matched_results.xlsx")
                with pd.ExcelWriter(matched_excel, engine='openpyxl') as writer:
                    any_written = False
                    if not events_matched.empty:
                        events_matched.to_excel(writer, sheet_name='Events', index=False)
                        any_written = True
                    if not event_props_matched.empty:
                        event_props_matched.to_excel(writer, sheet_name='Event_Properties', index=False)
                        any_written = True
                    if not user_props_matched.empty:
                        user_props_matched.to_excel(writer, sheet_name='User_Properties', index=False)
                        any_written = True
                    if not any_written:
                        # Write a default sheet with a message
                        pd.DataFrame({"Message": ["No matched duplicates found for this project."]}).to_excel(writer, sheet_name="No Data", index=False)


                # Identify stale and single-day events
                stale_events_df, single_day_events_df = identify_stale_and_single_day_events(events_df)

                # Identify stale and single-day event properties from the deduplicated file
                dedup_file_path = os.path.join(output_dir, project, support_files_dir, f"{project}_event_properties_deduplicated.csv")
                if os.path.exists(dedup_file_path):
                    dedup_df = pd.read_csv(dedup_file_path)
                    stale_properties_df, single_day_properties_df = identify_stale_and_single_day_properties(dedup_df)
                else:
                    print(f"Deduplicated properties file not found for project '{project}'. Skipping stale property analysis.")
                    stale_properties_df, single_day_properties_df = pd.DataFrame(), pd.DataFrame()

                # Identify stale and single-day user properties
                stale_user_props_df, single_day_user_props_df = pd.DataFrame(), pd.DataFrame()
                if user_props_df is not None and not user_props_df.empty:
                    stale_user_props_df, single_day_user_props_df = identify_stale_and_single_day_user_properties(user_props_df)

                # Generate stale and single-day events and properties report
                generate_old_events_properties_report(stale_events_df, single_day_events_df, 
                                                    stale_properties_df, single_day_properties_df, 
                                                    stale_user_props_df, single_day_user_props_df, 
                                                    project_output_dir)
                
                # Identify missing categories and descriptions
                summary_df, missing_event_categories, missing_event_descriptions, missing_event_prop_descriptions, missing_user_prop_descriptions = (
                    identify_missing_categories_descriptions(event_names[project], dedup_dfs[project], user_props_df)
                )

                # Generate report if any missing data is found
                if not summary_df.empty:
                    generate_missing_categories_descriptions_report(summary_df, missing_event_categories, 
                                                                    missing_event_descriptions, missing_event_prop_descriptions, 
                                                                    missing_user_prop_descriptions, project_output_dir)

                # Profile naming syntax
                syntax_results = profile_naming_syntax(event_names[project], dedup_dfs[project], user_props_df)

                # Generate Syntax Summary and Capture the DataFrame
                syntax_summary_df = generate_syntax_report(syntax_results, project_output_dir)
            
                # Identify event properties that should be user properties
                flagged_properties_df = identify_event_properties_as_user_properties(dedup_dfs[project])

                # Create grouped summary from flagged event properties
                grouped_flagged_summary_df = (
                    flagged_properties_df
                    .groupby("Reason for Flagging")
                    .agg(Count=("Event Property Name", "count"))
                    .reset_index()
                    .rename(columns={"Reason for Flagging": "Reason"})
                )

                # Store for PDF use later
                all_flagged_summary[project] = grouped_flagged_summary_df

                # Generate report if any properties are flagged
                if not flagged_properties_df.empty:
                    generate_user_property_misclassification_report(flagged_properties_df, project_output_dir)
                
                # Call the PII report generation
                print(f"Generating PII report for project: {project}")
                event_pii, user_pii = generate_pii_report(event_props_matched, user_props_matched, project_output_dir)

                # Wordcloud generation
                print(f"Generating word clouds for project: {project}")
                create_event_wordclouds(event_names[project], project_output_dir)
                create_event_props_wordcloud(event_props[project], project_output_dir)
                if user_props_df is not None and not user_props_df.empty:
                    create_user_props_wordcloud(user_props_df, project_output_dir)
                else:
                    print(f"No user_props_df for project '{project}' or it's empty, skipping user props wordcloud.")
            
            except Exception as e:
                print(f"Error saving reports for project '{project}': {e}")

            processed_projects += 1
            progress_percent = int((processed_projects / total_projects) * 100)
            if hasattr(app, 'progress'):
                app.progress.emit(progress_percent)

            all_events_matched[project] = events_matched
            all_event_props_matched[project] = event_props_matched
            all_user_props_matched[project] = user_props_matched
            all_event_pii[project] = event_pii
            all_user_pii[project] = user_pii
            all_counts_dfs[project] = counts_df
            all_event_props_counts[project] = event_props_status_df
            all_user_props_counts[project] = user_props_status_df
            all_syntax_summaries[project] = syntax_summary_df
            all_missing_summary[project] = summary_df
            all_stale_events[project] = stale_events_df
            all_stale_event_props[project] = stale_properties_df
            all_stale_user_props[project] = stale_user_props_df
            all_single_day_events[project] = single_day_events_df
            all_single_day_event_props[project] = single_day_properties_df
            all_single_day_user_props[project] = single_day_user_props_df

        
        if len(selected_projects) > 1:
            print("Running gap analysis...")

            # Prepare sets for Events
            events_sets = {}
            for project in event_names.keys():
                if 'Object Name' in event_names[project].columns:
                    events_sets[project] = set(event_names[project]['Object Name'].dropna().astype(str))
                else:
                    print(f"Warning: 'Object Name' column not found for project '{project}'. Using empty set for events.")
                    events_sets[project] = set()

            # Prepare sets for Event Properties
            event_props_sets = {}
            for project in event_props.keys():
                if 'Event Property Name' in event_props[project].columns:
                    event_props_sets[project] = set(event_props[project]['Event Property Name'].dropna().astype(str))
                else:
                    print(f"Warning: 'Event Property Name' column not found for project '{project}'. Using empty set for event properties.")
                    event_props_sets[project] = set()

            # Prepare sets for User Properties
            user_props_sets = {}
            for project in user_props_data.keys():
                if 'Property Name' in user_props_data[project].columns:
                    user_props_sets[project] = set(user_props_data[project]['Property Name'].dropna().astype(str))
                else:
                    print(f"Warning: 'Property Name' column not found for project '{project}'. Using empty set for user properties.")
                    user_props_sets[project] = set()

            # Function to build gap analysis DataFrame
            def build_gap_df(sets_dict):
                """
                Given a dictionary of {project: set_of_items}, produce a DataFrame where each column is a project.
                Each column lists items not in that project but present in at least one other project.
                """
                if not sets_dict:
                    return pd.DataFrame()

                # Union of all items across projects
                all_items = set().union(*sets_dict.values())

                # For each project, find missing items
                # missing = all_items - sets_dict[project]
                data = {}
                for project in sets_dict:
                    missing_items = sorted(all_items - sets_dict[project])
                    data[project] = pd.Series(missing_items)

                # Create a DataFrame with columns as projects
                df = pd.DataFrame(data)
                return df

            events_gap_df = build_gap_df(events_sets)
            event_props_gap_df = build_gap_df(event_props_sets)
            user_props_gap_df = build_gap_df(user_props_sets)

            # Only create the file if there's something to write
            gap_file = os.path.join(output_dir, "gap_analysis.xlsx")
            with pd.ExcelWriter(gap_file, engine='openpyxl') as writer:
                any_written = False
                if not events_gap_df.empty:
                    events_gap_df.to_excel(writer, sheet_name='Events', index=False)
                    any_written = True
                if not event_props_gap_df.empty:
                    event_props_gap_df.to_excel(writer, sheet_name='Event_Properties', index=False)
                    any_written = True
                if not user_props_gap_df.empty:
                    user_props_gap_df.to_excel(writer, sheet_name='User_Properties', index=False)
                    any_written = True
                if not any_written:
                    pd.DataFrame({"Message": ["No cross-project gaps identified."]}).to_excel(writer, sheet_name="No Data", index=False)


            print(f"Gap analysis saved to {gap_file}")
        else:
            print("Multiple projects not selected. Skipping gap analysis.")

        # Loop for PDF Generation 
        for project in selected_projects:
            # retrieve from dictionaries
            project_events_matched = all_events_matched[project]
            project_event_props_matched = all_event_props_matched[project]
            project_user_props_matched = all_user_props_matched[project]

            # Then create the pivot table:
            duplicate_counts_df = get_exact_duplicate_counts_matrix(
                project_events_matched, project_event_props_matched, project_user_props_matched, project
            )

            # Retrieve the dictionaries:
            event_pii = all_event_pii[project]
            user_pii = all_user_pii[project]
            counts_df = all_counts_dfs[project]
            event_props_status_df = all_event_props_counts[project]
            user_props_status_df = all_user_props_counts[project]
            syntax_summary_df = all_syntax_summaries[project]
            missing_summary_df = all_missing_summary[project] 
            top_unused_events_df = all_top_unused_events[project]
            bottom_unused_events_df = all_bottom_unused_events[project]
            flagged_misclass_summary_df = all_flagged_summary[project]
            stale_events_df = all_stale_events[project]
            stale_properties_df = all_stale_event_props[project]
            stale_user_props_df = all_stale_user_props[project]
            single_day_events_df = all_single_day_events[project]
            single_day_properties_df = all_single_day_event_props[project]
            single_day_user_props_df = all_single_day_user_props[project]


            # Filter usage data for the current project
            project_usage_df = usage_df[usage_df["Project Name"] == project] if "Project Name" in usage_df.columns else pd.DataFrame()

            # Get top duplicate events by volume 
            duplicate_events_volume_df = get_top_duplicate_events_by_volume(project_usage_df, lookback_window) if not project_usage_df.empty else pd.DataFrame()

            
            # Ensure 'Percentage' column exists before applying formatting
            if 'Percentage' in counts_df.columns:
                if pd.api.types.is_string_dtype(counts_df['Percentage']):
                    # Extract numeric values from strings like '90.75%' → 90.75
                    counts_df['Percentage'] = counts_df['Percentage'].str.replace('%', '', regex=False).astype(float)

                # Ensure numeric formatting (round to 2 decimal places and add '%')
                counts_df['Percentage'] = counts_df['Percentage'].apply(lambda x: f"{x:.2f}%")

            # Get top and bottom unused events by volume 
            top_unused_events_df = all_top_unused_events.get(project, pd.DataFrame())
            # Ensure numeric formatting (round to 2 decimal places and add '%')
            top_unused_events_df['Volume %'] = top_unused_events_df['Volume %'].apply(lambda x: f"{x:.2f}%")
            bottom_unused_events_df = all_bottom_unused_events.get(project, pd.DataFrame())
            # Ensure numeric formatting (round to 2 decimal places and add '%')
            bottom_unused_events_df['Volume %'] = bottom_unused_events_df['Volume %'].apply(lambda x: f"{x:.2f}%")                

            # Get missing categories and descriptions report
            missing_summary_df = all_missing_summary.get(project, pd.DataFrame())

            # Group and summarize flagged misclassified event properties
            flagged_misclass_summary_df = all_flagged_summary.get(project, pd.DataFrame())

            # Count Stale Events and Properties 
            stale_events_df = all_stale_events.get(project, pd.DataFrame())
            stale_properties_df = all_stale_event_props.get(project, pd.DataFrame())
            stale_user_props_df = all_stale_user_props.get(project, pd.DataFrame())

            # Count Singe Day Events and Properties 
            single_day_events_df = all_single_day_events.get(project, pd.DataFrame())
            single_day_properties_df = all_single_day_event_props.get(project, pd.DataFrame())
            single_day_user_props_df = all_single_day_user_props.get(project, pd.DataFrame())
            
            # Ensure valid data before generating PDF
            if not duplicate_counts_df.empty or not duplicate_events_volume_df.empty:
                pdf_path = os.path.join(output_dir, project, f"{project}_report.pdf")
                os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

                # Generate the PDF with both sections
                generate_project_pdf(
                        project,
                        pdf_path,
                        duplicate_counts_df,
                        duplicate_events_volume_df,
                        event_pii,
                        user_pii,
                        event_counts_df=counts_df,
                        event_props_counts_df=event_props_status_df,
                        user_props_counts_df=user_props_status_df,
                        syntax_summary_df=syntax_summary_df,
                        missing_summary_df=missing_summary_df,
                        top_unused_events_df=top_unused_events_df,
                        bottom_unused_events_df=bottom_unused_events_df,
                        lookback_window=lookback_window,
                        flagged_misclass_summary_df=flagged_misclass_summary_df,
                        stale_events_df=stale_events_df,
                        stale_properties_df=stale_properties_df,
                        stale_user_props_df=stale_user_props_df,
                        single_day_events_df=single_day_events_df,
                        single_day_properties_df=single_day_properties_df,
                        single_day_user_props_df=single_day_user_props_df   
                    )
            else:
                print(f"Skipping PDF for {project}: No matched duplicates or duplicate events by volume found.")


        # Add dedup_dfs and user_props_data to results so they're available in update_results
        results = {
            'event_names': event_names,
            'counts_dfs': counts_dfs,
            'user_props_data': user_props_data,
            'event_props_counts': event_props_counts_data,
            'user_props_counts': user_props_counts_data,
            'dedup_dfs': dedup_dfs,
            'params': params
        }

        if hasattr(app, 'completed'):
            app.completed.emit(results)

        return results
    except Exception as e:
        logger.exception("Fatal error in run_data_processing")
        return None


if __name__ == "__main__":
    main()