# agent.py

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseConnectionParams

# This is the key configuration. It tells ADK to connect to the
# MCP server running at the specified URL instead of trying to run a command.
google_workspace_tools = MCPToolset(
    connection_params=SseConnectionParams(
        url="http://localhost:8000"
    )
)

# Define your ADK agent and give it the toolset
root_agent = LlmAgent(
    # Make sure to use a model you have access to
    model='gemini-2.5-flash',
    name='workspace_assistant',
    instruction='You are a helpful assistant. You have access to Google Workspace tools like Drive, Gmail, and Calendar.',
    tools=[google_workspace_tools],
)