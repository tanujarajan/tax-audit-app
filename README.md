# Taxonomy Audit Helper

## 📌 Project Overview
The **Taxonomy Audit Helper** is a Python-based tool that helps teams analyze and audit event taxonomy data. It provides a GUI interface for loading event/user properties data, processing it, and generating various reports, including schema status insights, data profiling, word clouds for visualization, and PII detection.

## ✨ Features
- **Graphical User Interface (GUI)** using Tkinter.
- **CSV Data Loading**: Load event and user property data.
- **Data Cleaning & Processing**: Filters out blocked/deleted records, fills missing schema statuses.
- **Threshold-Based Matching**: Uses **fuzzy matching** with RapidFuzz to identify similar events.
- **Word Cloud Generation**: Visualizes event and property names.
- **Gap Analysis**: Compares taxonomy structures across multiple projects.
- **PII Report Generation**: Detects sensitive data fields like names, emails, phone numbers, etc.
- **Exportable Reports**: Generates CSV/Excel reports for further analysis.
- **Automatic Directory Setup**: Ensures necessary directories are created automatically.

## 🛠️ Installation
### **1. Clone the repository**
```bash
git clone https://github.com/your-org/taxonomy-audit-helper.git
cd taxonomy-audit-helper
```

### **2. Install Python 3.11.0** (CRITICAL)
```bash
brew install python@3.11
```

### **2.5. Verify the installation** 
```bash
python3.11 --version
```

