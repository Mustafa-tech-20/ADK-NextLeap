import os
import json
from typing import Dict, Any
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timezone


load_dotenv()

# Move this inside functions to avoid module-level state
def _get_mongo_client():
    """Helper function to create MongoDB client when needed"""
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI environment variable not set")
    return MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

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

        # Rule 3: Check Role
        role = candidate_record.get('Role')
        if not role:
            continue

        # Rule 4: Ensure all fields match the header length
        if len(candidate_record) != len(header):
            continue
        
        # If all checks pass, add the validated and structured record to our list
        # Ensure the gender is stored in the standardized format
        candidate_record['Gender'] = gender
        validated_candidates_list.append(candidate_record)
    
    # --- End of manual building and validation ---

    if not validated_candidates_list:
        return "Validation complete. No valid candidate records were found to save."

    # Create MongoDB connection inside the function
    client = None
    try:
        client = _get_mongo_client()
        client.server_info()
        db = client['nextleap']
        collection = db['candidates']
        
        # Use the manually built list to create records in the database
        # add a status field to each record
        for candidate in validated_candidates_list:
            candidate['status'] = 'Record_Saved'
            candidate['created_at'] = datetime.now(timezone.utc)
        
        collection.insert_many(validated_candidates_list)
        
        # The final, simple success message
        return "Candidate records were validated and saved in MongoDB."
        
    except Exception as e:
        return f"Database Error: Could not save records. Details: {e}"
    finally:
        if client:
            client.close()


def generate_onboarding_email_prompts() -> str:
    """
    Reads every candidate record from MongoDB, then for each:
      - Pulls First Name, Last Name, Email, Role
      - Builds a personalized onboarding email title/subject/body
      - Collects all emails into a JSON list

    Returns JSON-string with:
      {
        "status": "success"|"no_records"|"error",
        "emails": [ { "to","title","subject","body" }, … ],
        "message": error-or-info-text
      }
    """
    # Define role requirements inside the function to avoid module-level state
    ROLE_DOCUMENT_REQUIREMENTS = {
        "Software Engineer": [
            "Signed NDA",
            "Proof of identity (passport or driver's license or PAN card)",
            "Signed offer letter",
            "Educational certificates (degree/diploma in Computer Science/IT)",
            "Previous employment certificate",
            "Salary slip (last 3 months)",
            "Bank account details",
            "Technical skills assessment certificate",
            "Code of conduct acknowledgement",
            "Programming competency test results",
            "GitHub/portfolio submission",
            "System access request form"
        ],
        
        "Human Resources Executive": [
            "Signed NDA",
            "Proof of identity (passport or driver's license or PAN card)",
            "Signed offer letter",
            "Educational certificates (degree in HR/Psychology/Business Administration)",
            "Previous employment certificate",
            "Salary slip (last 3 months)",
            "Bank account details",
            "HR practices certification",
            "Employment law training certificate",
            "Enhanced confidentiality agreement",
            "HRIS system access form",
            "Background verification authorization",
            "Employee data handling training completion",
            "Conflict resolution certification"
        ]
    }
    
    client = None
    try:
        client = _get_mongo_client()
        client.server_info()
        coll = client['nextleap']['candidates']

        emails = []
        for cand in coll.find({}):
            first = cand.get("First Name", "").strip()
            last  = cand.get("Last Name", "").strip()
            to    = cand.get("Email", "").strip()
            role  = cand.get("Role", "").strip()

            if not (first and last and to and role):
                continue

            # Build title/subject
            subject = f"Welcome to NextLeap, {first}! Onboarding for your {role} Role"
            title   = subject  # add 'title' key

            # Document list
            docs = ROLE_DOCUMENT_REQUIREMENTS.get(role, [
                "Signed NDA",
                "Proof of identity",
                "Signed offer letter"
            ])
            docs_list = "\n".join(f"- {d}" for d in docs)

            body = (
                f"Hi {first} {last},\n\n"
                f"Congratulations on joining NextLeap as a {role}!\n\n"
                "To complete your onboarding, please prepare and upload the following documents:\n"
                f"{docs_list}\n\n"
                "If you have any questions, feel free to reach out. We're excited to have you on board!\n\n"
                "Best,\n"
                "The NextLeap HR Team"
            )

            emails.append({
                "to": to,
                "title": title,
                "subject": subject,
                "body": body
            })

            # Update the candidate record status to "Onboarding_Email_Sent" only when the email is successfully generated
            # This ensures we don't update the status if no email
            coll.update_one(
                {"_id": cand["_id"]},
                {"$set": {"status": "Onboarding_Email_Sent"}}
            )

        if not emails:
            return json.dumps({
                "status": "no_records",
                "emails": [],
                "message": "No complete candidate records found to generate emails."
            })

        return json.dumps({
            "status": "success",
            "emails": emails
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "emails": [],
            "message": f"Could not generate onboarding emails: {e}"
        })
    finally:
        if client:
            client.close()