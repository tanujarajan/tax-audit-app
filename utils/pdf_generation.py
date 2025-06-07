from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from xml.sax.saxutils import escape
import os
import pandas as pd

# ─────────────────────────────────────────────────────
# GLOBAL HELPERS
# ─────────────────────────────────────────────────────

# We'll create one global styles object that each helper can reuse.
styles = getSampleStyleSheet()

def measure_paragraph_height(text, style_name, max_width):
    """
    Returns the height needed to draw the paragraph without actually drawing it.
    """
    paragraph = Paragraph(text, styles[style_name])
    # wrap() returns (width, height) that the paragraph needs
    _, paragraph_height = paragraph.wrap(max_width, 0)
    return paragraph_height

def draw_wrapped_text(canvas_obj, text, style_name, x, y, max_width):
    """
    Draws the given text in a Paragraph at (x, y), wrapping
    within 'max_width'. Returns the updated y-position.
    """
    paragraph = Paragraph(text, styles[style_name])
    # We pass 'y' for the available height, but it doesn't strictly matter
    # if we handle page breaks ourselves. It's part of the normal
    # 'platypus' approach though.
    _, paragraph_height = paragraph.wrap(max_width, y)
    paragraph.drawOn(canvas_obj, x, y - paragraph_height)
    return y - paragraph_height - 10  # 10 is just a spacing buffer

def check_and_page_break(canvas_obj, needed_height, y_position, page_height, bottom_margin=50):
    """
    Checks if there's enough space for 'needed_height' at the current y_position.
    If not, forces a page break and resets y_position near the top of the new page.
    Returns the updated y_position (either unchanged or reset).
    """
    # If there's not enough space for the needed_height plus a bottom margin,
    # start a new page.
    if (y_position - needed_height) < bottom_margin:
        canvas_obj.showPage()
        return page_height - 50  # Something near the top of the new page
    else:
        return y_position

# ─────────────────────────────────────────────────────
# FORMATTING HELPERS FOR CONSISTENT SECTION STRUCTURE
# ─────────────────────────────────────────────────────

# Constants for alignment and spacing
LEFT_MARGIN = 50
INDENT_MARGIN = 50
SUBSECTION_SPACING = 8  # Space between subsection elements
SECTION_SPACING = 25  # Space between sections
TITLE_SPACING = 8  # Space below section title
HEADER_SPACING = 5  # Space below headers like "Context:" and "Importance:"
TABLE_BOTTOM_SPACING = 15  # Space below table before next section

def draw_section_title(canvas_obj, title_text, x, y, page_width, page_height):
    """
    Draws a bold section title and returns the updated y position.
    """
    y = check_and_page_break(canvas_obj, TITLE_SPACING + 14, y, page_height)
    # Draw label
    canvas_obj.setFont("Helvetica-Bold", 14)
    canvas_obj.drawString(x, y, title_text)
    return y - TITLE_SPACING

def draw_subheader_text(canvas_obj, subheader_text, x, y, page_width, page_height):
    """
    Draws the italic subheader text and returns the updated y position.
    """
    needed_height = measure_paragraph_height(subheader_text, "Italic", page_width - 100)
    y = check_and_page_break(canvas_obj, needed_height, y, page_height)
    return draw_wrapped_text(canvas_obj, subheader_text, "Italic", x, y, page_width - 100)

def draw_context_text(canvas_obj, context_text, x, y, page_width, page_height):
    """
    Draws the 'Context' label and its text. Returns the updated y position.
    """
    needed_height = measure_paragraph_height(context_text, "BodyText", page_width - 120)
    y = check_and_page_break(canvas_obj, needed_height + HEADER_SPACING, y, page_height)
    # Draw label
    canvas_obj.setFont("Helvetica-Bold", 12)
    canvas_obj.drawString(x, y, "Context:")
    y -= HEADER_SPACING
    return draw_wrapped_text(canvas_obj, context_text, "BodyText", INDENT_MARGIN, y, page_width - 120)

def draw_importance_text(canvas_obj, importance_text, x, y, page_width, page_height):
    """
    Draws the 'Importance' label and its text. Returns the updated y position.
    """
    needed_height = measure_paragraph_height(importance_text, "BodyText", page_width - 120)
    y = check_and_page_break(canvas_obj, needed_height + HEADER_SPACING, y, page_height)
    # Draw label
    canvas_obj.setFont("Helvetica-Bold", 12)
    canvas_obj.drawString(x, y, "Importance:")
    y -= HEADER_SPACING
    return draw_wrapped_text(canvas_obj, importance_text, "BodyText", INDENT_MARGIN, y, page_width - 120)

def draw_table(canvas_obj, table_data, x, y_position, page_width, page_height, col_widths=None, table_style=None):
    """
    Draws a table with dynamic column widths and styles. If there isn't enough space, it moves to a new page.

    Parameters:
        canvas_obj (Canvas): The ReportLab canvas object.
        table_data (list): List of rows, where each row is a list of cell values.
        x (int): X-coordinate (usually LEFT_MARGIN).
        y_position (int): Current Y position on the page.
        page_width (int): Width of the page.
        page_height (int): Height of the page.
        col_widths (list, optional): List of column widths. If None, it will distribute evenly within margins.
        table_style (TableStyle, optional): Custom table styling. Defaults to standard grid.

    Returns:
        int: Updated Y position after drawing the table.
    """
    if not table_data or len(table_data) == 0:
        return y_position  # If there's no data, do nothing

    styles = getSampleStyleSheet()

    # Convert table_data to wrapped paragraphs to ensure proper text formatting
    wrapped_data = []
    for row in table_data:
        wrapped_row = [Paragraph(str(cell), styles["BodyText"]) for cell in row]
        wrapped_data.append(wrapped_row)

    # Define the right margin
    RIGHT_MARGIN = 50

    # Adjust column width based on left & right margins
    usable_width = page_width - (LEFT_MARGIN + RIGHT_MARGIN)

    # Default column width: distribute evenly if not provided
    num_columns = len(table_data[0])
    if col_widths is None:
        col_widths = [usable_width / num_columns] * num_columns  # Fit within margins

    # Create the table
    table = Table(wrapped_data, colWidths=col_widths)

    # Apply default style if none provided
    if table_style is None:
        table_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 1, colors.black)
        ])

    table.setStyle(table_style)

    # Measure the height required for the table
    _, table_height = table.wrap(usable_width, y_position)

    # Check if the table fits on the page, else move to a new page
    if (y_position - table_height) < 50:  # 50px bottom margin
        canvas_obj.showPage()
        y_position = page_height - 50  # Reset near the top

    # Draw the table (x-position is LEFT_MARGIN, ensuring right margin padding)
    table.drawOn(canvas_obj, x, y_position - table_height)

    return y_position - table_height - TABLE_BOTTOM_SPACING  # Move cursor down after table


