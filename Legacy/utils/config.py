# config.py
# Stores configuration variables and constants

# Matching threshold
threshold = 80  # Adjust this value as needed

# File paths
INPUT_DIR = 'data/input/'
REPORTS_DIR = 'reports/'
OUTPUT_DIR = ""
USAGE_FILE = ""
EVENT_FILES = {}

# Containers for DataFrames
events = {}        # Holds initial events DataFrame
event_names = {}   # Holds split events-only DataFrame
event_props = {}   # Holds split event properties-only DataFrame

# Other configurations
SELECTED_WORKSPACES = []
SELECTED_PROJECTS = []
EVENT_FILES = {}
THRESHOLD = 80  # Default threshold value

# Add more variables as needed
