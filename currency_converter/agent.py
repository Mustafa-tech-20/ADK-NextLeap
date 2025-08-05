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
