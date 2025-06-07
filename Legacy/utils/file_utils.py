# file_utils.py
# Functions related to file and directory operations

import os

def create_directories():
    """
    Creates necessary directories if they don't exist.
    """
    directories = ['data/input', 'data/output', 'reports']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")
        else:
            print(f"Directory already exists: {directory}")

def write_safe_excel(writer, sheet_name, df):
    if not df.empty:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        return True
    return False
