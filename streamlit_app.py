import streamlit as st
import pandas as pd
import json
import zipfile
import os
import tempfile

# Function to format seconds into hh:mm
def format_seconds_to_hhmm(seconds):
    minutes = seconds // 60
    return f"{minutes:02d}:{seconds % 60:02d}"

# Function to create a cumulative timing table
def create_cumulative_timing_table(timing_info):
    cumulative_time = 0
    table_data = []

    for item in timing_info:
        cumulative_time += item.get('timer_seconds', 0)
        table_data.append({
            'Cumulative Time (hh:mm)': format_seconds_to_hhmm(cumulative_time),
            'Subject': item.get('subject', ''),
            'Text': item.get('text', ''),
            'Inject Timing (s)': item.get('timer_seconds', 0)
        })

    return pd.DataFrame(table_data)

# Streamlit app
def main():
    st.title("Cumulative Timing Table from .txplib File")

    # Upload the .txplib file
    uploaded_file = st.file_uploader("Choose a .txplib file", type="txplib")
    
    if uploaded_file is not None:
        # Create a temporary directory to extract files
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Save the uploaded file to the temporary directory
            zip_path = os.path.join(tmpdirname, uploaded_file.name)
            with open(zip_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())

            # Unzip the file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdirname)

            # Find the JSON file within the extracted files
            json_file_path = None
            for root, dirs, files in os.walk(tmpdirname):
                for file in files:
                    if file.endswith('.txt'):
                        json_file_path = os.path.join(root, file)
                        break
                if json_file_path:
                    break

            # Process the JSON file if found
            if json_file_path:
                with open(json_file_path, 'r') as json_file:
                    data = json.load(json_file)
                    
                    # Extract the stages
                    stages = data.get('stages', [])

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
                    cumulative_timing_table = create_cumulative_timing_table(timing_info)

                    # Display the table
                    st.dataframe(cumulative_timing_table)
            else:
                st.error("No valid .txt file found inside the .txplib archive.")
        
if __name__ == "__main__":
    main()
