# analysis.py
# Functions for additional analysis

import pandas as pd
import os
import numpy as np
import re
from rapidfuzz import process, fuzz
from utils.config import OUTPUT_DIR
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from utils.data_processing import identify_duplicate_events


def find_match(name, idx, comp_list, orig_idx_col, names_col, threshold):
    """
    Finds the best match for a given name within a list of names, excluding itself.
    Also returns the category in which the match was found.
    """
    # Exclude the current index to avoid matching with itself
    comparison_list = comp_list[comp_list[orig_idx_col] != idx]
    choices = comparison_list[names_col].tolist()

    # extractOne returns a tuple: (best_match, score, match_index)
    # match_index is the index of the match within 'choices'
    match = process.extractOne(
        name,
        choices,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=threshold
    )
    if match is not None and match[1] >= threshold:
        best_match_name, score, match_idx_in_choices = match
        # Retrieve the category using match_idx_in_choices
        # This maps back to comparison_list since 'choices' came from comparison_list[names_col]
        matched_row = comparison_list.iloc[match_idx_in_choices]
        matched_category = matched_row['Category']
        return (best_match_name, score, matched_row[orig_idx_col], matched_category)
    else:
        return (pd.NA, pd.NA, pd.NA, pd.NA)


def matcher(df, orig_idx_col, names_col, threshold):
    """
    Applies find_match across the DataFrame to find matches for all names.
    Also includes the category of the match found.
    """
    # Include 'Category' in comp_list so we can retrieve it after matching
    comp_list = df[[orig_idx_col, names_col, 'Category']].copy()

    # Apply find_match to each row
    # find_match now returns 4 items: (Match Found, Match Score, Match Index, Match Category)
    df[['Match Found', 'Match Score', 'Match Index', 'Match Category']] = df.apply(
        lambda row: pd.Series(
            find_match(
                row[names_col],
                row[orig_idx_col],
                comp_list,
                orig_idx_col,
                names_col,
                threshold
            )
        ),
        axis=1
    )

    # Replace NA/None values with 0
    df['Match Score'] = pd.to_numeric(df['Match Score'], errors='coerce')
    df['Match Score'] = df['Match Score'].fillna(0)
    # Round the Match Score
    df['Match Score'] = df['Match Score'].round(2)

    return df


def event_counts(events_df, name=''):
    """
    Calculates counts and percentages of event schema statuses.

    Parameters:
    - events_df (pd.DataFrame): The DataFrame containing event data.
    - name (str): An optional name for the dataset or project.

    Returns:
    - pd.DataFrame: A DataFrame with counts and percentages of event schema statuses.
    """

    # Check if 'Object Type' column exists
    if 'Object Type' not in events_df.columns:
        print("Column 'Object Type' not found in DataFrame.")
        return None

    # Filter the DataFrame to include only events
    events_only_df = events_df[events_df['Object Type'] == 'Event']

    # Check if 'Event Schema Status' column exists
    if 'Event Schema Status' not in events_only_df.columns:
        print("Column 'Event Schema Status' not found in DataFrame.")
        return None

    # Calculate counts and percentages
    counts = events_only_df['Event Schema Status'].value_counts(dropna=False)
    percentages = events_only_df['Event Schema Status'].value_counts(dropna=False, normalize=True) * 100  # Convert to percentage

    # Create a DataFrame with counts and percentages
    counts_df = pd.DataFrame({
        'Event Schema Status': counts.index,
        'Counts': counts.values,
        'Percentage': percentages.values
    })

    # Reset index to ensure 'Event Schema Status' is a column
    counts_df.reset_index(drop=True, inplace=True)

    # Optionally, add the dataset or project name
    if name:
        counts_df['Dataset Name'] = name

    # Rearrange columns if 'Dataset Name' is included
    if 'Dataset Name' in counts_df.columns:
        counts_df = counts_df[['Dataset Name', 'Event Schema Status', 'Counts', 'Percentage']]
    else:
        counts_df = counts_df[['Event Schema Status', 'Counts', 'Percentage']]

    return counts_df

def event_properties_counts(dedup_df, name=''):
    if 'Property Schema Status' not in dedup_df.columns:
        return pd.DataFrame()

    counts = dedup_df['Property Schema Status'].value_counts(dropna=False)
    percentages = counts / counts.sum() * 100  # Calculate percentage

    df = pd.DataFrame({
        'Property Schema Status': counts.index,
        'Counts': counts.values,
        'Percentage': percentages.values
    })
    df.reset_index(drop=True, inplace=True)

    if name:
        df['Project'] = name

    return df