def draw_next_steps_text(canvas_obj, next_steps_text, x, y, page_width, page_height):
    """
    Draws the 'Next Steps' label and its text. Returns the updated y position.
    """
    needed_height = measure_paragraph_height(next_steps_text, "BodyText", page_width - 120)
    y = check_and_page_break(canvas_obj, needed_height + HEADER_SPACING, y, page_height)
    # Draw label
    canvas_obj.setFont("Helvetica-Bold", 12)
    canvas_obj.drawString(x, y, "Next Steps:")
    y -= HEADER_SPACING
    return draw_wrapped_text(canvas_obj, next_steps_text, "BodyText", INDENT_MARGIN, y, page_width - 120)

def draw_related_report_text(canvas_obj, file_name, x, y, page_width, page_height):
    """
    Draws the 'Related Report' label and its text. Returns the updated y position.
    """
    needed_height = measure_paragraph_height(file_name, "BodyText", page_width - 120)
    y = check_and_page_break(canvas_obj, needed_height + HEADER_SPACING, y, page_height)
    # Draw label
    canvas_obj.setFont("Helvetica-Bold", 12)
    canvas_obj.drawString(x, y, "Related Report File:")
    y -= HEADER_SPACING
    return draw_wrapped_text(canvas_obj, file_name, "BodyText", INDENT_MARGIN, y, page_width - 120)


# ─────────────────────────────────────────────────────
# PDF GENERATION
# ─────────────────────────────────────────────────────

def generate_project_pdf(
    project_name,
    output_path,
    duplicate_counts_df,
    duplicate_events_volume_df,
    event_pii,
    user_pii,
    event_counts_df=None,
    event_props_counts_df=None,
    user_props_counts_df=None,
    syntax_summary_df=None,
    missing_summary_df=None,
    top_unused_events_df=None,
    bottom_unused_events_df=None,
    lookback_window=None,
    flagged_misclass_summary_df=None,
    stale_events_df=None,
    stale_properties_df=None,
    stale_user_props_df=None,
    single_day_events_df=None,
    single_day_properties_df=None,
    single_day_user_props_df=None 
):
    """
    Generates a PDF report for a given project.
    """
    try:
        c = canvas.Canvas(output_path, pagesize=LETTER)
        width, height = LETTER

        # Set title
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2, height - 50, f"Project Report: {project_name}")

        y_position = height - 100  # Adjust vertical positioning

        # Debugging: Ensure DataFrame is populated
        print(f"Checking duplicate_counts_df for {project_name}:")
        print(duplicate_counts_df)

        # Ensure duplicate events table data is formatted properly before passing
        duplicate_counts_data = (
            [duplicate_counts_df.columns.tolist()] + duplicate_counts_df.values.tolist()
            if not duplicate_counts_df.empty else [["No Data"]]
        )

        # Add 'Duplicate Events by Name' section even if empty (so format remains consistent)
        y_position = add_duplicate_events_by_name_section(
            c,
            title="Duplicate Events and Properties by Name",
            subheader="Events and Properties where duplicates have been found based on name.",
            context="Multiple Events and Properties can be ingested in Amplitude with nearly "
            "identical names and show up as different Events or Properties. Separate event and "
            "property tracking can also happen because Amplitude is case sensitive",
            importance="Duplication across event and property names will make the analysis"
            "harder by confusing users on which events or properties are the correct choice and"
            "result in data trust issues.",
            table_data=duplicate_counts_data,  # Ensure it's always passed correctly
            next_steps="We recommend reviewing duplicate events and "
            '<font color="blue"><u><a href="https://amplitude.com/docs/faq/hide-block-or-delete-and-event-or-property">'
            'hiding, blocking or deleting</a></u></font>'
            " those that are no longer needed. Amplitude allows you "
            '<font color="blue"><u><a href="https://amplitude.com/docs/data/transformations">'
            'transform</a></u></font>'
            " events or properties,"
            "but we also recommend reviewing tracking at the data source to clean up and "
            "implementing governance procedures such as a taxonomy guide to ensure data cleanliness"
            "long term.",
            y_position=y_position,
            page_width=width,
            page_height=height
        )

        # Ensure duplicate events by volume table data is formatted properly before passing
        duplicate_events_volume_data = (
            [duplicate_events_volume_df.columns.tolist()] + duplicate_events_volume_df.values.tolist()
            if not duplicate_events_volume_df.empty else [["No Data"]]
        )

        # Add 'Duplicate Events by Volume' section
        y_position = add_duplicate_events_by_volume_section(
            c,
            title="Duplicate Events by Volume",
            subheader="Events where the event volume is identical to other events within the same lookback window.",
            context="Do not track 2 events for 1 action (e.g. 'search clicked' and 'search results displayed')."
            "If there is no drop-off to measure between the 2 events, then it is not necessary to track both.",
            importance="Duplication across tracked event data will make the analysis harder and result in data "
            "trust issues. Tracking the same action multiple times also inflates your event volume without adding "
            "any additional value.",
            table_data=duplicate_events_volume_data,  # Ensure it's always passed correctly
            next_steps="We recommend choosing one event for one user action and updating your instrumentation to "
            "track that event going forward. Any duplicate events identified in this list should be fixed in your "
            "instrumentation and "
            '<font color="blue"><u><a href="https://amplitude.com/docs/data/transformations">'
            'transformed</a></u></font>'
            " in Amplitude. If any of these events are no longer used and not required "
            "for your analysis, considering cleaning up your taxonomy by "
            '<font color="blue"><u><a href="https://amplitude.com/docs/faq/hide-block-or-delete-and-event-or-property">'
            'hiding, blocking or deleting</a></u></font>'
            " those.",
            y_position=y_position,
            page_width=width,
            page_height=height
        )

        # Add User Identifying Data Detected Section
        y_position = add_user_identifying_data_section(c, event_pii, user_pii, y_position, width, height)

        # 4) New Event & Property Status Section
        y_position = add_event_and_prop_status_section(
            c,
            event_counts_df if event_counts_df is not None else pd.DataFrame(),
            event_props_counts_df if event_props_counts_df is not None else pd.DataFrame(),
            user_props_counts_df if user_props_counts_df is not None else pd.DataFrame(),
            y_position,
            width,
            height
        )
        
        # Add Syntax Summary Section
        y_position = add_syntax_summary_section(
            c,
            syntax_summary_df if syntax_summary_df is not None else pd.DataFrame(),
            y_position,
            width,
            height
        )

        # Add Top 10 and Bottom 10 Unused Events By Volume
        y_position = add_unused_events_section(
            c,
            top_unused_events_df if top_unused_events_df is not None else pd.DataFrame(),
            bottom_unused_events_df if bottom_unused_events_df is not None else pd.DataFrame(),
            y_position,
            width,
            height,
            lookback_window  # Ensure this variable is available in `generate_project_pdf`
        )

        # Add Event Property Misclassification Summary Section
        y_position = add_event_prop_misclassification_section(
            c,
            flagged_misclass_summary_df if flagged_misclass_summary_df is not None else pd.DataFrame(),
            y_position,
            width,
            height
        )


        # Add Missing Category And Description Summary Section
        y_position = add_missing_categories_descriptions_section(
            c,
            missing_summary_df if missing_summary_df is not None else pd.DataFrame(),
            y_position,
            width,
            height
        )

        # Add Stale Items Summary Section
        y_position = add_stale_items_section(
            c,
            stale_events_df if stale_events_df is not None else pd.DataFrame(),
            stale_properties_df if stale_properties_df is not None else pd.DataFrame(),
            stale_user_props_df if stale_user_props_df is not None else pd.DataFrame(),
            y_position,
            width,
            height
        )


        # Add Single Day Items Summary Section
        y_position = add_single_day_items_section(
            c,
            single_day_events_df if single_day_events_df is not None else pd.DataFrame(),
            single_day_properties_df if single_day_properties_df is not None else pd.DataFrame(),
            single_day_user_props_df if single_day_user_props_df is not None else pd.DataFrame(),
            y_position,
            width,
            height
        )

        
        # Save the PDF
        c.save()
        print(f"✅ PDF successfully generated: {output_path}")

    except Exception as e:
        print(f"❌ Error generating PDF: {e}")

