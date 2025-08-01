
import requests
import vertexai
from typing import Dict, Any
import os
from dotenv import load_dotenv

from vertexai import agent_engines
from vertexai.preview import reasoning_engines
from google.adk.tools import ToolContext
from google.adk.tools.google_api_tool import CalendarToolset

from google.adk.agents import Agent
from google.oauth2.credentials import Credentials
from typing import Optional

from google.adk.tools import FunctionTool

from myadktoolset4 import SimpleCredentialStore, MyCalendarToolset

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = "us-central1"
STAGING_BUCKET = os.getenv("STAGING_BUCKET")

print("Initializing credential store...")
cred_store = SimpleCredentialStore()


# vertexai.init(
#     project=PROJECT_ID,
#     location=LOCATION,
#     staging_bucket=STAGING_BUCKET,
# )



# Example: Configuring Google Calendar Tools


client_id = os.getenv("OAUTH_CLIENT_ID")
client_secret = os.getenv("OAUTH_CLIENT_SECRET")


print("Initializing MyCalendarToolset with credential store...")
calendar_tool = MyCalendarToolset(credential_store=cred_store)

calcal= CalendarToolset()

print("Configuring OAuth credentials for the toolset...")
calendar_tool.configure_auth(
    client_id=client_id, client_secret=client_secret
)


root_agent = Agent(
   name="calendar_agent",
   model="gemini-2.5-flash",
   description=(
   "an angent that reads users google calendar"   
   ),
   instruction=(
       "You are an agent that mananges google calendar for the user , always greet the user with the appropriate message based on this context. "
   ),
   tools = [calendar_tool]
)




# remote_app = agent_engines.create(
#     agent_engine=root_agent,
#     requirements=[
#         "google-cloud-aiplatform[adk,agent_engines]",
#     ]
# )




# app = reasoning_engines.AdkApp(
#     agent=root_agent,
#     enable_tracing=True,
# )


# session = app.create_session(user_id="u_123")
# print("Session created", session)