def user_properties_counts(user_props_df, name=''):
    if 'Property Schema Status' not in user_props_df.columns:
        return pd.DataFrame()

    counts = user_props_df['Property Schema Status'].value_counts(dropna=False)
    percentages = counts / counts.sum() * 100  # Calculate percentage

    df = pd.DataFrame({
        'Property Schema Status': counts.index,
        'Counts': counts.values,
        'Percentage': percentages.values
    })
    df.reset_index(drop=True, inplace=True)

    if name:
        df['Project'] = name

    return df

def generate_wordcloud(text, output_path, max_words=200, background_color="white"):
    """Generate and save a word cloud image from the given text."""
    wc = WordCloud(
        background_color=background_color,
        max_words=max_words,
        width=800,
        height=400
    )
    wc.generate(text)
    wc.to_file(output_path)
    print(f"Word cloud saved at {output_path}")


def create_event_wordclouds(events_df, project_output_dir):
    # Create a subdirectory for wordclouds
    wc_dir = os.path.join(project_output_dir, "wordclouds")
    os.makedirs(wc_dir, exist_ok=True)

    # Word cloud for Object Name
    if 'Object Name' in events_df.columns:
        text_data = events_df['Object Name'].dropna().astype(str).tolist()
        combined_text = " ".join(text_data)
        wc_path = os.path.join(wc_dir, "events_display_name_wordcloud.png")
        generate_wordcloud(combined_text, wc_path)
    else:
        print("Warning: 'Object Namee' column not found in events_df.")

    # # Word cloud for Event Description
    # if 'Object Description' in events_df.columns:
    #     text_data_desc = events_df['Object Description'].dropna().astype(str).tolist()
    #     combined_text_desc = " ".join(text_data_desc)
    #     wc_path_desc = os.path.join(wc_dir, "events_description_wordcloud.png")
    #     generate_wordcloud(combined_text_desc, wc_path_desc)
    # else:
    #     print("Warning: 'Object Description' column not found in events_df.")


def create_event_props_wordcloud(event_props_df, project_output_dir):
    wc_dir = os.path.join(project_output_dir, "wordclouds")
    os.makedirs(wc_dir, exist_ok=True)

    # Word cloud for Event Property Name
    if 'Event Property Name' in event_props_df.columns:
        text_data = event_props_df['Event Property Name'].dropna().astype(str).tolist()
        combined_text = " ".join(text_data)
        wc_path = os.path.join(wc_dir, "event_props_name_wordcloud.png")
        generate_wordcloud(combined_text, wc_path)
    else:
        print("Warning: 'Event Property Name' column not found in event_props_df.")

    # # Word cloud for Property Description
    # if 'Property Description' in event_props_df.columns:
    #     text_data_desc = event_props_df['Property Description'].dropna().astype(str).tolist()
    #     combined_text_desc = " ".join(text_data_desc)
    #     wc_path_desc = os.path.join(wc_dir, "event_props_description_wordcloud.png")
    #     generate_wordcloud(combined_text_desc, wc_path_desc)
    # else:
    #     print("Warning: 'Property Description' column not found in event_props_df.")


def create_user_props_wordcloud(user_props_df, project_output_dir):
    wc_dir = os.path.join(project_output_dir, "wordclouds")
    os.makedirs(wc_dir, exist_ok=True)

    # Word cloud for Property Name
    if 'Property Name' in user_props_df.columns:
        text_data = user_props_df['Property Name'].dropna().astype(str).tolist()
        combined_text = " ".join(text_data)
        wc_path = os.path.join(wc_dir, "user_props_name_wordcloud.png")
        generate_wordcloud(combined_text, wc_path)
    else:
        print("Warning: 'Property Name' column not found in user_props_df.")

    # # Word cloud for Property Description
    # if 'Property Description' in user_props_df.columns:
    #     text_data_desc = user_props_df['Property Description'].dropna().astype(str).tolist()
    #     combined_text_desc = " ".join(text_data_desc)
    #     wc_path_desc = os.path.join(wc_dir, "user_props_description_wordcloud.png")
    #     generate_wordcloud(combined_text_desc, wc_path_desc)
    # else:
    #     print("Warning: 'Property Description' column not found in user_props_df.")

