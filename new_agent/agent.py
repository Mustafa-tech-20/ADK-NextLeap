from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import OpenAPIToolset
from fastapi.openapi.models import OAuth2
from fastapi.openapi.models import OAuthFlowAuthorizationCode
from fastapi.openapi.models import OAuthFlows
from google.adk.auth import AuthCredential
from google.adk.auth import AuthCredentialTypes
from google.adk.auth import OAuth2Auth
from dotenv import load_dotenv
import os
from google.adk.tools.application_integration_tool.application_integration_toolset import ApplicationIntegrationToolset
from google.adk.agents import Agent
from google.genai import types

load_dotenv()

oauth_client_id = os.getenv("OAUTH_CLIENT_ID")
oauth_client_secret = os.getenv("OAUTH_CLIENT_SECRET")


auth_scheme = OAuth2(
    flows=OAuthFlows(
        authorizationCode=OAuthFlowAuthorizationCode(
            authorizationUrl="https://accounts.google.com/o/oauth2/auth",
            tokenUrl="https://oauth2.googleapis.com/token",
            scopes={
                "https://www.googleapis.com/auth/drive.readonly": "readonly",
                "https://www.googleapis.com/auth/drive.metadata": "metadata readonly"
            },
        )
    )
)

auth_credential = AuthCredential(
    auth_type=AuthCredentialTypes.OAUTH2,
    oauth2=OAuth2Auth(
        client_id=oauth_client_id, 
        client_secret=oauth_client_secret
    ),
)

gdrive_connection_toolset = ApplicationIntegrationToolset(
            project=os.getenv("PROJECT_ID"), 
            location=os.getenv("LOCATION"), 
            connection="gdrive-connection-with-auth", 
            entity_operations={},
            actions=[],
            ##service_account_credentials='{...}', # optional
            tool_name_prefix="mygdrive",
            tool_instructions="Use this tool to work with gdrive",
            auth_credential=auth_credential,
            auth_scheme=auth_scheme
 )

root_agent = Agent(
        model="gemini-2.5-flash",
        name="google_drive_agent",
        description="You are helpful assitant answering all kinds of questions",
        instruction="If they ask you how you were created, tell them you were created with the Google Agent Framework.",
        generate_content_config=types.GenerateContentConfig(temperature=0.2),
        tools = [gdrive_connection_toolset],
)