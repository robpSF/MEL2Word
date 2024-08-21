import streamlit as st
import pandas as pd
import json
import zipfile
import io
import fnmatch
from datetime import datetime, timedelta
from docx import Document
from docx.shared import Pt

# Function to format timedelta into D days hh:mm:ss
def format_timedelta(td):
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} days {hours:02d}:{minutes:02d}:{seconds:02d}"

# Function to parse text for <B> and <I> tags and apply formatting
def parse_text(doc, text):
    run = doc.add_paragraph().add_run()

    while "<B>" in text or "<I>" in text:
        b_start = text.find("<B>")
        b_end = text.find("</B>")
        i_start = text.find("<I>")
        i_end = text.find("</I>")

        # Handle bold text
        if b_start != -1 and (b_start < i_start or i_start == -1):
            run.add_text(text[:b_start])
            bold_text = text[b_start + 3:b_end]
            run.bold = True
            run.add_text(bold_text)
            run.bold = None
            text = text[b_end + 4:]
        # Handle italic text
        elif i_start != -1:
            run.add_text(text[:i_start])
            italic_text = text[i_start + 3:i_end]
            run.italic = True
            run.add_text(italic_text)
            run.italic = None
            text = text[i_end + 4:]

    # Add remaining text
    run.add_text(text)
    return run

# Function to create a cumulative timing table
def create_cumulative_timing_table(timing_info, start_time):
    cumulative_time = start_time
    table_data = []

    for item in timing_info:
        cumulative_time += timedelta(seconds=item.get('timer_seconds', 0))
        table_data.append({
            'Cumulative Time (D days hh:mm:ss)': format_timedelta(cumulative_time - start_time),
            'Subject': item.get('subject', ''),
            'Text': item.get('text', ''),
            'Inject Timing (s)': item.get('timer_seconds', 0)
        })

    return pd.DataFrame(table_data)

# Function to save the cumulative timing table to a Word document
def save_to_word(table):
    doc = Document()
    doc.add_heading('Cumulative Timing Table', 0)

    for i, row in table.iterrows():
        # Add cumulative time
        doc.add_paragraph(f"Cumulative Time: {row['Cumulative Time (D days hh:mm:ss)']}", style='BodyText')

        # Add subject
        subject_paragraph = doc.add_paragraph("Subject: ", style='BodyText')
        parse_text(subject_paragraph, row['Subject'])

        # Add text
        text_paragraph = doc.add_paragraph("Text: ", style='BodyText')
        parse_text(text_paragraph, row['Text'])

        # Add space between entries
        doc.add_paragraph("", style='BodyText')

    # Save to a bytes buffer instead of a file
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# Streamlit app
def main():
    st.title("Cumulative Timing Tables from .txplib File")

    # Ask the user for a start time
    start_time_input = st.text_input("Enter the start time (format: YYYY-MM-DD HH:MM:SS)", value="2024-01-01 00:00:00")
    start_time = datetime.strptime(start_time_input, "%Y-%m-%d %H:%M:%S")

    # Upload the .txplib file
    uploaded_file = st.file_uploader("Choose a .txplib file", type="txplib")
    
    if uploaded_file is not None:
        st.write("File uploaded successfully.")
        
        # Open the uploaded .txplib file as a zip file
        try:
            with zipfile.ZipFile(io.BytesIO(uploaded_file.read()), 'r') as zip_ref:
                st.write("Zip file opened successfully.")
                
                # Find all the JSON files within the zip archive matching "design *.txt"
                design_files = []
                for file_name in zip_ref.namelist():
                    st.write(f"Checking file: {file_name}")
                    if fnmatch.fnmatch(file_name, "design *.txt"):
                        st.write(f"Found matching design file: {file_name}")
                        with zip_ref.open(file_name) as json_file:
                            json_file_content = json_file.read()
                            design_files.append((file_name, json_file_content))

                # Process each found JSON file
                if design_files:
                    for file_name, json_file_content in design_files:
                        st.write(f"Processing {file_name}")
                        data = json.loads(json_file_content)
                        
                        # Extract the stages
                        stages = data.get('stages', [])
                        st.write(f"Number of stages found in {file_name}: {len(stages)}")

                        # Extract potential time-related data from the stages
                        timing_info = []

                        for stage in stages:
                            if 'timer_answers' in stage:
                                for timer in stage['timer_answers']:
                                    if 'timer_seconds' in timer and timer['timer_seconds'] > 0:
                                        timing_info.append({
                                            'subject': stage.get('subject', ''),
                                            'text': stage.get('text', ''),
                                            'timer_seconds': timer['timer_seconds']
                                        })
                            if 'timestamp' in stage and stage['timestamp']:
                                timing_info.append({
                                    'subject': stage.get('subject', ''),
                                    'text': stage.get('text', ''),
                                    'timestamp': stage['timestamp']
                                })

                        # Create the cumulative timing table
                        cumulative_timing_table = create_cumulative_timing_table(timing_info, start_time)

                        # Display the table for each design file
                        st.write(f"Displaying the cumulative timing table for {file_name}")
                        st.dataframe(cumulative_timing_table)

                        # Provide an option to download the table as a Word document
                        if st.button(f"Download {file_name} table as Word"):
                            word_buffer = save_to_word(cumulative_timing_table)
                            st.download_button(
                                label=f"Download {file_name} table as Word",
                                data=word_buffer,
                                file_name=f"{file_name}_timing_table.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                else:
                    st.error("No valid 'design *.txt' files found inside the .txplib archive.")
        except Exception as e:
            st.error(f"Error processing the zip file: {e}")
        
if __name__ == "__main__":
    main()