def generate_pii_report(event_props_matched, user_props_matched, project_output_dir):
    # Define patterns for PII detection
    pii_patterns = [
        r'(?i)\bfirst[\s._-]*name\b',        # first name
        r'(?i)\blast[\s._-]*name\b',         # last name / surname
        r'(?i)\bfull[\s._-]*name\b',         # full name
        r'(?i)\bsurname\b',                  # surname
        r'(?i)\bname\b',                      # generic name (broad match)
        r'(?i)\bemail\b',                     # email
        r'(?i)\baddress\b',                   # address (single word)
        r'(?i)\bstreet\b',                    # street
        r'(?i)\bcity\b',                      # city
        r'(?i)\bstate\b',                     # state
        r'(?i)\b(zip[-\s]?code|zipcode|postal[-\s]?code)\b',  # zip code / postal code
        r'(?i)\bphone\b',                     # phone number    
        r'(?i)\bip[\s._-]*address\b',         # IP address
        r'(?i)\bdate[\s._-]*of[\s._-]*birth\b',  # date of birth
        r'(?i)\bage\b',                       # age
        r'(?i)\brace\b',                      # race
        r'(?i)\bethnicity\b',                 # ethnicity
        r'(?i)\bbank[\s._-]*(name|code|id|branch|account)\b',  # bank-related details
        r'(?i)\baccount[\s._-]*(name|number)\b',  # account-related details
        r'(?i)\brouting\b',                    # routing number
        r'(?i)\bbalance\b',                    # balance (bank balance)
        r'(?i)\blast[\s._-]*4\b',               # last 4 digits (account, card, etc.)
        r'(?i)\bpassword\b',                    # password
        r'(?i)\bhint\b',                        # password hint
        r'(?i)\breminder\b',                    # password reminder
        r'(?i)\bpatient[\s._-]*id\b',           # patient ID
        r'(?i)\b(result|results|lab|labs|test)\b',  # lab/test results
        r'(?i)\bfamily[\s._-]*history\b'        # family history
    ]

    def check_pii(value, patterns):
        """Check if the given value matches any PII patterns."""
        return any(re.search(pattern, value) for pattern in patterns)

    print("Generating PII report...")

    # Filter Event Properties for PII
    event_pii = pd.DataFrame()
    if not event_props_matched.empty and 'Event Property Name' in event_props_matched.columns:
        event_pii = event_props_matched[event_props_matched['Event Property Name'].apply(lambda x: check_pii(str(x), pii_patterns))]
        if not event_pii.empty:
            event_pii = event_pii[['Orig Index', 'Event Property Name', 'Project']]

    # Filter User Properties for PII
    user_pii = pd.DataFrame()
    if not user_props_matched.empty and 'Property Name' in user_props_matched.columns:
        user_pii = user_props_matched[user_props_matched['Property Name'].apply(lambda x: check_pii(str(x), pii_patterns))]
        if not user_pii.empty:
            user_pii = user_pii[['Orig Index', 'Property Name', 'Project']]

    # Excel output
    pii_report_path = os.path.join(project_output_dir, "user_identifying_data_report.xlsx")

    with pd.ExcelWriter(pii_report_path, engine='openpyxl') as writer:
        sheets_created = False  # Track if sheets were added
        
        if not event_pii.empty:
            event_pii.to_excel(writer, sheet_name='Event_Properties_PII', index=False)
            sheets_created = True
        
        if not user_pii.empty:
            user_pii.to_excel(writer, sheet_name='User_Properties_PII', index=False)
            sheets_created = True
        
        # Add a default "No Data" sheet if no other sheets were created
        if not sheets_created:
            pd.DataFrame({"Message": ["No PII found for this project."]}) \
              .to_excel(writer, sheet_name="No Data", index=False)
            print("No PII found for this project.")

    print(f"PII report saved to {pii_report_path}")

    # Return detected PII dataframes (empty or not)
    return event_pii, user_pii


