import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams , StreamableHTTPConnectionParams
from mcp.client.stdio import StdioServerParameters 
from dotenv import load_dotenv
from .custom_read_tools import   process_and_save_candidates , generate_onboarding_email_prompts
from .prompt import system_prompt

load_dotenv()

clientid = os.getenv("OAUTH_CLIENT_ID")
clientsecret = os.getenv("OAUTH_CLIENT_SECRET")

# Define the absolute path to your MCP server directory
MCP_SERVER_PATH = "/Users/mustafa.mohammed/Documents/google_workspace_mcp"

MCP_SERVER_URL="https://workspace-mcp-13982625832.us-central1.run.app"

# Verify the path exists
if not os.path.exists(MCP_SERVER_PATH):
    raise ValueError(f"MCP server path does not exist: {MCP_SERVER_PATH}")

# Verify main.py exists in the server directory
main_py_path = os.path.join(MCP_SERVER_PATH, "main.py")
if not os.path.exists(main_py_path):
    raise ValueError(f"main.py not found at: {main_py_path}")

root_agent = LlmAgent(
    model ='gemini-2.5-flash',
    name ='google_workspace_agent',
    instruction = system_prompt ,
    tools=[
         MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=MCP_SERVER_URL
            ),
        ), process_and_save_candidates, generate_onboarding_email_prompts
    ],
)

# Alternative configuration if you're not using uv to manage the Python environment
# and want to run the MCP server directly with Python:
"""
root_agent = LlmAgent(
    model='gemini-2.0-flash',
    name='filesystem_assistant_agent',
    instruction='Help the user manage their files. You can list files, read files, etc.',
    tools=[
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='python',
                    args=[
                        os.path.join(MCP_SERVER_PATH, "main.py")
                    ],
                    env={
                        "GOOGLE_OAUTH_CLIENT_ID": clientid,
                        "GOOGLE_OAUTH_CLIENT_SECRET": clientsecret,
                        "OAUTHLIB_INSECURE_TRANSPORT": "1"
                    }
                ),
            ),
        )
    ],
)
"""