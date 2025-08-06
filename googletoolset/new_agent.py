from google.adk.agents import Agent, LlmAgent
from google.adk.tools import google_search
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest
import pandas as pd
import io
import json
import pprint
from google.genai import types
from google.adk.tools.google_api_tool import CalendarToolset
import asyncio
from google.adk.sessions import InMemorySessionService, Session
from google.adk.auth import AuthConfig
from google.adk.runners import Runner
from google.genai.types import Content, Part
from dotenv import load_dotenv

load_dotenv()

# Assume these classes are available from the Google Agent Development Kit
# This is for creating a runnable example.
# In your actual agent code, you won't need to define these.
from typing import List, Optional

google_sheet_tool = CalendarToolset(client_id="13982625832-amp5pmtf70mk1uc13u134bt2phdfd2ot.apps.googleusercontent.com", client_secret="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")
    
def remove_unprocessable_file_from_llm_request(llm_request: LlmRequest):
    """
    Removes any binary data from the llm_request contents.

    Args:
        llm_request: The conversation history object.
    
    Returns:
        The modified llm_request with binary data removed.
    """
    # This will be our new, cleaned list of conversation turns (Content objects)
    filtered_contents = []
    
    # Iterate through each Content object (each turn of the conversation)
    for content in llm_request.contents:
        # Use a list comprehension to build a new list of parts,
        # keeping only those that DO NOT have inline_data.
        # This is a safe way to "remove" items from a list.
        kept_parts = [part for part in content.parts if not part.inline_data]

        # Check if this Content object is still useful after filtering.
        # If the 'kept_parts' list is not empty, it means there was text or
        # other data we want to keep.
        if kept_parts:
            # We create a new Content object to be safe, or modify the existing one.
            # Modifying is fine here since we're building a new outer list.
            content.parts = kept_parts
            filtered_contents.append(content)
        else:
            # If kept_parts is empty, the entire Content object (e.g., a user message)
            # consisted only of a file. We will effectively delete this entire turn
            # by not adding it to our filtered_contents list.
            print(
                f"\n[Callback] INFO: Removing entire Content block (role: '{content.role}') "
                "as it only contained file data."
            )

    # Finally, replace the original contents with our new, filtered list.
    llm_request.contents = filtered_contents
    
def convert_xlsx_to_json(data_bytes: bytes) -> Optional[str]:
    """
    Reads binary data of an .xlsx file and converts its first sheet to JSON.

    Args:
        data_bytes: The raw byte content of the .xlsx file.

    Returns:
        A JSON string representing the Excel data, or None if conversion fails.
    """
    try:
        # Use io.BytesIO to treat the byte string as a file in memory
        file_in_memory = io.BytesIO(data_bytes)
        
        # Read the Excel file using pandas. 'openpyxl' is the engine for .xlsx
        df = pd.read_excel(file_in_memory, engine='openpyxl')
        
        # Convert the DataFrame to a JSON string in 'records' orientation
        # (a list of dictionaries), which is a very common format.
        json_output = df.to_json(orient='records', indent=2)
        
        return json_output
        
    except ImportError:
        print("Error: The 'pandas' or 'openpyxl' library is not installed.")
        return None
    except Exception as e:
        print(f"Error converting Excel to JSON: {e}")
        return None

