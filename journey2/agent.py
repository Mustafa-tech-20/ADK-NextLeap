import requests
import vertexai
from typing import Dict, Any
import os
import json
from dotenv import load_dotenv






from vertexai import agent_engines
from vertexai.preview import reasoning_engines
from google.adk.tools import ToolContext , FunctionTool
from google.adk.sessions import InMemorySessionService
from google.adk.auth.auth_credential import AuthCredential, AuthCredentialTypes, OAuth2Auth
from google.adk.auth.auth_schemes import OpenIdConnectWithConfig
from google.auth.transport.requests import Request
from google.adk.agents import Agent
from google.oauth2 import id_token
from google.adk.auth import AuthConfig
from google.oauth2.credentials import Credentials




load_dotenv()  # This reads .env and sets the environment variables




# print(ToolContext._invocation_context.__dict__)




# vertexai.init(
#     project=PROJECT_ID,
#     location=LOCATION,
#     staging_bucket=STAGING_BUCKET,
# )


auth_scheme = OpenIdConnectWithConfig(
   authorization_endpoint="https://accounts.google.com/o/oauth2/auth",
   token_endpoint="https://oauth2.googleapis.com/token",
   scopes=["openid", "email", "profile"],
)


auth_credential = AuthCredential(
   auth_type=AuthCredentialTypes.OPEN_ID_CONNECT,
   oauth2=OAuth2Auth(
       client_id=os.environ["OAUTH_CLIENT_ID"],
       client_secret=os.environ["OAUTH_CLIENT_SECRET"],
       redirect_uri="https://developers.google.com/oauthplayground"
   ),
)








def get_exchange_rate(
   tool_context: ToolContext,
   currency_from: str = "USD",
   currency_to: str = "INR",
   currency_date: str = "latest",
) -> dict:
   """
   Retrieves the exchange rate between two currencies on a specified date,
   enforcing user authentication via OIDC.
   """
   TOKEN_CACHE_KEY = "exchange_tool_tokens"
   SCOPES = auth_scheme.scopes
   creds = None


   # Step 1: Check for cached & valid credentials in the session state. (This part is correct)
   cached = tool_context.state.get(TOKEN_CACHE_KEY)
   if cached:
       try:
           creds = Credentials.from_authorized_user_info(cached, SCOPES)
           if not creds.valid and creds.expired and creds.refresh_token:
               creds.refresh(Request())
               tool_context.state[TOKEN_CACHE_KEY] = json.loads(creds.to_json())
           elif not creds.valid:
               creds = None
               tool_context.state.pop(TOKEN_CACHE_KEY, None)
       except Exception as e:
           print(f"Error loading/refreshing cached creds: {e}")
           creds = None
           tool_context.state.pop(TOKEN_CACHE_KEY, None)


   # Step 2: If no valid credentials, check for an auth response from the client. (This part is correct)
   if not creds or not creds.valid:
       exchanged = tool_context.get_auth_response(
           AuthConfig(auth_scheme=auth_scheme, raw_auth_credential=auth_credential)
       )
       if exchanged:
           # We correctly build the Credentials object without the id_token
           creds = Credentials(
               token=exchanged.oauth2.access_token,
               refresh_token=exchanged.oauth2.refresh_token,
               token_uri=auth_scheme.token_endpoint,
               client_id=auth_credential.oauth2.client_id,
               client_secret=auth_credential.oauth2.client_secret,
               scopes=SCOPES,
           )
           tool_context.state[TOKEN_CACHE_KEY] = json.loads(creds.to_json())
       else:
           # Step 3: Initiate authentication request. (This part is correct)
           auth_config = AuthConfig(
               auth_scheme=auth_scheme,
               raw_auth_credential=auth_credential,
           )
           # print("Generatedauth URL:", auth_scheme.get_authorization_url(auth_config))


           tool_context.request_credential(auth_config)
           return {"pending": True, "message": "Awaiting user authentication."}


   if not creds or not creds.valid:
       return {"status": "error", "error_message": "Authentication failed or was not completed."}


   # **** Step 4: CORRECTED LOGIC - Get user info from the UserInfo endpoint ****
   try:
       # We use the access token to get the user's profile information.
       userinfo_response = requests.get(
           "https://www.googleapis.com/oauth2/v3/userinfo",
           headers={"Authorization": f"Bearer {creds.token}"}
       )
       userinfo_response.raise_for_status() # Raise an exception for bad status codes
       user_info = userinfo_response.json()
       user_email = user_info.get("email", "<unknown>")
       print(f"This tool was invoked by user: {user_email}")
   except Exception as e:
       # This can happen if the token is invalid or the API call fails
       return {"status": "error", "error_message": f"Could not retrieve user identity: {e}"}




   # Step 5: Make the authenticated API call. (This part is correct)
   try:
       resp = requests.get(
           f"https://api.frankfurter.app/{currency_date}",
           params={"from": currency_from, "to": currency_to},
           # Note: This specific API doesn't require auth, but we include the header
           # as a demonstration of how to use the token for a real protected API.
           headers={"Authorization": f"Bearer {creds.token}"}
       )
       resp.raise_for_status()
       data = resp.json()
   except Exception as e:
       return {"status": "error", "error_message": str(e)}


   # Step 6: Return tool result.
   return {
       "status": "success",
       "invoked_by": user_email,
       "exchange": data,
   }


# --- Tool & Agent setup ---


# CORRECTED: FunctionTool is initialized only with the function.
# The authentication logic is now self-contained within get_exchange_rate. [1]
exchange_tool = FunctionTool(
   func=get_exchange_rate,
)


# Agent setup remains the same.


root_agent = Agent(
   name="currency_converter_agent",
   # It's good practice to use a model that supports tool use well.
   model="gemini-2.5-flash",
   description="Converts currency; requires user login to identify who's calling.",
   instruction="You are a currency converter. You must always use the get_exchange_rate tool. When you get the result, state the exchange rate and mention who it was invoked by.",
   tools=[exchange_tool],
)
