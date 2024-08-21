import streamlit as st
import pandas as pd
import json
import zipfile
import io
import fnmatch
from datetime import datetime, timedelta
from docx import Document

# Function to format timedelta into D days hh:mm:ss
def format_timedelta(td):
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} days {hours:02d}:{minutes:02d}:{seconds:02d}"

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
def save_to_word(table, file_name):
    doc = Document()
    doc.add_heading('Cumulative Timing Table', 0)

    table_to_word = doc.add_table(rows=1, cols=4)
    hdr_cells = table_to_word.rows[0].cells
    hdr_cells[0].text = 'Cumulative Time (D days hh:mm:ss)'
    hdr_cells[1].text = 'Subject'
    hdr_cells[2].text = 'Text'
    hdr_cells[3].text = 'Inject Timing (s)'

    for i, row in table.iterrows():
        row_cells = table_to_word.add_row().cells
        row_cells[0].text = row['Cumulative Time (D days hh:mm:ss)']
        row_cells[1].text = row['Subject']
        row_cells[2].text = row['Text']
        row_cells[3].text = str(row['Inject Timing (s)'])

    doc.save(file_name)

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
                            output_file_name = f"{file_name}_timing_table.docx"
                            save_to_word(cumulative_timing_table, output_file_name)
                            st.write(f"Word document saved as {output_file_name}.")
                else:
                    st.error("No valid 'design *.txt' files found inside the .txplib archive.")
        except Exception as e:
            st.error(f"Error processing the zip file: {e}")
        
if __name__ == "__main__":
    main()
