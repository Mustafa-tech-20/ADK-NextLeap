import io


from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google.adk.tools import FunctionTool
import google.genai.types as types
from fastapi import UploadFile


import requests
from fastapi import FastAPI
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService




session_service = InMemorySessionService()










def get_exchange_rate(
   currency_from: str = "USD",
   currency_to: str = "INR",
   currency_date: str = "latest",
):
   """Retrieves the exchange rate between two currencies on a specified date."""


   response = requests.get(
       f"https://api.frankfurter.app/{currency_date}",
       params={"from": currency_from, "to": currency_to},
   )
   return response.json()




root_agent = Agent(
   name="excel_reader_agent",
   model="gemini-2.5-flash",
   description=(
"an angent that reads the user uploaded file"    ),
   instruction=(
       "You are a currency converter , alwasy greet the user with the appropriat message based on this context. "
   ),
   tools=[FunctionTool(func=get_exchange_rate)]
)






def read_file(file : UploadFile) ->str :
   """Reads the uploaded file and prints the filename."""
   print(file.filename)
   return f"File {file.filename} has been read successfully."
def convert_excel_to_json(  # type: ignore
 
) -> str:
   """
   Loads the user‑uploaded Excel file.


   Args:
      file: The uploaded Excel file object injected by ADK.


   Returns:
       dict: {
         "status": "success"
       }
       or {
         "status": "error"
       }
   """
   try:
      
       return {"status": "success"}
      
   except Exception as e:
       return {
           "status": "error"
       }




async def list_user_files_py(tool_context: ToolContext) -> str:
   """Tool to list available artifacts for the user."""
   try:
       available_files = await tool_context.list_artifacts()
       if not available_files:
           return "You have no saved artifacts."
       else:
           # Format the list for the user/LLM
           file_list_str = "\n".join([f"- {fname}" for fname in available_files])
           return f"Here are your available Python artifacts:\n{file_list_str}"
   except ValueError as e:
       print(f"Error listing Python artifacts: {e}. Is ArtifactService configured?")
       return "Error: Could not list Python artifacts."
   except Exception as e:
       print(f"An unexpected error occurred during Python artifact list: {e}")
       return "Error: An unexpected error occurred while listing Python artifacts."




# wrap it as a FunctionTool so ADK can parse its signature
excel_json_tool = FunctionTool(
   func=convert_excel_to_json
)




from google.adk.artifacts import InMemoryArtifactService # Or GcsArtifactService
from google.adk.agents import LlmAgent # Any agent
from google.adk.sessions import InMemorySessionService


# Example: Configuring the Runner with an Artifact Service
#my_agent = LlmAgent(name="artifact_user_agent", model="gemini-2.0-flash")
artifact_service = InMemoryArtifactService() # Choose an implementation
session_service = InMemorySessionService()


def save_artifacts(tool_context: ToolContext, filename: str, file_bytes: bytes) -> dict:
   """
   Tool to save an uploaded file as an artifact.
   Must use exactly tool_context: ToolContext as first parameter.
   """
   csv_artifact = types.Part.from_data(data=file_bytes, mime_type="text/csv")
   version = tool_context.save_artifact(filename=filename, artifact=csv_artifact)
   return {"status": "success", "version": version}




# root_agent = Agent(
#     name="excel_reader_agent",
#     model="gemini-2.5-flash",
#     description=(
# "an angent that reads the user uploaded file"    ),
#     instruction=(
#         "Always call the read_file function / tool when the user uploads a file. "
#     ),
#     tools=[FunctionTool(func=read_file)]
# )


root_agent = Agent(
   name="excel_reader_agent",
   model="gemini-2.5-flash",
   description=(
"an angent that reads the user uploaded file"    ),
   instruction=(
       "You are a currency converter , alwasy greet the user with the appropriat message based on this context. "
   ),
   tools=[FunctionTool(func=get_exchange_rate)]
)
# runner = Runner(
#     agent=root_agent,
   # app_name="multi_tool_agent",
   # session_service=session_service,
#     artifact_service=artifact_service # Provide the service instance here
# )


