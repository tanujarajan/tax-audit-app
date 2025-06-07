# data_processing.py
# Functions for data loading and processing

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from rapidfuzz.utils import default_process
import re

def load_data(file_path):
    """
    Loads data from a CSV file.
    """
    try:
        df = pd.read_csv(file_path)
        print(f"Data loaded successfully from {file_path}")
        return df
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred while loading the data: {e}")
        return None

def load_events_data(file_path):
    """
    Loads events data from a CSV file.
    """
    try:
        events_df = pd.read_csv(
            file_path,
            dtype={'Tags': str, 'Event Source': str, 'Property Description': str},
            parse_dates=[
                'Event First Seen',
                'Event Last Seen',
                'Property First Seen',
                'Property Last Seen'
            ]
        )
        print(f"Events data loaded successfully from {file_path}")
        return events_df
    except Exception as e:
        print(f"An error occurred while loading the events data: {e}")
        return None

def process_events(events_df):
    """
    Cleans the events DataFrame by filling missing values.
    - Fills missing 'Event Schema Status' with 'LIVE' where 'Object Type' is not null.
    - Fills missing 'Event Display Name' with an empty string where 'Object Type' is not null.
    """
    events_df.loc[
        (events_df['Object Type'].notnull() & events_df['Event Schema Status'].isnull()),
        'Event Schema Status'
    ] = 'LIVE'

    events_df.loc[
        (events_df['Object Type'].notnull() & events_df['Event Display Name'].isnull()),
        'Event Display Name'
    ] = ''
    return events_df

def ff_empties(df_events, cols_ffill):
    """
    Performs forward fill on specified columns to handle missing values.
    """
    missing_cols = [col for col in cols_ffill if col not in df_events.columns]
    if missing_cols:
        print(f"Warning: The following columns to forward fill are missing in the DataFrame: {missing_cols}")
    existing_cols = [col for col in cols_ffill if col in df_events.columns]
    df_events.loc[:, existing_cols] = df_events.loc[:, existing_cols].ffill()
    return df_events

def rm_blocked_deleted(df_events):
    """
    Removes events with a status of 'BLOCKED' or 'DELETED'.
    """
    filtered_df = df_events[
        (df_events['Event Schema Status'] != 'BLOCKED') &
        (df_events['Event Schema Status'] != 'DELETED')
    ]
    removed_count = len(df_events) - len(filtered_df)
    print(f"Removed {removed_count} events with status 'BLOCKED' or 'DELETED'.")
    return filtered_df

def fill_prop_status(df_events):
    """
    Fills missing property schema statuses with 'LIVE'.
    """
    df_events.loc[
        df_events['Property Schema Status'].isnull(),
        'Property Schema Status'
    ] = 'LIVE'
    return df_events

def rm_blocked_deleted_properties(df_props):
    """
    Removes properties with a status of 'BLOCKED' or 'DELETED'.
    """
    filtered_df = df_props[
        (df_props['Property Schema Status'] != 'BLOCKED') &
        (df_props['Property Schema Status'] != 'DELETED')
    ]
    removed_count = len(df_props) - len(filtered_df)
    print(f"Removed {removed_count} properties with status 'BLOCKED' or 'DELETED'.")
    return filtered_df

def fill_property_schema_status(df_props):
    """
    Fills missing property schema statuses with 'LIVE'.
    """
    df_props['Property Schema Status'].fillna('LIVE', inplace=True)
    return df_props

def prune_user_properties_df(df_props):
    """
    Selects only the specified columns from the User Properties DataFrame.

    Parameters:
    - df_props (pd.DataFrame): The original User Properties DataFrame.

    Returns:
    - df_props_pruned (pd.DataFrame): DataFrame containing only the specified columns.
    """
    # Define the columns to keep
    user_props_cols = [
        'Property Type',
        'Property Name',
        'Property Description',
        'Property Value Type',
        'Property Schema Status',
        'Property First Seen',
        'Property Last Seen'
    ]

    # Check for missing columns
    missing_cols = [col for col in user_props_cols if col not in df_props.columns]
    if missing_cols:
        print(f"Warning: The following User Properties columns are missing and will be skipped: {missing_cols}")

    # Select existing columns
    selected_cols = [col for col in user_props_cols if col in df_props.columns]
    df_props_pruned = df_props[selected_cols]

    return df_props_pruned


