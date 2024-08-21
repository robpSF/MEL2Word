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

def get_facilitator_content(stages):
    facilitator_content = []
    next_stage_id = None

    # Debug: Print the stages to verify what's being processed
    print("All stages:")
    for stage in stages:
        print(f"Stage ID: {stage.get('id')}, Subject: {stage.get('subject')}")

    # Find the first stage with make_first_moderator_content = 1
    first_stage = None
    for index, stage in enumerate(stages):
        if stage.get('make_first_moderator_content') == 1 and stage.get('channel') == 4:
            first_stage = stage
            print(f"First stage identified: {stage.get('subject')} at index {index}")
            facilitator_content.append({'subject': stage.get('subject'), 'text': stage.get('text')})
            next_stage_id = stage.get('single_go_on_answers', [{}])[0].get('destination_stage_id') if stage.get('question_type') == 9 else stage.get('timer_answers', [{}])[0].get('destination_stage_id')
            break

    if first_stage is None:
        print("Error: No starting stage found with make_first_moderator_content = 1 and channel = 4")

    # Traverse through the stages using the pointers
    while next_stage_id:
        print(f"Next stage ID: {next_stage_id}")
        for stage in stages:
            if stage.get('id') == next_stage_id:
                print(f"Processing stage: {stage.get('subject')} (ID: {stage.get('id')})")
                facilitator_content.append({'subject': stage.get('subject'), 'text': stage.get('text')})
                next_stage_id = stage.get('single_go_on_answers', [{}])[0].get('destination_stage_id') if stage.get('question_type') == 9 else stage.get('timer_answers', [{}])[0].get('destination_stage_id')
                print(f"Next stage ID after processing: {next_stage_id}")
                break
        else:
            print(f"Error: No valid next stage found for ID {next_stage_id}, stopping sequence.")
            break

    return facilitator_content

# Streamlit app
def main():
    st.title("Cumulative Timing Tables from .txplib File")

    start_time_input = st.text_input("Enter the start time (format: YYYY-MM-DD HH:MM:SS)", value="2024-01-01 00:00:00")
    start_time = datetime.strptime(start_time_input, "%Y-%m-%d %H:%M:%S")

    uploaded_file = st.file_uploader("Choose a .txplib file", type="txplib")
    
    if uploaded_file is not None:
        st.write("File uploaded successfully.")
        
        try:
            with zipfile.ZipFile(io.BytesIO(uploaded_file.read()), 'r') as zip_ref:
                st.write("Zip file opened successfully.")
                
                design_files = []
                for file_name in zip_ref.namelist():
                    st.write(f"Checking file: {file_name}")
                    if fnmatch.fnmatch(file_name, "design *.txt"):
                        st.write(f"Found matching design file: {file_name}")
                        with zip_ref.open(file_name) as json_file:
                            json_file_content = json_file.read()
                            design_files.append((file_name, json_file_content))

                if design_files:
                    for file_name, json_file_content in design_files:
                        st.write(f"Processing {file_name}")
                        data = json.loads(json_file_content)
                        
                        stages = data.get('stages', [])
                        st.write(f"Number of stages found in {file_name}: {len(stages)}")

                        # Call get_facilitator_content with debug info
                        facilitator_content = get_facilitator_content(stages)
                        st.write(f"Facilitator content extracted with {len(facilitator_content)} stages.")

                        # Example of further processing or use of `facilitator_content`

                else:
                    st.error("No valid 'design *.txt' files found inside the .txplib archive.")
        except zipfile.BadZipFile:
            st.error("Error: The uploaded file is not a valid zip file.")
        except Exception as e:
            st.error(f"Error processing the zip file: {e}")
        
if __name__ == "__main__":
    main()
