import streamlit as st
import pandas as pd
import json
import zipfile
import io
import fnmatch
from datetime import datetime, timedelta
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Function to format timedelta into D days hh:mm:ss
def format_timedelta(td):
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} days {hours:02d}:{minutes:02d}:{seconds:02d}"

# Function to parse and format text with <B> and <I> tags
def parse_and_add_run(paragraph, text):
    while text:
        if text.startswith("<B>"):
            text = text[3:]  # Remove the <B> tag
            end_index = text.find("</B>")
            if end_index != -1:
                paragraph.add_run(text[:end_index]).bold = True
                text = text[end_index + 4:]  # Remove the </B> tag
            else:
                paragraph.add_run(text).bold = True
                break
        elif text.startswith("<I>"):
            text = text[3:]  # Remove the <I> tag
            end_index = text.find("</I>")
            if end_index != -1:
                paragraph.add_run(text[:end_index]).italic = True
                text = text[end_index + 4:]  # Remove the </I> tag
            else:
                paragraph.add_run(text).italic = True
                break
        else:
            next_tag = min(
                (text.find("<B>"), text.find("<I>")),
                key=lambda x: (x == -1, x)  # Find the next tag or end
            )
            if next_tag == -1:
                paragraph.add_run(text)
                break
            paragraph.add_run(text[:next_tag])
            text = text[next_tag:]

# Function to create a cumulative timing table
def create_cumulative_timing_table(timing_info, start_time):
    cumulative_time = start_time
    st.write(start_time)  # Display the start time for debugging
    table_data = []

    for item in timing_info:
        # Add the current inject's timer_seconds to cumulative_time
        cumulative_time += timedelta(seconds=item.get('timer_seconds', 0))
        
        # Record the current cumulative_time as it is, without subtracting start_time
        table_data.append({
            'Cumulative Time (D days hh:mm:ss)': format_timedelta(cumulative_time - datetime(1970, 1, 1)),  # Direct cumulative time
            'Subject': item.get('subject', ''),
            'Text': item.get('text', ''),
            'Inject Timing (s)': item.get('timer_seconds', 0)
        })

    return pd.DataFrame(table_data)


# Function to add shading to a cell
def add_shading(cell, color):
    tc_pr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), color)
    tc_pr.append(shd)

# Function to save the cumulative timing table to a Word document
def save_to_word(table):
    doc = Document()
    doc.add_heading('Master Events List', 0)

    table_to_word = doc.add_table(rows=1, cols=4)
    hdr_cells = table_to_word.rows[0].cells
    hdr_cells[0].text = 'Cumulative Time (D days hh:mm:ss)'
    hdr_cells[1].text = 'Subject'
    hdr_cells[2].text = 'Text'
    hdr_cells[3].text = 'Inject Timing (s)'

    # Add shading to header
    for cell in hdr_cells:
        add_shading(cell, 'D3D3D3')  # Light grey for header

    # Add rows with alternating shading
    for i, row in table.iterrows():
        row_cells = table_to_word.add_row().cells
        row_cells[0].text = row['Cumulative Time (D days hh:mm:ss)']
        parse_and_add_run(row_cells[1].paragraphs[0], row['Subject'])
        parse_and_add_run(row_cells[2].paragraphs[0], row['Text'])
        row_cells[3].text = str(row['Inject Timing (s)'])

        # Alternate row color
        if i % 2 == 0:
            for cell in row_cells:
                add_shading(cell, 'D3D3D3')  # Light grey

    # Save to a bytes buffer instead of a file
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# Function to retrieve facilitator content from the stages with timing information
def get_facilitator_content(stages):
    facilitator_content = []
    next_stage_id = None

    # Traverse through the stages
    for stage in stages:
        if stage.get('make_first_moderator_content') == 1 and stage.get('channel') == 4:
            # Determine the inject timing
            timer_seconds = 0
            if stage.get('timer_answers'):
                for timer in stage['timer_answers']:
                    if 'timer_seconds' in timer:
                        timer_seconds = timer['timer_seconds']
                        break

            stage_info = {
                'subject': stage.get('subject'),
                'text': stage.get('text'),
                'timer_seconds': timer_seconds
            }
            facilitator_content.append(stage_info)

            next_stage_id = stage.get('single_go_on_answers', [{}])[0].get('destination_stage_id') if stage.get('question_type') == 9 else stage.get('timer_answers', [{}])[0].get('destination_stage_id')
            break

    # Traverse through the stages using the pointers
    while next_stage_id:
        for stage in stages:
            if stage.get('id') == next_stage_id:
                # Determine the inject timing
                timer_seconds = 0
                if stage.get('timer_answers'):
                    for timer in stage['timer_answers']:
                        if 'timer_seconds' in timer:
                            timer_seconds = timer['timer_seconds']
                            break
                
                stage_info = {
                    'subject': stage.get('subject'),
                    'text': stage.get('text'),
                    'timer_seconds': timer_seconds
                }
                facilitator_content.append(stage_info)

                next_stage_id = stage.get('single_go_on_answers', [{}])[0].get('destination_stage_id') if stage.get('question_type') == 9 else stage.get('timer_answers', [{}])[0].get('destination_stage_id')
                break
        else:
            break

    return facilitator_content

# Streamlit app
def main():
    st.title("MELs from .txplib File")

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
                st.write("Library file opened successfully.")
                
                # Find all the JSON files within the zip archive matching "design *.txt"
                design_files = []
                for file_name in zip_ref.namelist():
                    #st.write(f"Checking file: {file_name}")
                    if fnmatch.fnmatch(file_name, "design *.txt"):
                        #st.write(f"Found matching design file: {file_name}")
                        with zip_ref.open(file_name) as json_file:
                            json_file_content = json_file.read()
                            design_files.append((file_name, json_file_content))

                # Process each found JSON file
                if design_files:
                    for file_name, json_file_content in design_files:
                        #st.write(f"Processing {file_name}")
                        data = json.loads(json_file_content)
                        
                        # Extract the stages
                        stages = data.get('stages', [])
                        #st.write(f"Number of stages found in {file_name}: {len(stages)}")

                        # Get facilitator content with improved indexing and timing info
                        facilitator_content = get_facilitator_content(stages)
                        #st.write(f"Facilitator content extracted with {len(facilitator_content)} stages.")
                        
                        # Print each stage's subject
                        #st.write("Stages extracted in order:")
                        #for index, content in enumerate(facilitator_content):
                            #st.write(f"Stage {index + 1}: {content['subject']} (Inject Timing: {content['timer_seconds']}s)")
                        
                        # Create the cumulative timing table
                        cumulative_timing_table = create_cumulative_timing_table(facilitator_content, start_time)

                                                # Display the table for each design file
                        st.write(f"Displaying the Master Events List for {file_name}")
                        st.dataframe(cumulative_timing_table)

                        # Provide an option to download the table as a Word document
                        if st.button(f"Prepare table for Word"):
                            word_buffer = save_to_word(cumulative_timing_table)
                            st.download_button(
                                label=f"Download Word file",
                                data=word_buffer,
                                file_name=f"{uploaded_file.name}_MEL.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                else:
                    st.error("No valid 'design *.txt' files found inside the .txplib archive.")
        except Exception as e:
            st.error(f"Error processing the file: {e}")

if __name__ == "__main__":
    main()