def split_prune_df(df_events):
    """
    Splits the events DataFrame into two DataFrames: one for events and one for properties.

    Parameters:
    - df_events (pd.DataFrame): The original events DataFrame.

    Returns:
    - event_names (pd.DataFrame): DataFrame containing event names and related information.
    - event_props (pd.DataFrame): DataFrame containing event properties and related information.
    """
    # Define default columns for event names and event properties
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

    event_prop_cols = [
        'Object Name',
        'Event Display Name',
        'Property Type',
        'Property Group Names',
        'Event Property Name',
        'Property Description',
        'Property Value Type',
        'Property Schema Status',
        'Property Required',
        'Property Is Array',
        'Property First Seen',
        'Property Last Seen'
    ]

    # Check if 'Object Type' column exists
    if 'Object Type' not in df_events.columns:
        print("Error: 'Object Type' column is missing from the DataFrame.")
        return pd.DataFrame(), pd.DataFrame()

    # Split based on 'Object Type' being null
    props = df_events['Object Type'].isnull()
    event_names = df_events[~props].copy()
    event_props = df_events[props].copy()

    # Select specified columns, ignoring any missing columns
    missing_event_name_cols = [col for col in event_name_cols if col not in event_names.columns]
    if missing_event_name_cols:
        print(f"Warning: The following event name columns are missing and will be skipped: {missing_event_name_cols}")
    selected_event_name_cols = [col for col in event_name_cols if col in event_names.columns]
    event_names = event_names[selected_event_name_cols]

    missing_event_prop_cols = [col for col in event_prop_cols if col not in event_props.columns]
    if missing_event_prop_cols:
        print(f"Warning: The following event property columns are missing and will be skipped: {missing_event_prop_cols}")
    selected_event_prop_cols = [col for col in event_prop_cols if col in event_props.columns]
    event_props = event_props[selected_event_prop_cols]

    print(f"Split into {len(event_names)} event names and {len(event_props)} event properties.")
    return event_names, event_props

def preprocess(df, table_type):
    """
    Preprocesses names for matching by normalizing them.

    Parameters:
    - df (pd.DataFrame): The DataFrame to preprocess.
    - table_type (str): Type of table ('event', 'event_prop', 'user_prop').

    Returns:
    - df (pd.DataFrame): The preprocessed DataFrame with a new 'Preprocessed Name' column.
    """
    df = df.reset_index(drop=False)
    df = df.rename(columns={'index': 'Orig Index'})

    if table_type == 'event':
        if 'Event Display Name' in df.columns and 'Object Name' in df.columns:
            df['Event Display Name'] = df['Event Display Name'].replace('', pd.NA)
            df['Preprocessed Name'] = [
                default_process(name) for name in df['Event Display Name'].combine_first(df['Object Name'])
            ]
        else:
            print("Warning: 'Event Display Name' or 'Object Name' column is missing for preprocessing.")
            df['Preprocessed Name'] = pd.NA

    elif table_type == 'event_prop':
        if 'Event Property Name' in df.columns:
            df['Preprocessed Name'] = [
                default_process(name) for name in df['Event Property Name']
            ]
        else:
            print("Warning: 'Event Property Name' column is missing for preprocessing.")
            df['Preprocessed Name'] = pd.NA

    elif table_type == 'user_prop':
        if 'Property Name' in df.columns:
            df['Preprocessed Name'] = [
                default_process(name) for name in df['Property Name']
            ]
        else:
            print("Warning: 'Property Name' column is missing for preprocessing.")
            df['Preprocessed Name'] = pd.NA

    else:
        print(f"Warning: Unknown table_type '{table_type}'. No preprocessing applied.")
        df['Preprocessed Name'] = pd.NA

    return df

