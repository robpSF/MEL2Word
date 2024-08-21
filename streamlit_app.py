import streamlit as st
import pandas as pd
import json
import zipfile
import io
import fnmatch
from datetime import datetime, timedelta
from docx import Document

# Function to process facilitator content
def get_facilitator_content(stages):
    facilitator_content = []
    next_stage_id = None

    # Find the first stage with make_first_moderator_content = 1
    for stage in stages:
        if stage.get('make_first_moderator_content') == 1 and stage.get('channel') == 4:
            facilitator_content.append({'subject': stage.get('subject'), 'text': stage.get('text')})
            next_stage_id = stage.get('single_go_on_answers', [{}])[0].get('destination_stage_id') if stage.get('question_type') == 9 else stage.get('timer_answers', [{}])[0].get('destination_stage_id')
            break

    # Traverse through the stages using the pointers
    while next_stage_id:
        for stage in stages:
            if stage.get('id') == next_stage_id:
                facilitator_content.append({'subject': stage.get('subject'), 'text': stage.get('text')})
                next_stage_id = stage.get('single_go_on_answers', [{}])[0].get('destination_stage_id') if stage.get('question_type') == 9 else stage.get('timer_answers', [{}])[0].get('destination_stage_id')
                break
        else:
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
            # Open the uploaded .txplib file as a zip file
            with zipfile.ZipFile(io.BytesIO(uploaded_file.read()), 'r') as zip_ref:
                st.write("Zip file opened successfully.")
                
                design_files = [name for name in zip_ref.namelist() if fnmatch.fnmatch(name, "design *.txt")]
                
                if design_files:
                    for file_name in design_files:
                        st.write(f"Processing {file_name}")
                        
                        with zip_ref.open(file_name) as json_file:
                            data = json.load(json_file)
                        
                        stages = data.get('stages', [])
                        st.write(f"Number of stages found in {file_name}: {len(stages)}")
                        
                        facilitator_content = get_facilitator_content(stages)
                        st.write(f"Facilitator content extracted with {len(facilitator_content)} stages.")
                        
                        # Print each stage's subject
                        st.write("Stages extracted in order:")
                        for index, content in enumerate(facilitator_content):
                            st.write(f"Stage {index + 1}: {content['subject']}")
                        
                else:
                    st.error("No valid 'design *.txt' files found inside the .txplib archive.")
        
        except zipfile.BadZipFile:
            st.error("Error: The uploaded file is not a valid zip file.")
        except Exception as e:
            st.error(f"Error processing the zip file: {e}")

if __name__ == "__main__":
    main()