def process_request(llm_request: LlmRequest):
    """
    Finds an Excel file in the last user message, converts it to JSON,
    and removes the binary data from the llm_request.

    Args:
        llm_request: The conversation history object.
    
    Returns:
        A tuple containing (json_data, modified_llm_request)
    """
    # The most recent user input is the last item in the history
    last_user_content = llm_request.contents[-1]
    
    # Check if the last message is from the user
    if last_user_content.role != 'user':
        return None

    binary_data = None
    
    # Find the part containing the file data
    for part in last_user_content.parts:
        if part.inline_data:
            # Check if it's likely an excel file (optional but good practice)
            # XLSX files don't have a universal magic number, but often start
            # with 'PK' since they are zip archives.
            #if part.inline_data.data.startswith(b'PK\x03\x04'):
            binary_data = part.inline_data.data
            break

    if not binary_data:
        print("No Excel file found in the last user message.")
        return None

    # 1. CONVERT THE DATA TO JSON
    print("✅ File found. Converting to JSON...")
    if binary_data.startswith(b'PK\x03\x04'):
        excel_data_as_json = convert_xlsx_to_json(binary_data)
    
    if not excel_data_as_json:
        print("Failed to convert file data.")
        return None

    # 2. REMOVE THE BINARY DATA FROM THE REQUEST
    print("✅ Conversion successful.")
    
    # The llm_request object itself has now been modified in place.
    print("EXCEL DATA AS JSON:")
    print(excel_data_as_json)
    return excel_data_as_json

# --- Define the Callback Function ---
def simple_before_model_modifier(
    callback_context: CallbackContext, llm_request: LlmRequest
):
    """Inspects/modifies the LLM request or skips the call."""
    agent_name = callback_context.agent_name
    print(f"[Callback] Before model call for agent: {agent_name}")

    # Inspect the last user message in the request contents
    last_user_message = ""
    if llm_request.contents and llm_request.contents[-1].role == 'user':
         if llm_request.contents[-1].parts:
            last_user_message = llm_request.contents[-1].parts[0].text
    print(f"[Callback] Inspecting last user message: '{last_user_message}'")
    print("\n--- Pretty-printing LlmRequest: ---")
    #pprint.pprint(llm_request)
    print("----------------------------------\n")
    excel_data_as_json = process_request(llm_request)

    # 2. If JSON data was successfully created, inject it into the user's prompt
    if excel_data_as_json:
        # The user's message is the last one in the conversation history.
        # We only proceed if it's a 'user' role message.
        if llm_request.contents and llm_request.contents[-1].role == 'user':
            last_user_content = llm_request.contents[-1]

            # We create a formatted block to make it clear to the LLM
            # where the file content begins and ends.
            injected_content = (
                f"\n\n--- Content of Attached Excel File ---\n"
                f"{excel_data_as_json}\n"
                f"--- End of File Content ---"
            )

            # Search for an existing text part in the user's message
            text_part_found = False
            for part in last_user_content.parts:
                if part.text is not None:
                    # If found, append the JSON string to it
                    part.text += injected_content
                    text_part_found = True
                    print("[Callback] INFO: Appended file JSON to existing user prompt.")
                    break # Stop after modifying the first text part

            # If the user only uploaded a file (no text), create a new text part
            if not text_part_found:
                # .strip() removes leading newlines from our formatted block
                new_text_part = types.Part(text=injected_content.strip())
                # Add the new text part to the message
                last_user_content.parts.insert(0, new_text_part)
                print("[Callback] INFO: Created new text part with file JSON content.")

    remove_unprocessable_file_from_llm_request(llm_request)

root_agent = Agent(
    name="weather_time_agent",
    model="gemini-2.5-flash",
    description=(
        "Agent to read google sheets"
    ),
    instruction=(
        "You are a helpful agent who can read google sheets for the user."
    ),
    tools=[google_sheet_tool],
    sub_agents=[],
    #before_model_callback=simple_before_model_modifier
)

# Helper functions from the documentation to identify the auth request
def get_auth_request_function_call(event) -> types.FunctionCall | None:
    if not (event.content and event.content.parts):
        return None
    for part in event.content.parts:
        if (
            part
            and part.function_call
            and part.function_call.name == "adk_request_credential"
            and event.long_running_tool_ids
            and part.function_call.id in event.long_running_tool_ids
        ):
            return part.function_call
    return None

def get_auth_config(auth_request_function_call: types.FunctionCall) -> AuthConfig:
    if not (
        auth_request_function_call.args
        and (auth_config := auth_request_function_call.args.get("auth_config"))
    ):
        raise ValueError(
            f"Cannot get auth config from function call: {auth_request_function_call}"
        )
    if not isinstance(auth_config, AuthConfig):
        raise ValueError(
            f"Cannot get auth config {auth_config} is not an instance of AuthConfig."
        )
    return auth_config

