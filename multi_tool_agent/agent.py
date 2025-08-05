# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os

from dotenv import load_dotenv
from fastapi.openapi.models import OAuth2
from fastapi.openapi.models import OAuthFlowAuthorizationCode
from fastapi.openapi.models import OAuthFlows
from google.adk import Agent
from google.adk.auth import AuthConfig
from google.adk.auth import AuthCredential
from google.adk.auth import AuthCredentialTypes
from google.adk.auth import OAuth2Auth
from google.adk.tools import ToolContext
from google.adk.tools.google_api_tool import SheetsToolset , CalendarToolset
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Load environment variables from .env file
load_dotenv()

# Access the variable
oauth_client_id = os.getenv("OAUTH_CLIENT_ID")
oauth_client_secret = os.getenv("OAUTH_CLIENT_SECRET")


SCOPES = ["https://www.googleapis.com/auth/calendar"]


calendar_toolset = CalendarToolset(
    client_id=oauth_client_id,
    client_secret=oauth_client_secret,
)




def read_calendar(
    calendar_id: str,
    tool_context: ToolContext,
) -> str:
    """Read events from a Google Calendar.

    Args:
        calendar_id (str): The ID of the calendar.

    Returns:
        str: A list of events from the calendar.
    """
    creds = None

    if "calendar_tool_tokens" in tool_context.state:
        creds = Credentials.from_authorized_user_info(
            tool_context.state["calendar_tool_tokens"], SCOPES
        )
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            auth_scheme = OAuth2(
                flows=OAuthFlows(
                    authorizationCode=OAuthFlowAuthorizationCode(
                        authorizationUrl="https://accounts.google.com/o/oauth2/auth",
                        tokenUrl="https://oauth2.googleapis.com/token",
                        scopes={
                            "https://www.googleapis.com/auth/calendar": (
                                "See, edit, share, and permanently delete all the calendars you can access using Google Calendar"
                            )
                        },
                    )
                )
            )
            auth_credential = AuthCredential(
                auth_type=AuthCredentialTypes.OAUTH2,
                oauth2=OAuth2Auth(
                    client_id=oauth_client_id, client_secret=oauth_client_secret,
                    redirect_uri="https://developers.google.com/oauthplayground"
                ),
            )
            auth_response = tool_context.get_auth_response(
                AuthConfig(
                    auth_scheme=auth_scheme, raw_auth_credential=auth_credential
                )
            )
            if auth_response:
                access_token = auth_response.oauth2.access_token
                refresh_token = auth_response.oauth2.refresh_token

                creds = Credentials(
                    token=access_token,
                    refresh_token=refresh_token,
                    token_uri=auth_scheme.flows.authorizationCode.tokenUrl,
                    client_id=oauth_client_id,
                    client_secret=oauth_client_secret,
                    scopes=list(auth_scheme.flows.authorizationCode.scopes.keys()),
                )
            else:
                tool_context.request_credential(
                    AuthConfig(
                        auth_scheme=auth_scheme,
                        raw_auth_credential=auth_credential,
                    )
                )
                return "Need User Authorization to access their Google Calendar."
        tool_context.state["calendar_tool_tokens"] = json.loads(creds.to_json())

    # service = build("calendar", "v3", credentials=creds)
    # events_result = (
    #     service.events()
    #     .list(calendarId=calendar_id, maxResults=10, singleEvents=True, orderBy="startTime")
    #     .execute()
    # )
    # events = events_result.get("items", [])
    # return json.dumps(events, indent=2)



root_agent = Agent(
    model="gemini-2.0-flash",
    name="google_calendar_agent",
    instruction="""
      You are a helpful Google Calendar assistant.
      Use the provided tools to read from Google Calendar.
""",
    tools=[read_calendar, calendar_toolset],
)