def schema_status_agg(x):
    unique_statuses = x.unique()
    # If both LIVE and UNEXPECTED appear, go with LIVE
    if 'LIVE' in unique_statuses:
        return 'LIVE'
    elif 'UNEXPECTED' in unique_statuses:
        return 'UNEXPECTED'
    else:
        # If other statuses appear, just pick the first encountered
        return x.iloc[0]

def identify_stale_and_single_day_events(events_df):
    """
    Identifies events that have not been seen in over a year (stale)
    and events that were only seen for a single day.
    
    Parameters:
    - events_df (pd.DataFrame): DataFrame containing event data.

    Returns:
    - stale_events_df (pd.DataFrame): Events not seen in over a year.
    - single_day_events_df (pd.DataFrame): Events seen only for one day.
    """
    if 'Event Last Seen' not in events_df.columns or 'Event First Seen' not in events_df.columns:
        print("Required columns for stale event detection are missing.")
        return pd.DataFrame(), pd.DataFrame()
    
    # Define the threshold for "stale" (1 year ago)
    one_year_ago = datetime.now() - timedelta(days=365)

    # Convert to datetime
    events_df['Event Last Seen'] = pd.to_datetime(events_df['Event Last Seen'], errors='coerce')
    events_df['Event First Seen'] = pd.to_datetime(events_df['Event First Seen'], errors='coerce')

    # Identify stale events
    stale_events_df = events_df[events_df['Event Last Seen'] < one_year_ago].copy()

    # Identify single-day events
    single_day_events_df = events_df[events_df['Event First Seen'] == events_df['Event Last Seen']].copy()

    return stale_events_df, single_day_events_df


def identify_stale_and_single_day_properties(event_props_dedup_df):
    """
    Identifies stale and single-day event properties using the '_event_properties_deduplicated.csv' file.

    Parameters:
    - event_props_dedup_df (pd.DataFrame): DataFrame containing deduplicated event properties.

    Returns:
    - stale_properties_df (pd.DataFrame): Properties not seen in over a year.
    - single_day_properties_df (pd.DataFrame): Properties seen only for one day.
    """
    if 'Property Last Seen' not in event_props_dedup_df.columns or 'Property First Seen' not in event_props_dedup_df.columns:
        print("Required columns for stale property detection are missing.")
        return pd.DataFrame(), pd.DataFrame()

    # Define the threshold for "stale" (1 year ago)
    one_year_ago = datetime.now() - timedelta(days=365)

    # Convert to datetime
    event_props_dedup_df['Property Last Seen'] = pd.to_datetime(event_props_dedup_df['Property Last Seen'], errors='coerce')
    event_props_dedup_df['Property First Seen'] = pd.to_datetime(event_props_dedup_df['Property First Seen'], errors='coerce')

    # Identify stale properties
    stale_properties_df = event_props_dedup_df[event_props_dedup_df['Property Last Seen'] < one_year_ago].copy()

    # Identify single-day properties
    single_day_properties_df = event_props_dedup_df[event_props_dedup_df['Property First Seen'] == event_props_dedup_df['Property Last Seen']].copy()

    return stale_properties_df, single_day_properties_df


def identify_stale_and_single_day_user_properties(user_props_df):
    """
    Identifies stale and single-day user properties.

    Parameters:
    - user_props_df (pd.DataFrame): DataFrame containing user properties.

    Returns:
    - stale_user_props_df (pd.DataFrame): User properties not seen in over a year.
    - single_day_user_props_df (pd.DataFrame): User properties seen only for one day.
    """
    if 'Property Last Seen' not in user_props_df.columns or 'Property First Seen' not in user_props_df.columns:
        print("Required columns for stale user property detection are missing.")
        return pd.DataFrame(), pd.DataFrame()

    # Define the threshold for "stale" (1 year ago)
    one_year_ago = datetime.now() - timedelta(days=365)

    # Convert to datetime
    user_props_df['Property Last Seen'] = pd.to_datetime(user_props_df['Property Last Seen'], errors='coerce')
    user_props_df['Property First Seen'] = pd.to_datetime(user_props_df['Property First Seen'], errors='coerce')

    # Identify stale user properties
    stale_user_props_df = user_props_df[user_props_df['Property Last Seen'] < one_year_ago].copy()

    # Identify single-day user properties
    single_day_user_props_df = user_props_df[user_props_df['Property First Seen'] == user_props_df['Property Last Seen']].copy()

    return stale_user_props_df, single_day_user_props_df