# --- Main Application Logic ---
async def main():
    # ==============================================================================
    # 1. CONFIGURE TOOLS AND AGENT
    # ==============================================================================
    print("--- Step 1: Configuring Tools and Agent ---")

    # TODO: Replace with your actual OAuth 2.0 Client ID and Secret
    # oauth_client_id = "YOUR_CLIENT_ID.apps.googleusercontent.com"
    # oauth_client_secret = "YOUR_CLIENT_SECRET"

    # if "YOUR_CLIENT_ID" in oauth_client_id:
    #     print("WARNING: Please replace YOUR_CLIENT_ID and YOUR_CLIENT_SECRET.")
    #     return

    # Configure the pre-built Google Drive toolset with our credentials
    google_sheet_tool = CalendarToolset(client_id="13982625832-amp5pmtf70mk1uc13u134bt2phdfd2ot.apps.googleusercontent.com", client_secret="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")
 

    # Create the LLM Agent, providing the configured toolset
    drive_agent = LlmAgent(
        name="google_calendar_agent",
        model="gemini-2.5-flash",
        description=(
            "Agent to read google calendar"
        ),
        instruction=(
            "You are a helpful agent who can read google calendar for the user."
        ),
        tools=[google_sheet_tool]
    )
    print(f"Agent '{drive_agent.name}' created with Google Drive tools.")

    # ==============================================================================
    # 2. SETUP SESSION SERVICE AND RUNNER (FIXED CODE)
    # ==============================================================================
    print("\n--- Step 2: Setting up Session and Runner ---")

    session_service = InMemorySessionService()
    runner = Runner(agent=drive_agent, session_service=session_service, app_name="google_drive_agent")

    # Define identifiers for the conversation
    session = await session_service.create_session(app_name="google_drive_agent", user_id="user123")
    print(f"Session created with ID: {session.id}")


    # ==============================================================================
    # 3. RUN THE AGENT AND HANDLE THE AUTHENTICATION FLOW
    # ==============================================================================
    print("\n--- Step 3: Running the Agent ---")

    user_prompt_text = "list the first 5 events in my google calendar"
    print(f"User > {user_prompt_text}")

    # --- FIX 2: Create a `Content` object with a 'user' role ---
    user_message = Content(role="user", parts=[Part(text=user_prompt_text)])

    events_async = runner.run_async(session_id=session.id, new_message=user_message, user_id="user123")

    auth_request_id = None
    auth_request_uri = None

    async for event in events_async:

        print(event)
        # Check if the agent is requesting user authentication
        if auth_request := get_auth_request_function_call(event):
            print("\n--> AGENT REQUIRES USER AUTHENTICATION <--")
            auth_request_id = auth_request.id
            auth_config_info = get_auth_config(auth_request)

            # Build the full authorization URL
            base_auth_uri = auth_config_info.exchanged_auth_credential.oauth2.auth_uri
            redirect_uri = 'http://localhost:8000/callback' # MUST MATCH YOUR OAUTH CLIENT CONFIG

            auth_request_uri = base_auth_uri + f'&redirect_uri={redirect_uri}'

            print("\nACTION REQUIRED:")
            print("1. Ensure your FastAPI server (`callback_server.py`) is running.")
            print("2. Please visit this URL in your browser to authorize the application:")
            print(f"\n   {auth_request_uri}\n")
            break # Stop processing events, waiting for user to authorize

        # Handle the final response if no auth is needed or after it's complete
        # if event. == "finalize":
        #     print(f"Agent < {event.content.parts[0].text}")

    if auth_request_id:
        print("--- Waiting for user to complete authorization ---")
        print("After you authorize in the browser, the authorization code will appear in the FastAPI server's terminal.")
        print("The next step will be to send that code back to the agent.")


if __name__ == "__main__":
    asyncio.run(main())