# ─────────────────────────────────────────────────────
# CONTENT SECTIONS
# ─────────────────────────────────────────────────────

def add_duplicate_events_by_name_section(canvas_obj, title, subheader, context, importance, table_data, next_steps, y_position, page_width, page_height):

    """
    Adds the 'Duplicate Events by Name' section to the PDF with dynamic spacing.
    """

    TEXT_WIDTH = page_width - 120

    file_name = (
        "matched_results.xlsx"
    )

    # Draw section title
    y_position = draw_section_title(canvas_obj, title, LEFT_MARGIN, y_position, page_width, page_height)

    # Draw subheader
    y_position = draw_subheader_text(canvas_obj, subheader, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # Draw context
    y_position = draw_context_text(canvas_obj, context, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # Draw importance
    y_position = draw_importance_text(canvas_obj, importance, LEFT_MARGIN, y_position, page_width, page_height)

    # Table Data (if available)
    if table_data and len(table_data) > 1:
         num_columns = len(table_data[0])
 
         if num_columns == 4:
             col_widths = [
                 page_width * 0.2,  # Object Type
                 page_width * 0.2,  # Events
                 page_width * 0.2,  # Event Property
                 page_width * 0.2  # User Property
             ]
         else:
             col_widths = [page_width / num_columns] * num_columns
 
         # Wrap text inside table cells
         table_data_wrapped = []
         for row in table_data:
             wrapped_row = [Paragraph(str(cell), styles["BodyText"]) if isinstance(cell, str) else cell for cell in row]
             table_data_wrapped.append(wrapped_row)
 
         table = Table(table_data_wrapped, colWidths=col_widths)
         table.setStyle(TableStyle([
             ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
             ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
             ("ALIGN", (0, 0), (-1, -1), "LEFT"),
             ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
             ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
             ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
             ("GRID", (0, 0), (-1, -1), 1, colors.black)
         ]))
 
         # Ensure the table is fully drawn within the available space
         _, table_height = table.wrap(page_width, y_position)
 
         table.drawOn(canvas_obj, LEFT_MARGIN, y_position - table_height)
         y_position -= table_height + TABLE_BOTTOM_SPACING  # Move down after table


    y_position -= SUBSECTION_SPACING
    # Draw next steps
    y_position = draw_next_steps_text(canvas_obj, next_steps, LEFT_MARGIN, y_position, page_width, page_height)
    
    y_position -= SUBSECTION_SPACING
    # Draw Related Report File
    y_position = draw_related_report_text(canvas_obj, file_name, LEFT_MARGIN, y_position, page_width, page_height)
    
    # Add spacing before the next section
    y_position -= SECTION_SPACING

    return y_position


def get_exact_duplicate_counts_matrix(events_matched, event_props_matched, user_props_matched, project_name):
    """
    Generates a pivot table summarizing exact duplicate counts (Match Score = 100)
    using separate DataFrames for Events, Event Properties, and User Properties.

    Parameters:
        events_matched (pd.DataFrame): Project-specific DataFrame for event duplicates.
        event_props_matched (pd.DataFrame): Project-specific DataFrame for event property duplicates.
        user_props_matched (pd.DataFrame): Project-specific DataFrame for user property duplicates.
        project_name (str): The name of the project being processed.

    Returns:
        pd.DataFrame: Pivot table showing duplicate counts across categories.
    """
    if events_matched.empty and event_props_matched.empty and user_props_matched.empty:
        return pd.DataFrame(columns=["Object Type", "Event", "Event Property", "User Property"])

    # Ensure we're only looking at exact duplicates (Match Score = 100)
    exact_events = events_matched[events_matched['Match Score'] == 100]
    exact_event_props = event_props_matched[event_props_matched['Match Score'] == 100]
    exact_user_props = user_props_matched[user_props_matched['Match Score'] == 100]

    # Count occurrences for each type
    event_counts = exact_events.groupby("Match Category").size().rename("Event")
    event_props_counts = exact_event_props.groupby("Match Category").size().rename("Event Property")
    user_props_counts = exact_user_props.groupby("Match Category").size().rename("User Property")

    # Combine counts into a single DataFrame
    duplicate_counts_df = pd.concat([event_counts, event_props_counts, user_props_counts], axis=1).fillna(0)

    # Ensure standard column order
    order = ["Event", "Event Property", "User Property"]
    duplicate_counts_df = duplicate_counts_df.reindex(columns=order, fill_value=0)

    # Reset index so "Object Type" becomes a column
    duplicate_counts_df = duplicate_counts_df.reset_index().rename(columns={"Match Category": "Object Type"})

    return duplicate_counts_df

def add_duplicate_events_by_volume_section(canvas_obj, title, subheader, context, importance, table_data, next_steps, y_position, page_width, page_height):
    """
    Adds the 'Duplicate Events by Volume' section to the PDF with dynamic spacing.
    """
    styles = getSampleStyleSheet()
    
    # Constants for alignment and spacing
    TEXT_WIDTH = page_width - 120

    file_name = (
        "duplicate_events_report.xlsx"
    )

    # Draw section title
    y_position = draw_section_title(canvas_obj, title, LEFT_MARGIN, y_position, page_width, page_height)

    # Draw subheader
    y_position = draw_subheader_text(canvas_obj, subheader, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # Draw context
    y_position = draw_context_text(canvas_obj, context, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # Draw importance
    y_position = draw_importance_text(canvas_obj, importance, LEFT_MARGIN, y_position, page_width, page_height)
    
    # Table Data (if available)
    if table_data and len(table_data) > 1:
        col_widths = [page_width * 0.15, page_width * 0.7] 

        # Wrap text inside table cells
        table_data_wrapped = []
        for row in table_data:
            wrapped_row = [Paragraph(str(cell), styles["BodyText"]) if isinstance(cell, str) else cell for cell in row]
            table_data_wrapped.append(wrapped_row)

        table = Table(table_data_wrapped, colWidths=col_widths)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 1, colors.black)
        ]))

        # Ensure the table is fully drawn within the available space
        _, table_height = table.wrap(page_width, y_position)
        if y_position - table_height < 50:  # Ensure there's enough space on the page
            canvas_obj.showPage()
            y_position = page_height - 50 # Reset Y position on new page

        table.drawOn(canvas_obj, LEFT_MARGIN, y_position - table_height)
        y_position -= table_height + TABLE_BOTTOM_SPACING  # Move down after table

    y_position -= SUBSECTION_SPACING
    # Draw next steps
    y_position = draw_next_steps_text(canvas_obj, next_steps, LEFT_MARGIN, y_position, page_width, page_height)
    
    y_position -= SUBSECTION_SPACING
    # Draw Related Report File
    y_position = draw_related_report_text(canvas_obj, file_name, LEFT_MARGIN, y_position, page_width, page_height)
    
    # Add spacing before the next section
    y_position -= SECTION_SPACING

    return y_position