# Define syntax patterns including additional cases
SYNTAX_PATTERNS = {
    "UPPER CASE": r"^[A-Z\s]+$",  # All uppercase letters, allowing spaces
    "lower case": r"^[a-z\s]+$",  # All lowercase letters, allowing spaces
    "Sentence case": r"^[A-Z][a-z]*(?:\s[a-z]+)*$",  # First word capitalized, others lowercase
    "Title Case": r"^(?:[A-Z][a-z]+\s*)+$",  # Every word capitalized
    "PascalCase": r"^[A-Z][a-zA-Z0-9]+(?:[A-Z][a-zA-Z0-9]+)*$",
    "camelCase": r"^[a-z]+(?:[A-Z][a-zA-Z0-9]*)*$",
    "snake_case": r"^[a-z]+(?:_[a-z0-9]+)*$",
    "kebab-case": r"^[a-z]+(?:-[a-z0-9]+)*$",
    "SCREAMING_SNAKE_CASE": r"^[A-Z]+(?:_[A-Z0-9]+)*$"
}

def categorize_syntax(name):
    """
    Categorizes the syntax type of a given name.

    Parameters:
    - name (str): The event, event property, or user property name.

    Returns:
    - (str): The detected syntax type or 'Other' if no match is found.
    """
    if not isinstance(name, str) or name.strip() == "":
        return "Other"

    for syntax_type, pattern in SYNTAX_PATTERNS.items():
        if re.match(pattern, name):
            return syntax_type
    return "Other"

def profile_naming_syntax(events_df, event_props_df, user_props_df):
    """
    Profiles naming syntax for events, event properties, and user properties.

    Parameters:
    - events_df (pd.DataFrame): DataFrame containing event names.
    - event_props_df (pd.DataFrame): DataFrame containing event property names.
    - user_props_df (pd.DataFrame): DataFrame containing user property names.

    Returns:
    - (dict): Dictionary containing categorized dataframes for events, event properties, and user properties.
    """
    syntax_results = {}

    if "Object Name" in events_df.columns:
        events_df["Syntax Category"] = events_df["Object Name"].apply(categorize_syntax)
        events_df["Org Index"] = events_df.index
        syntax_results["events"] = events_df[["Object Name", "Syntax Category", "Org Index"]]

    if "Event Property Name" in event_props_df.columns:
        event_props_df["Syntax Category"] = event_props_df["Event Property Name"].apply(categorize_syntax)
        event_props_df["Org Index"] = event_props_df.index
        syntax_results["event_properties"] = event_props_df[["Event Property Name", "Syntax Category", "Org Index"]]

    if "Property Name" in user_props_df.columns:
        user_props_df["Syntax Category"] = user_props_df["Property Name"].apply(categorize_syntax)
        user_props_df["Org Index"] = user_props_df.index
        syntax_results["user_properties"] = user_props_df[["Property Name", "Syntax Category", "Org Index"]]

    return syntax_results