### **3. Create a Virtual Environment** (Recommended)
```bash
python3.11 -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

### **3.5. Verify the Virtual Environment** 
```bash
python --version
```

### **4. Install Dependencies**
```bash
pip install -r requirements.txt
```

## 🚀 Usage
### **1. Launch the Application**
```bash
python main.py
```
This will open a **GUI interface**, where users can:
- Select an **output directory**.
- Choose **workspaces and projects** for analysis.
- Load **event/user property files**.
- Set a **lookback window** for event volume analysis.
- Set a **matching threshold**.
- Start processing and generate reports.

### **2. Output Reports**
The processed data and reports are saved in the specified **output directory**. These include:
- `event_counts.csv` → Summary of event occurrences.
- `event_properties.csv` → Deduplicated list of event properties.
- `processed_user_properties.csv` → Cleaned user property data.
- `matched_results.xlsx` → Matched taxonomy structures.
- `gap_analysis.xlsx` → Identifies missing taxonomy elements across projects.
- **Word Clouds**: Saved as PNG images in the **output directory**.
- **PII Report (`PII_report.xlsx`)**: Identifies fields containing sensitive data.

## 📂 Project Structure
```
📦 taxonomy-audit-helper
├── data/                   # Input data directory (auto-created)
├── reports/                # Output reports directory
├── utils/                  # Utility modules
│   ├── analysis.py         # Event taxonomy analysis & matching
│   ├── data_processing.py  # Data cleaning and transformations
│   ├── file_utils.py       # File handling & directory setup
│   ├── GUI.py              # Tkinter-based GUI
│   ├── report_generation.py# Generates Excel & HTML reports
│   ├── setup.py            # Setup utilities
├── .gitignore              # Ignore unnecessary files
├── application.log         # Logs
├── main.py                 # Entry point
├── main.spec               # PyInstaller spec file (if packaging)
├── README.md               # Project documentation
├── requirements.txt        # Required dependencies
├── test.py                 # Test scripts
```

## 🏗️ Dependencies
The project relies on the following key libraries:
- **Pandas**: Data processing (`pandas`)
- **Tkinter**: GUI framework (`tk`)
- **Matplotlib**: Visualization (`matplotlib`)
- **WordCloud**: Generates word clouds (`wordcloud`)
- **RapidFuzz**: Fuzzy string matching for taxonomy analysis (`rapidfuzz`)
- **OpenPyXL**: Excel report generation (`openpyxl`)
- **Sweetviz**: Automated data profiling (`sweetviz`)

To install all dependencies, run:
```bash
pip install -r requirements.txt
```

## 🔍 Data Processing & Matching
- Uses **fuzzy matching** with **RapidFuzz** to detect similar event names and properties.
- Generates **gap analysis reports** comparing different project taxonomies.
- Detects **Personally Identifiable Information (PII)** such as names, emails, and phone numbers in event and user properties.
- Produces **visualizations**, including **word clouds** for better analysis.

## 🛠️ Troubleshooting / FAQ
### **Issue: Virtual Environment Not Activating**
- **Windows**: If `venv\Scripts\activate` doesn’t work, try:
  ```powershell
  Set-ExecutionPolicy Unrestricted -Scope Process
  venv\Scripts\activate
  ```
- **Mac/Linux**: Ensure you’re using the correct shell. Try:
  ```bash
  source venv/bin/activate
  ```
- **General Fix**: If activation fails, delete `venv/` and recreate it:
  ```bash
  rm -rf venv  # macOS/Linux
  rmdir /s /q venv  # Windows
  python -m venv venv
  ```

### **Issue: Dependencies Not Installing Correctly**
- If `pip install -r requirements.txt` fails:
  ```bash
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  ```
- Ensure you’re in the virtual environment (`venv` activated) before installing.

### **Issue: Application Fails to Start**
- Ensure you have installed **all dependencies**.
- Check for missing files in `data/` or `reports/` directories.
- Run with `python main.py` and check for error messages.

## ✨ Planned Updates
- **Enhance PII Detection**: Enhance PII Property detection by adding more PII detection fields (COMPLETE - 2/26/2025)
- **Inconsistent Syntax Flagging**: Profile Event & Property naming syntax & generate a report of events and properties that fall out of the majority syntax (COMPLETE - 2/26/2025)
- **Old Events and Properties Report**: Flag Events and Properties that have not been ingested in one year & generate a report for potential data deletion. (COMPLETE - 2/26/2025)
- **Unused Events Report**: Flag events with top volume and no queries as well as events with low volume and no queries (Top & Bottom 10) (COMPLETE - 2/27/2025)
- **Events and Properties with Missing Categories and Descrptions**: Generate report summarizing number of events and properties where the descrptions and categories are missing (COMPLETE - 2/28/2025)
- **Identify Duplicate Event Count**: Identify events with identical event volumes to flag as potential duplicative events (COMPLETE - 3/3/2025)
- **User Property Detection with Event Property List**: Based on a standardized list, detect Event properties that should be User Properties (based on best practices) (COMPLETE - 3/3/2025)
- **Consolidated Findings Report (PDF)**: Generate a PDF report summarizing findings, referencing individual sheets containing flagged event and property lists. A PDF report will also contain an explanation of why the data is being flagged and potential next steps (WIP)
- **Enhancements to Secondary Results Window**: Enhancements to Secondary Results window to contain summaries of data flag reports generated
- **Report Generation Flexibility**: Ability to choose which reports are generated (nice-to-have).
- **GUI-Based Multi-Project Comparison**: Allow users to compare taxonomy structures across multiple projects interactively in the GUI rather than relying solely on reports.
- **Advanced Logging & Debugging**: Introduce a dedicated logging module for better debugging and include a "debug mode" to capture additional insights.
- **Optimized Fuzzy Matching**: Implement caching for previously matched results and explore using approximate nearest neighbor algorithms (e.g., FAISS) for better performance.
- **Asynchronous Processing**: Improve GUI responsiveness by running data processing in the background using threading or asyncio.
- **Memory-Efficient Data Processing**: Implement chunked CSV reading (`pd.read_csv(..., chunksize=5000)`) and explore parallel processing for large datasets.
- **Modular Report Generation**: Refactor `report_generation.py` to break down large functions into single-responsibility functions for better maintainability.

## 🤝 Contributing
If you'd like to contribute:
1. Fork the repository.
2. Create a new branch (`feature/your-feature-name`).
3. Commit your changes and push to the branch.
4. Open a **pull request**.

💡 **Need help?** Feel free to reach out by opening an issue on GitHub! Or contact Abi Moosa