def add_user_identifying_data_section(canvas_obj, event_pii, user_pii, y_position, page_width, page_height):
    """
    Adds the 'User Identifying Data Detected' section to the PDF, ensuring it starts on a new page.

    Parameters:
        canvas_obj (Canvas): The ReportLab canvas object.
        event_pii (pd.DataFrame): DataFrame containing detected user-identifying event properties.
        user_pii (pd.DataFrame): DataFrame containing detected user-identifying user properties.
        y_position (int): Current Y position to begin writing.
        page_width (int): Page width for alignment.
        page_height (int): Page height for checking page space.

    Returns:
        int: Updated Y position after writing the section.
    """
    # Define Section Text
    title = "User Identifying Data Detected"
    subheader = "Event and User Properties detected as user identifying data based on the property's name."
    context = ("User-identifiable data can include properties like a user’s name, email, phone, address, "
               "credit card information, and any other user-identifiable information.")
    importance = ("It is important to be aware of all user-identifying data being tracked in Ampltiude. If you plan to"
                  "send this data to Amplitude, we recommend that you carefully review the data being tracked with your"
                  "Legal team to confirm that certain fields need to be tracked and sent into Amplitude."
    )
    next_steps = (
        "If you have ot already done so, review these with your legal team to confirm if these need to be tracked in "
        "Amplitude for any of your use cases. If only specific individuals need access to these data points, you can also "
        "use "
        '<font color="blue"><u><a href="https://amplitude.com/docs/data/data-access-control">'
        'data access controls</a></u></font>'
        " to restrict access to certain user groups. If these are not expected to be tracked in "
        "Amplitude, you can use the "
        '<font color="blue"><u><a href="https://amplitude.com/docs/admin/account-management/self-service-data-deletion-in-amplitude">'
        'self-service data deletion</a></u></font>'
        " tool or work with your account team to initiate data scrubs."
    )
    file_name = (
        "user_identifying_data_report.xlsx"
    )

    # Styling & Layout Constants
    TEXT_WIDTH = page_width - 120
    NEW_PAGE_THRESHOLD = 200  # Minimum space required before starting this section

    # ✅ Ensure this section starts on a new page if space is insufficient
    if y_position < NEW_PAGE_THRESHOLD:
        canvas_obj.showPage()  # Force a new page
        y_position = page_height - 50  # Reset position at the top of the new page

    # Draw section title
    y_position = draw_section_title(canvas_obj, title, LEFT_MARGIN, y_position, page_width, page_height)

    # Draw subheader
    y_position = draw_subheader_text(canvas_obj, subheader, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # Draw context
    y_position = draw_context_text(canvas_obj, context, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # Draw importance
    y_position = draw_importance_text(canvas_obj, importance, LEFT_MARGIN, y_position, page_width, page_height)

    # Table Data
    event_pii_count = len(event_pii) if not event_pii.empty else 0
    user_pii_count = len(user_pii) if not user_pii.empty else 0
    table_data = [["Category", "Count"], ["Event Property", event_pii_count], ["User Property", user_pii_count]]

    if event_pii_count > 0 or user_pii_count > 0:
            # Draw table (if data exists)
        if table_data and len(table_data) > 1:
            y_position = draw_table(canvas_obj, table_data, LEFT_MARGIN, y_position, page_width, page_height)

    y_position -= SUBSECTION_SPACING
    # Draw next steps
    y_position = draw_next_steps_text(canvas_obj, next_steps, LEFT_MARGIN, y_position, page_width, page_height)

    y_position -= SUBSECTION_SPACING
    # Draw Related Report File
    y_position = draw_related_report_text(canvas_obj, file_name, LEFT_MARGIN, y_position, page_width, page_height)
    
    # Add spacing before the next section
    y_position -= SECTION_SPACING

    return y_position

def draw_schema_status_table(canvas_obj, df, status_column, title, y_position, page_width, page_height):
    """
    Helper function to draw a small table showing [status, count, percentage], with a title.

    Parameters:
        canvas_obj (Canvas): The ReportLab canvas object.
        df (pd.DataFrame): DataFrame containing status information.
        status_column (str): Name of the column for status labels.
        title (str): Title of the table.
        y_position (int): Current Y position.
        page_width (int): Width of the page.
        page_height (int): Height of the page.

    Returns:
        int: Updated Y position after drawing the table.
    """

    # If df is empty, return the current position
    if df.empty:
        return y_position

    # Add table title
    y_position = check_and_page_break(canvas_obj, TITLE_SPACING + 12, y_position, page_height)
    canvas_obj.setFont("Helvetica-Bold", 12)
    canvas_obj.drawString(LEFT_MARGIN, y_position, title)
    y_position -= TITLE_SPACING  # Add spacing below title

    # Convert DataFrame to list format for table function
    table_data = [df.columns.tolist()] + df.values.tolist()

    # Define column widths (ensuring padding within page margins)
    num_columns = len(df.columns)
    RIGHT_MARGIN = 50  # Same as left margin
    usable_width = page_width - (LEFT_MARGIN + RIGHT_MARGIN)
    col_widths = [usable_width / num_columns] * num_columns  # Evenly distribute

    # Draw the table using the universal `draw_table` function
    y_position = draw_table(canvas_obj, table_data, LEFT_MARGIN, y_position, page_width, page_height, col_widths)

    return y_position


def add_event_and_prop_status_section(
    canvas_obj,
    event_counts_df,
    event_props_counts_df,
    user_props_counts_df,
    y_position,
    page_width,
    page_height
):
    """
    Adds a section showing Event & Property Schema Status counts (LIVE, UNEXPECTED, etc.)
    to the PDF after the user-identifying data section.
    """
    styles = getSampleStyleSheet()

    # ─── TEXT DEFINITIONS ───────────────────────────────────────────
    title = "Event & Property Status Summary"
    subheader = (
        "Events and Property counts based on their taxonomy status. "
    )
    context = (
        "Live events and properties were added to the tracking plan. "
        "Unexpected events and properties were not added to the plan before ingestion. "
    )

    importance = (
        "Planning your taxonomy helps validate the data with "
        '<font color="blue"><u><a href="https://amplitude.com/docs/data/validate-events">'
        'Observe</a></u></font>'
        " in Amplitude Data. Planned events "
        "can also be better managed within Amplitude; categories can be assigned and marked as inactive "
        "to not contribute toward MAU/WAU counts. "
    )
    next_steps = (
        """
        To leverage 
        <font color="blue"><u><a href="https://amplitude.com/docs/data/validate-events">
        Observe</a></u></font> 
        in Amplitude Data, review all events in your taxonomy and add any ‘Unexpected’ 
        events that are considered part of your tracking plan to the taxonomy, and Block or Delete any events 
        that are not considered part of your tracking plan. This will help ensure your tracking plan is clean 
        and will allow for easy validation going forward. 
        <br/><br/>
        Review all properties as well, and follow the same steps to clean up the list of properties in your 
        tracking plan. In addition, add data types to properties where you would like Amplitude to validate 
        incoming data based on the set data types. 
        """
    )

    # ─── LAYOUT CONSTANTS ───────────────────────────────────────────
    TEXT_WIDTH = page_width - 120
    NEW_PAGE_THRESHOLD = 200

    # ─── START OF CONTENT ───────────────────────────────────────────
    # If there's not enough room on the current page, start a new one
    if y_position < NEW_PAGE_THRESHOLD:
        canvas_obj.showPage()
        y_position = page_height - 50

    # Draw section title
    y_position = draw_section_title(canvas_obj, title, LEFT_MARGIN, y_position, page_width, page_height)

    # Draw subheader
    y_position = draw_subheader_text(canvas_obj, subheader, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # Draw context
    y_position = draw_context_text(canvas_obj, context, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # Draw importance
    y_position = draw_importance_text(canvas_obj, importance, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # Build the three tables (Events, Event Props, User Props)
    y_position = draw_schema_status_table(
        canvas_obj,
        event_counts_df,
        "Event Schema Status",
        "Event Schema Status Count/Percentage",
        y_position,
        page_width,
        page_height
    )

    y_position = draw_schema_status_table(
        canvas_obj,
        event_props_counts_df,
        "Event Property Schema Status",
        "Event Property Schema Status Count/Percentage",
        y_position,
        page_width,
        page_height
    )

    y_position = draw_schema_status_table(
        canvas_obj,
        user_props_counts_df,
        "User Property Schema Status",
        "User Property Schema Status Count/Percentage",
        y_position,
        page_width,
        page_height
    )

    y_position -= SUBSECTION_SPACING
    # Draw next steps
    y_position = draw_next_steps_text(canvas_obj, next_steps, LEFT_MARGIN, y_position, page_width, page_height)
   
    y_position -= SECTION_SPACING

    return y_position

def add_syntax_summary_section(canvas_obj, syntax_summary_df, y_position, page_width, page_height):
    """
    Adds the 'Syntax Summary Report' section to the PDF.
    """
    # ─── TEXT DEFINITIONS ───────────────────────────────────────────
    title = "Syntax Summary Report"
    subheader = "Events and Properties counts based on the syntax detected of the name of the Event or Property."
    context = "Syntax here refers to the naming convention for events and properties."
    importance = "Using a standard naming convention and syntax decreases the chance of instrumentation errors and increases data clarity."
    next_steps = (
        """
        <b>Pick a Consistent Syntax and Tense:</b> Select one naming convention (e.g., all lowercase, title case) 
        and apply it to all events.
        <br/><br/>
        <b>Review Old or Unused Events:</b> If certain events with outdated naming conventions are no longer analyzed, 
        consider 
        <font color="blue"><u><a href="https://amplitude.com/docs/faq/hide-block-or-delete-and-event-or-property">
        blocking</a></u></font>
         or removing them from tracking.
        <br/><br/>
        <b>Block Before Deleting:</b> In Amplitude, you can block an event if you still need historical data. Otherwise, 
        removing it from instrumentation, rather than deleting in Amplitude, is safer.
        <br/><br/>
        <b>Merge Duplicates:</b> If you have the same event tracked under different names, 
        <font color="blue"><u><a href="https://amplitude.com/docs/data/transformations#merge-events-event-properties-and-user-properties">
        merge</a></u></font>
         them in Amplitude to 
        reduce confusion.
        <br/><br/>
        <b>Rename via Display Name:</b> If renaming is needed, 
        <font color="blue"><u><a href="https://amplitude.com/docs/data/display-names-in-amplitude-data">
        update the display name</a></u></font>
         name in Amplitude’s UI instead of 
        changing the code that sends the event.
        """
    )
    file_name = (
        "naming_syntax_report.xlsx"
    )

    # ─── LAYOUT CONSTANTS ───────────────────────────────────────────
    TEXT_WIDTH = page_width - 120
    NEW_PAGE_THRESHOLD = 200

    # ─── START OF CONTENT ───────────────────────────────────────────
    if y_position < NEW_PAGE_THRESHOLD:
        canvas_obj.showPage()
        y_position = page_height - 50

    # Draw section title
    y_position = draw_section_title(canvas_obj, title, LEFT_MARGIN, y_position, page_width, page_height)

    # Draw subheader
    y_position = draw_subheader_text(canvas_obj, subheader, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # Draw context
    y_position = draw_context_text(canvas_obj, context, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # Draw importance
    y_position = draw_importance_text(canvas_obj, importance, LEFT_MARGIN, y_position, page_width, page_height)

    # ─── TABLE: Syntax Summary ───────────────────────────────────────
    if not syntax_summary_df.empty:
        table_data = [syntax_summary_df.columns.tolist()] + syntax_summary_df.values.tolist()

        col_widths = [page_width * 0.2, page_width * 0.2, page_width * 0.2, page_width * 0.2]

        y_position = draw_table(
            canvas_obj,
            table_data,
            LEFT_MARGIN,
            y_position,
            page_width,
            page_height,
            col_widths=col_widths,
        )

    # ─── NEXT STEPS ─────────────────────────────────────────────────
    y_position -= SUBSECTION_SPACING
    y_position = draw_next_steps_text(canvas_obj, next_steps, LEFT_MARGIN, y_position, page_width, page_height)

    y_position -= SUBSECTION_SPACING
    # Draw Related Report File
    y_position = draw_related_report_text(canvas_obj, file_name, LEFT_MARGIN, y_position, page_width, page_height)
    
    # Add spacing before next major section
    y_position -= SECTION_SPACING

    return y_position

def add_missing_categories_descriptions_section(
    canvas_obj,
    summary_df,
    y_position,
    page_width,
    page_height
):
    """
    Adds the 'Missing Descriptions and Categories' section to the PDF,
    showing summary_df (Category vs. Count) and standard text.
    """

    title = "Missing Descriptions and Categories"
    subheader = "Events and Properties with missing Categories and Descriptions."
    context = (
        "Categories and Descriptions are additional metadata you can add to your "
        "events and properties to make your tracking plan more readable and easy to access."
    )
    importance = (
        "Categories and Descriptions allow users to easily understand and discover "
        "the data that is tracked."
    )
    next_steps = (
        """
        <font color="blue"><b><u><a href="https://amplitude.com/docs/data/event-property-descriptions">
        Add Descriptions:</a></u></b></font>
         Even if your event names are clear, include details on how each event 
        is triggered. This helps new team members quickly find the right events when building charts.
        <br/><br/>
        <font color="blue"><b><u><a href="https://amplitude.com/docs/data/change-event-category">
        Use Categories:</a></u></b></font>
         Assign categories so your team can readily spot the most relevant events, 
        and so chart dropdowns automatically group them. This speeds up analysis and improves clarity.
        <br/><br/>
        <b>Update via UI or API:</b> You can add descriptions and categories directly in Amplitude’s Data 
        UI, or programmatically using our 
        <font color="blue"><u><a href="https://amplitude.com/docs/apis/analytics/taxonomy">
        Taxonomy API.</a></u></font>
        <br/><br/>
        <font color="blue"><b><u><a href="https://amplitude.com/docs/data/csv-import-export#events-and-event-properties">
        Bulk Updates with CSV:</a></u></b></font>
         Export your schema from Amplitude Data, add or revise descriptions and 
        categories in the CSV, and then re-upload it to apply changes in bulk.
        """
    )
    file_name = (
        "missing_categories_descriptions_report.xlsx"
    )

    # 1) Section Title
    y_position = draw_section_title(canvas_obj, title, LEFT_MARGIN, y_position, page_width, page_height)

    # 2) Subheader
    y_position = draw_subheader_text(canvas_obj, subheader, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # 3) Context
    y_position = draw_context_text(canvas_obj, context, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # 4) Importance
    y_position = draw_importance_text(canvas_obj, importance, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING

    # 5) If summary_df has rows, display it; else show [“No Data”]
    if not summary_df.empty:
        table_data = [summary_df.columns.tolist()] + summary_df.values.tolist()
    else:
        table_data = [["No Data"]]

    # Draw the table
    y_position = draw_table(
        canvas_obj,
        table_data,
        LEFT_MARGIN,
        y_position,
        page_width,
        page_height,
        col_widths=None
    )

    # 6) Next Steps
    y_position -= SUBSECTION_SPACING
    y_position = draw_next_steps_text(canvas_obj, next_steps, LEFT_MARGIN, y_position, page_width, page_height)

    y_position -= SUBSECTION_SPACING
    # Draw Related Report File
    y_position = draw_related_report_text(canvas_obj, file_name, LEFT_MARGIN, y_position, page_width, page_height)
    
    # Add spacing before next major section
    y_position -= SECTION_SPACING

    return y_position

from html import escape as html_escape  # ensure this is imported

def add_unused_events_section(
    canvas_obj,
    top_unused_events_df,
    bottom_unused_events_df,
    y_position,
    page_width,
    page_height,
    lookback_window
):
    """
    Draws a section in the PDF showing top and bottom 10 unused events,
    including the dynamically labeled 'Volume %' column.
    """
    # ───── SECTION TEXT ────────────────────────────────────────────
    title = "Unused Events"
    subheader = (
        f"Top and bottom events with zero queries within the selected {lookback_window}-day lookback window, "
        "based on event volume."
    )
    context = "Events with zero queries can indicate unused data."
    importance = (
        "Any data sent to Amplitude counts towards the volumes, and "
        "we want to ensure data in Amplitude is useful."
    )
    next_steps = (
        """
        High volume events with zero queries indicate events that are not directly used in any charts or cohorts. 
        If any of these events are events triggered in a user journey, re-evaluate the use cases being tracked in 
        Amplitude and ensure the teams using Amplitude understand the events better. This can include checking to 
        ensure the right event metadata is available to enable data trust and usability and training or creating 
        documentation for teams to enable them to effectively leverage the data. 
        <br/><br/>
        Low volume events with zero queries can indicate uncommon user actions and can still be helpful in 
        uncovering power user, issues, new user behaviors. Ensure the teams using Amplitude understand where these 
        events are triggered and their importance in user journey.
        """
    )
    file_name = (
        "unused_event_report.xlsx"
    )

    def format_cell(value):
        """Safely formats and escapes cell content for PDF table use."""
        if pd.isna(value):
            return "N/A"
        if isinstance(value, (int, float)):
            value = f"{value:,.2f}"
        return html_escape(str(value).strip())  # Avoid HTML errors

    volume_col = f"{lookback_window} Day Volume"
    queries_col = f"{lookback_window} Day Queries"

    # ───── SECTION HEADER TEXT ─────────────────────────────────────
    y_position = draw_section_title(canvas_obj, title, LEFT_MARGIN, y_position, page_width, page_height)
    y_position = draw_subheader_text(canvas_obj, subheader, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING
    y_position = draw_context_text(canvas_obj, context, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING
    y_position = draw_importance_text(canvas_obj, importance, LEFT_MARGIN, y_position, page_width, page_height)

    col_widths = [
        (page_width - 100) * 0.4,   # ~40%
        (page_width - 100) * 0.2,
        (page_width - 100) * 0.2,
        (page_width - 100) * 0.2
    ]

    # ───── TOP UNUSED EVENTS TABLE ─────────────────────────────────
    if not top_unused_events_df.empty:
        header_row = ["Top 10 (By Event Volume)", volume_col, queries_col, "Volume %"]
        table_data = [header_row]

        for _, row in top_unused_events_df.iterrows():
            table_data.append([
                format_cell(row.get("Event Name")),
                format_cell(row.get(volume_col)),
                format_cell(row.get(queries_col)),
                format_cell(row.get("Volume %"))
            ])

        print("Top Unused Events Table Preview:")
        for row in table_data[:1]:
            print(row)

        y_position = draw_table(canvas_obj, table_data, LEFT_MARGIN, y_position, page_width, page_height, col_widths)

    # ───── BOTTOM UNUSED EVENTS TABLE ──────────────────────────────
    if not bottom_unused_events_df.empty:
        y_position -= SUBSECTION_SPACING

        header_row = ["Bottom 10 (By Event Volume)", volume_col, queries_col, "Volume %"]
        table_data = [header_row]

        for _, row in bottom_unused_events_df.iterrows():
            table_data.append([
                format_cell(row.get("Event Name")),
                format_cell(row.get(volume_col)),
                format_cell(row.get(queries_col)),
                format_cell(row.get("Volume %"))
            ])

        print("Bottom Unused Events Table Preview:")
        for row in table_data[:1]:
            print(row)

        y_position = draw_table(canvas_obj, table_data, LEFT_MARGIN, y_position, page_width, page_height, col_widths)

    # ───── NEXT STEPS ──────────────────────────────────────────────
    y_position -= SUBSECTION_SPACING
    y_position = draw_next_steps_text(canvas_obj, next_steps, LEFT_MARGIN, y_position, page_width, page_height)
    
    y_position -= SUBSECTION_SPACING
    # Draw Related Report File
    y_position = draw_related_report_text(canvas_obj, file_name, LEFT_MARGIN, y_position, page_width, page_height)
    
    y_position -= SECTION_SPACING

    return y_position


def add_event_prop_misclassification_section(
    canvas_obj,
    summary_df,
    y_position,
    page_width,
    page_height
):
    """
    Adds a section to the PDF showing event properties that likely should be user properties,
    grouped by reason and count.
    """
    # ─── Section Text ─────────────────────
    title = "Potential User Property Detected in Event Properties"
    subheader = (
        "Event properties flagged as likely misclassified based on name. "
        "This includes items that look like user metadata or contain user identifying "
        "data."
    )
    context = (
        "Misclassifying properties can make analysis harder. Event properties typically describe an action, "
        "whereas user properties describe the person or account performing the action."
    )
    importance = (
        "Correctly classifying data helps ensure you're following Amplitude's best practices, "
        "and may help prevent duplicative or conflicting information in charts and filters."
    )
    next_steps = (
        "If the flagged event properties truly describe the user (e.g., `user_plan`, `email`, `country`), "
        "we recommend you move them to user properties in your implementation and remove them from event tracking.\n\n"
        "Note that you can keep old data available for analysis even after deprecating a property, "
        "and migrate new tracking going forward. If there are use cases to track these properties at the event scope" 
        "Verify that if they are tracked as event properties, they are included with every event where the property is "
        "essential for analysis."
    )
    file_name = (
        "user_property_misclassification_report.xlsx"
    )

    # ─── Draw text blocks ─────────────────
    y_position = draw_section_title(canvas_obj, title, LEFT_MARGIN, y_position, page_width, page_height)
    y_position = draw_subheader_text(canvas_obj, subheader, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING
    y_position = draw_context_text(canvas_obj, context, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING
    y_position = draw_importance_text(canvas_obj, importance, LEFT_MARGIN, y_position, page_width, page_height)

    # ─── Table ────────────────────────────
    if not summary_df.empty:
        table_data = [summary_df.columns.tolist()] + summary_df.values.tolist()
        col_widths = [
            (page_width - 100) * 0.7,  # Reason column
            (page_width - 100) * 0.3   # Count column
        ]
        y_position = draw_table(canvas_obj, table_data, LEFT_MARGIN, y_position, page_width, page_height, col_widths)

    # ─── Next Steps ───────────────────────
    y_position -= SUBSECTION_SPACING
    y_position = draw_next_steps_text(canvas_obj, next_steps, LEFT_MARGIN, y_position, page_width, page_height)
    
    y_position -= SUBSECTION_SPACING
    # Draw Related Report File
    y_position = draw_related_report_text(canvas_obj, file_name, LEFT_MARGIN, y_position, page_width, page_height)
    
    y_position -= SECTION_SPACING

    return y_position


def build_stale_items_summary_table(stale_events_df, stale_properties_df, stale_user_props_df):
    """
    Creates a simple summary DataFrame showing the count of stale items
    in each category: Events, Event Properties, and User Properties.
    """
    counts = {
        "Events": len(stale_events_df) if stale_events_df is not None and not stale_events_df.empty else 0,
        "Event Properties": len(stale_properties_df) if stale_properties_df is not None and not stale_properties_df.empty else 0,
        "User Properties": len(stale_user_props_df) if stale_user_props_df is not None and not stale_user_props_df.empty else 0,
    }

    summary_df = pd.DataFrame(list(counts.items()), columns=["Category", "Count"])
    return summary_df


def add_stale_items_section(
    canvas_obj,
    stale_events_df,
    stale_properties_df,
    stale_user_props_df,
    y_position,
    page_width,
    page_height
):
    """
    Adds a section to the PDF showing a summary count of stale events,
    stale event properties, and stale user properties.
    """
    title = "Stale Events and Properties"
    subheader = (
        "Events and Properties that have not been seen in the last 12 months are considered stale."
    )
    context = (
        "Stale events and properties are those that have not been ingested by Amplitude in the last year."
    )
    importance = (
        "These may be deprecated or legacy data points. They may be safe to archive or remove from tracking." 
        "Stale events can make your taxonomy look bloated and make it harder to find the correct events for "
        "analysis."
    )
    next_steps = (
        "Review stale events and properties to determine if they are still needed."
        '<font color="blue"><u><a href="https://amplitude.com/docs/faq/hide-block-or-delete-and-event-or-property">'
        'hide, block or delete</a></u></font>'
        " anything no longer in use to simplify your taxonomy."
        "Before deleting events, check for seasonality to ensure that needed events "
        "are not being removed in error."
    )
    file_name = (
        "stale_and_single_day_events_properties_report.xlsx"
    )

    # Draw Section Header
    y_position = draw_section_title(canvas_obj, title, LEFT_MARGIN, y_position, page_width, page_height)
    y_position = draw_subheader_text(canvas_obj, subheader, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING
    y_position = draw_context_text(canvas_obj, context, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING
    y_position = draw_importance_text(canvas_obj, importance, LEFT_MARGIN, y_position, page_width, page_height)

    # Build the summary table
    summary_df = build_stale_items_summary_table(stale_events_df, stale_properties_df, stale_user_props_df)
    table_data = [summary_df.columns.tolist()] + summary_df.values.tolist()

    col_widths = [page_width * 0.4, page_width * 0.3]  # Adjust column sizing as needed

    y_position = draw_table(
        canvas_obj,
        table_data,
        LEFT_MARGIN,
        y_position,
        page_width,
        page_height,
        col_widths
    )

    # Draw Next Steps
    y_position -= SUBSECTION_SPACING
    y_position = draw_next_steps_text(canvas_obj, next_steps, LEFT_MARGIN, y_position, page_width, page_height)
    
    y_position -= SUBSECTION_SPACING
    # Draw Related Report File
    y_position = draw_related_report_text(canvas_obj, file_name, LEFT_MARGIN, y_position, page_width, page_height)
    
    y_position -= SECTION_SPACING

    return y_position

# pdf_generation.py

def build_sing_day_items_summary_table(single_day_events_df, single_day_properties_df, single_day_user_props_df):
    """
    Creates a simple summary DataFrame showing the count of stale items
    in each category: Events, Event Properties, and User Properties.
    """
    counts = {
        "Events": len(single_day_events_df) if single_day_events_df is not None and not single_day_events_df.empty else 0,
        "Event Properties": len(single_day_properties_df) if single_day_properties_df is not None and not single_day_properties_df.empty else 0,
        "User Properties": len(single_day_user_props_df) if single_day_user_props_df is not None and not single_day_user_props_df.empty else 0,
    }

    summary_df = pd.DataFrame(list(counts.items()), columns=["Category", "Count"])
    return summary_df


def add_single_day_items_section(
    canvas_obj,
    single_day_events_df,
    single_day_properties_df,
    single_day_user_props_df,
    y_position,
    page_width,
    page_height
):
    """
    Adds a section to the PDF showing a summary count of stale events,
    stale event properties, and stale user properties.
    """
    title = "Single Day Events and Properties"
    subheader = (
        "Events and Properties have only been ingested for a single day."
    )
    context = (
        "Based on ‘First Seen’ date being equal to ‘Last Seen’ date."
    )
    importance = (
        "If the first seen date is the same as last seen date, its very likely "
        "these were test events, which clutter the taxonomy."
    )
    next_steps = (
        "Create a recurring cadence to clean up your taxonomy by hiding, "
        "blocking or deleting those events"
    )
    file_name = (
        "stale_and_single_day_events_properties_report.xlsx"
    )

    # Draw Section Header
    y_position = draw_section_title(canvas_obj, title, LEFT_MARGIN, y_position, page_width, page_height)
    y_position = draw_subheader_text(canvas_obj, subheader, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING
    y_position = draw_context_text(canvas_obj, context, LEFT_MARGIN, y_position, page_width, page_height)
    y_position -= SUBSECTION_SPACING
    y_position = draw_importance_text(canvas_obj, importance, LEFT_MARGIN, y_position, page_width, page_height)

    # Build the summary table
    summary_df = build_stale_items_summary_table(single_day_events_df, single_day_properties_df, single_day_user_props_df)
    table_data = [summary_df.columns.tolist()] + summary_df.values.tolist()

    col_widths = [page_width * 0.4, page_width * 0.3]  # Adjust column sizing as needed

    y_position = draw_table(
        canvas_obj,
        table_data,
        LEFT_MARGIN,
        y_position,
        page_width,
        page_height,
        col_widths
    )

    # Draw Next Steps
    y_position -= SUBSECTION_SPACING
    y_position = draw_next_steps_text(canvas_obj, next_steps, LEFT_MARGIN, y_position, page_width, page_height)
    
    y_position -= SUBSECTION_SPACING
    # Draw Related Report File
    y_position = draw_related_report_text(canvas_obj, file_name, LEFT_MARGIN, y_position, page_width, page_height)
    
    y_position -= SECTION_SPACING

    return y_position