def identify_unused_events(usage_df, lookback_window):
    """
    Identifies unused events by comparing volume and query counts using the usage report.
    Now also adds a 'Volume %' column, representing each event's volume percentage
    of ALL events (for the selected lookback window).
    """
    volume_col = f"{lookback_window} Day Volume"
    query_col = f"{lookback_window} Day Queries"

    # Ensure required columns exist
    if volume_col not in usage_df.columns or query_col not in usage_df.columns:
        print(f"Missing required columns: {volume_col} or {query_col}. Skipping analysis.")
        return pd.DataFrame(), pd.DataFrame()

    # Convert to numeric (handling potential missing values)
    usage_df[volume_col] = pd.to_numeric(usage_df[volume_col], errors="coerce").fillna(0)
    usage_df[query_col] = pd.to_numeric(usage_df[query_col], errors="coerce").fillna(0)

    # 1) Calculate total volume across ALL events (before filtering)
    total_volume = usage_df[volume_col].sum()

    # Avoid divide-by-zero if total_volume is 0
    if total_volume > 0:
        # 2) Create the 'Volume %' column as a numeric percentage
        usage_df["Volume %"] = (usage_df[volume_col] / total_volume) * 100.0
        # Round to 2 decimals
        usage_df["Volume %"] = usage_df["Volume %"].round(2)
    else:
        # If total_volume == 0, just set Volume % to 0
        usage_df["Volume %"] = 0.00

    # Filter only relevant columns
    usage_df = usage_df[["Event Name", volume_col, query_col, "Volume %"]].copy()

    # 3) Filter events where queries == 0
    unused_events = usage_df[usage_df[query_col] == 0].copy()

    # 4) Top & Bottom 10 by Volume
    top_unused_events = unused_events.nlargest(10, volume_col)
    bottom_unused_events = unused_events.nsmallest(10, volume_col)

    return top_unused_events, bottom_unused_events


def identify_missing_categories_descriptions(events_df, event_props_df, user_props_df):
    """
    Identifies events and properties missing descriptions and categories.

    Parameters:
    - events_df (pd.DataFrame): DataFrame containing event data.
    - event_props_df (pd.DataFrame): DataFrame containing event property names.
    - user_props_df (pd.DataFrame): DataFrame containing user properties.

    Returns:
    - summary_counts (pd.DataFrame): Summary of missing categories/descriptions.
    - missing_event_categories (pd.DataFrame): Events missing categories.
    - missing_event_descriptions (pd.DataFrame): Events missing descriptions.
    - missing_event_prop_descriptions (pd.DataFrame): Event properties missing descriptions.
    - missing_user_prop_descriptions (pd.DataFrame): User properties missing descriptions.
    """
    summary_counts = {}

    # Helper function to clean DataFrames
    def clean_dataframe(df, columns):
        """Filter and clean DataFrame to remove NaN values and reset index."""
        if not df.empty and all(col in df.columns for col in columns):
            df = df[df[columns[1]].isna()][columns].copy()
            df.fillna("", inplace=True)  # Replace NaNs with empty strings
            df.reset_index(drop=True, inplace=True)
        else:
            df = pd.DataFrame(columns=columns)
        return df

    # Identify missing event categories
    missing_event_categories = clean_dataframe(events_df, ["Object Name", "Event Category"])
    summary_counts["Missing Event Categories"] = len(missing_event_categories)

    # Identify missing event descriptions
    missing_event_descriptions = clean_dataframe(events_df, ["Object Name", "Object Description"])
    summary_counts["Missing Event Descriptions"] = len(missing_event_descriptions)

    # Identify missing event property descriptions
    missing_event_prop_descriptions = clean_dataframe(event_props_df, ["Event Property Name", "Property Description"])
    summary_counts["Missing Event Property Descriptions"] = len(missing_event_prop_descriptions)

    # Identify missing user property descriptions
    missing_user_prop_descriptions = clean_dataframe(user_props_df, ["Property Name", "Property Description"])
    summary_counts["Missing User Property Descriptions"] = len(missing_user_prop_descriptions)

    # Convert summary counts to DataFrame
    summary_df = pd.DataFrame(list(summary_counts.items()), columns=["Category", "Count"])

    return summary_df, missing_event_categories, missing_event_descriptions, missing_event_prop_descriptions, missing_user_prop_descriptions

