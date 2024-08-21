import streamlit as st
import pandas as pd
import json
import zipfile
import io
import fnmatch

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
        st.write("File uploaded successfully.")
        
        # Open the uploaded .txplib file as a zip file
        try:
            with zipfile.ZipFile(io.BytesIO(uploaded_file.read()), 'r') as zip_ref:
                st.write("Zip file opened successfully.")
                
                # Find the JSON file within the zip archive matching "design *.txt"
                json_file_content = None
                for file_name in zip_ref.namelist():
                    st.write(f"Checking file: {file_name}")
                    if fnmatch.fnmatch(file_name, "design *.txt"):
                        st.write(f"Found matching design file: {file_name}")
                        with zip_ref.open(file_name) as json_file:
                            json_file_content = json_file.read()
                            st.write("JSON file content read successfully.")
                            break

                # Process the JSON file if found
                if json_file_content:
                    st.write("Processing JSON content.")
                    data = json.loads(json_file_content)
                    
                    # Extract the stages
                    stages = data.get('stages', [])
                    st.write(f"Number of stages found: {len(stages)}")

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
                    st.write("Displaying the cumulative timing table.")
                    st.dataframe(cumulative_timing_table)
                else:
                    st.error("No valid 'design *.txt' file found inside the .txplib archive.")
        except Exception as e:
            st.error(f"Error processing the zip file: {e}")
        
if __name__ == "__main__":
    main()