def get_top_duplicate_events_by_volume(usage_df, lookback_window=30, top_n=10):
    """
    Groups duplicate events by identical event volume and returns the top N results.

    Parameters:
        usage_df (pd.DataFrame): DataFrame containing the usage report.
        lookback_window (int): The selected look-back window (30, 90, 180, 270, 365 days).
        top_n (int): Number of top duplicate groups to return.

    Returns:
        pd.DataFrame: A DataFrame with columns:
            - "Event Name List" (comma-separated event names)
            - "Volume" (shared event volume)
    """
    # Identify duplicate events using the existing function
    duplicate_events_df = identify_duplicate_events(usage_df, lookback_window)

    volume_col = f"{lookback_window} Day Volume"

    if duplicate_events_df.empty or volume_col not in duplicate_events_df.columns:
        return pd.DataFrame(columns=["Event Name List", "Volume"])

    # Group by volume and concatenate event names into a single row
    grouped_df = (
        duplicate_events_df.groupby(volume_col)["Event Name"]
        .apply(lambda x: ", ".join(x))
        .reset_index()
        .rename(columns={"Event Name": "Event Name List", volume_col: "Volume"})
    )

    # Sort by volume descending and limit results
    grouped_df = grouped_df.sort_values(by="Volume", ascending=False).head(top_n)

    return grouped_df

def event_properties_status_counts(dedup_df, name=''):
    """
    Calculates counts and percentages of event property statuses
    by grouping on 'Property Schema Status' and counting unique 'Event Property Name'.

    Parameters:
        dedup_df (pd.DataFrame): The DataFrame containing deduplicated event properties.
        name (str): Optional project name (kept internally but dropped before returning).

    Returns:
        pd.DataFrame: Columns [Property Schema Status, Counts, Percentage],
                      with the 'Percentage' column formatted to two decimals and appended '%'.
    """
    if dedup_df.empty:
        return pd.DataFrame(columns=['Property Schema Status', 'Counts', 'Percentage'])

    needed_cols = {'Event Property Name', 'Property Schema Status'}
    if not needed_cols.issubset(set(dedup_df.columns)):
        print("Required columns are missing from dedup_df.")
        return pd.DataFrame()

    # Group by status and count unique property names
    grouped = dedup_df.groupby('Property Schema Status')['Event Property Name'].nunique()

    # Convert to DataFrame
    df_counts = pd.DataFrame({
        'Property Schema Status': grouped.index,
        'Counts': grouped.values
    })

    # Calculate percentage
    total = df_counts['Counts'].sum()
    df_counts['Percentage'] = (df_counts['Counts'] / total) * 100
    df_counts['Percentage'] = df_counts['Percentage'].map(lambda x: f"{x:.2f}%")

    # If you want to store the Project name for potential debugging...
    if name:
        df_counts['Project'] = name

    df_counts.reset_index(drop=True, inplace=True)

    # Just drop 'Project' before returning, so final output won't have it
    if 'Project' in df_counts.columns:
        df_counts.drop(columns='Project', inplace=True)

    return df_counts

def user_properties_status_counts(user_props_df, name=''):
    """
    Calculates counts and percentages of user property statuses
    by grouping on 'Property Schema Status' and counting unique 'Property Name'.

    Parameters:
        user_props_df (pd.DataFrame): The DataFrame containing processed user properties.
        name (str): Optional project name (temporarily added, then dropped for final output).

    Returns:
        pd.DataFrame: Columns [Property Schema Status, Counts, Percentage]
                      with 'Percentage' as a string formatted to two decimals + '%'.
    """
    # If DataFrame empty, return the structure
    if user_props_df.empty:
        return pd.DataFrame(columns=['Property Schema Status', 'Counts', 'Percentage'])

    # Ensure needed columns exist
    needed_cols = {'Property Name', 'Property Schema Status'}
    if not needed_cols.issubset(user_props_df.columns):
        print("Required columns are missing from user_props_df.")
        return pd.DataFrame()

    # Group by 'Property Schema Status' and count unique 'Property Name'
    grouped = user_props_df.groupby('Property Schema Status')['Property Name'].nunique()

    # Construct new DataFrame
    df_counts = pd.DataFrame({
        'Property Schema Status': grouped.index,
        'Counts': grouped.values
    })

    # Compute percentages
    total = df_counts['Counts'].sum()
    df_counts['Percentage'] = (df_counts['Counts'] / total) * 100
    # Format: "xx.xx%"
    df_counts['Percentage'] = df_counts['Percentage'].map(lambda x: f"{x:.2f}%")

    # Optionally store 'Project' internally
    if name:
        df_counts['Project'] = name

    # Move 'Project' in case you want to see it for debugging...
    df_counts.reset_index(drop=True, inplace=True)

    # ...but drop it from final output
    if 'Project' in df_counts.columns:
        df_counts.drop(columns='Project', inplace=True)

    return df_counts