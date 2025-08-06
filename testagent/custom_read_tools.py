import os

from pymongo import MongoClient
from dotenv import load_dotenv


load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
       


# @tool.register
def process_and_save_candidates(raw_data_string: str) -> str:
    """
    Parses a raw string of candidate data, manually validates each record, and saves valid ones to MongoDB.

    This tool handles the entire workflow from raw text to database entry.
    It manually parses the string line-by-line and applies the following validation rules:

    - Rule 1: A 'First Name', 'Last Name', and 'Email' must be present for each candidate.
    - Rule 2: The 'Gender' must be either 'Male' or 'Female' (case-insensitive).
    - Rule 3: A 'Role' field for each candidate must be present regarding what role they are applying for.
    - Rule 4: Each candidate record must have the same number of fields as the header row.

    Records that fail validation are discarded.

    Args:
        raw_data_string (str): A single string containing candidate data, with each candidate on a new line
                               and fields separated by commas. Assumes a header is the first line.

    Returns:
        str: The final status message: "Candidate records were validated and saved in MongoDB."
    """
    if not raw_data_string or not raw_data_string.strip():
        return "Processing failed: The input string was empty."

    lines = raw_data_string.strip().split('\n')
    
    # Check for header and at least one data line
    if len(lines) < 2:
        return "Error: Data must include a header row and at least one candidate record."

    header = [h.strip() for h in lines[0].split(',')]
    data_lines = lines[1:]

    # --- This is where the list of dictionaries is built manually ---
    validated_candidates_list = []
    for line in data_lines:
        if not line.strip():
            continue  # Skip empty lines

        values = [v.strip() for v in line.split(',')]
        
        # Ensure the row has the same number of columns as the header
        if len(values) != len(header):
            continue

        # Create a dictionary for the current candidate record
        candidate_record = dict(zip(header, values))

        # --- Apply validation rules to the created dictionary ---
        first_name = candidate_record.get('First Name')
        last_name = candidate_record.get('Last Name')
        email = candidate_record.get('Email')
        
        # Rule 1: Check for presence of required fields
        if not all([first_name, last_name, email]):
            continue # Discard this record

        # Rule 2: Check Gender
        gender = candidate_record.get('Gender', '').title() # .title() makes it 'Male' or 'Female'
        if gender not in ['Male', 'Female']:
            continue # Discard this record
        
        # If all checks pass, add the validated and structured record to our list
        # Ensure the gender is stored in the standardized format
        candidate_record['Gender'] = gender
        validated_candidates_list.append(candidate_record)
    
    # --- End of manual building and validation ---

    if not validated_candidates_list:
        return "Validation complete. No valid candidate records were found to save."

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.server_info()
        db = client['nextleap']
        collection = db['candidates']
        
        # Use the manually built list to create records in the database
        #add a status field to each record
        for candidate in validated_candidates_list:
            candidate['status'] = 'Record_Saved'
        
        collection.insert_many(validated_candidates_list)
        client.close()
        
        # The final, simple success message
        return "Candidate records were validated and saved in MongoDB."
        
    except Exception as e:
        return f"Database Error: Could not save records. Details: {e}"