def identify_duplicate_events(usage_df, lookback_window):
    """
    Identifies duplicate events based on identical event volumes within the selected lookback window.

    Parameters:
    - usage_df (pd.DataFrame): DataFrame containing the usage report.
    - lookback_window (int): The selected look-back window (30, 90, 180, 270, 365 days).

    Returns:
    - duplicate_events_df (pd.DataFrame): DataFrame containing duplicate events with identical volumes.
    """
    volume_col = f"{lookback_window} Day Volume"

    # Ensure the required column exists
    if volume_col not in usage_df.columns:
        print(f"Missing required column: {volume_col}. Skipping duplicate event detection.")
        return pd.DataFrame()

    # Remove events where volume = 0
    usage_df = usage_df[usage_df[volume_col] > 0]

    # Group by project and volume, filter where multiple events share the same volume
    duplicate_events_df = usage_df.groupby(["Project Name", volume_col]).filter(lambda x: len(x) > 1)

    # Keep only relevant columns
    if not duplicate_events_df.empty:
        duplicate_events_df = duplicate_events_df[["Project Name", "Event Name", volume_col]].copy()
        duplicate_events_df = duplicate_events_df.sort_values(by=["Project Name", volume_col])

    return duplicate_events_df

import re

def identify_event_properties_as_user_properties(event_props_df):
    """
    Identifies event properties that should be categorized as user properties.

    Parameters:
    - event_props_df (pd.DataFrame): DataFrame containing event property names.

    Returns:
    - flagged_properties_df (pd.DataFrame): DataFrame containing flagged event properties with reasons.
    """
    # Define keyword-based detection patterns
    keyword_patterns = {
        "Starts with 'user_'": r"^user_.*",
        "Contains 'version'": r".*version.*",
        "Contains 'plan'": r".*plan.*",
        "Contains 'source'": r".*source.*",
        "Contains 'medium'": r".*medium.*",
        "Contains 'utm'": r".*utm.*",
        "Contains 'total'": r".*total.*",
        "Location Metadata": r".*(latitude|longitude|country|region|timezone).*",
        "Campaign Metadata": r".*(campaign|source|medium|utm_).*"
    }

    # Define PII detection patterns
    pii_patterns = [
        r'(?i)\bfirst[\s._-]*name\b', r'(?i)\blast[\s._-]*name\b', r'(?i)\bfull[\s._-]*name\b',
        r'(?i)\bsurname\b', r'(?i)\bname\b', r'(?i)\bemail\b', r'(?i)\baddress\b',
        r'(?i)\bstreet\b', r'(?i)\bcity\b', r'(?i)\bstate\b',
        r'(?i)\b(zip[-\s]?code|zipcode|postal[-\s]?code)\b',
        r'(?i)\bphone\b', r'(?i)\bip[\s._-]*address\b', r'(?i)\bdate[\s._-]*of[\s._-]*birth\b',
        r'(?i)\bage\b', r'(?i)\brace\b', r'(?i)\bethnicity\b',
        r'(?i)\bbank[\s._-]*(name|code|id|branch|account)\b',
        r'(?i)\baccount[\s._-]*(name|number)\b', r'(?i)\brouting\b',
        r'(?i)\bbalance\b', r'(?i)\blast[\s._-]*4\b', r'(?i)\bpassword\b',
        r'(?i)\bhint\b', r'(?i)\breminder\b', r'(?i)\bpatient[\s._-]*id\b',
        r'(?i)\b(result|results|lab|labs|test)\b', r'(?i)\bfamily[\s._-]*history\b'
    ]

    # Initialize a list to store flagged properties
    flagged_properties = []

    # Check each property against detection rules
    for _, row in event_props_df.iterrows():
        property_name = row["Event Property Name"]
        reason = []

        # Check keyword-based rules
        for rule, pattern in keyword_patterns.items():
            if re.match(pattern, property_name, re.IGNORECASE):
                reason.append(rule)

        # Check if the property matches PII patterns
        for pii_pattern in pii_patterns:
            if re.match(pii_pattern, property_name, re.IGNORECASE):
                reason.append("User Identifying Data Match")
                break  # No need to check more PII patterns if one match is found

        # If any rule matched, add the property to the flagged list
        if reason:
            flagged_properties.append({
                "Event Property Name": property_name,
                "Reason for Flagging": ", ".join(reason)
            })

    # Convert list to DataFrame
    flagged_properties_df = pd.DataFrame(flagged_properties)

    return flagged_properties_df

