# File: myadktoolset.py
# This file defines custom toolsets for your agent, using the correct absolute imports.

from __future__ import annotations
import logging
from typing import List, Optional, Union

# --- CORRECTED ABSOLUTE IMPORTS ---
# We use the full, unambiguous path starting from the top-level package name ('langfun' or 'google')
# so that Python can find these classes from our external file.

# This path translates "from ...auth.auth_credential import ServiceAccount"
from google.adk.auth.auth_credential import ServiceAccount

# This path translates "from ..base_toolset import ToolPredicate"
from google.adk.tools.base_toolset import ToolPredicate

# This path translates "from .google_api_toolset import GoogleApiToolset"
from google.adk.tools.google_api_tool.google_api_toolset import GoogleApiToolset

# This is the required import for the credential object itself.
from google.oauth2.credentials import Credentials

logger = logging.getLogger("google_adk." + __name__)


class MySimpleCredentialStore:
    """A simple in-memory credential store for the local development server."""
    def __init__(self):
        self._store = {}

    def read(self, key: str) -> Optional[Credentials]:
        return self._store.get(key)

    def write(self, key: str, creds: Credentials):
        self._store[key] = creds

    def clear(self):
        self._store = {}


class MyCalendarToolset(GoogleApiToolset):
  """
  A Calendar toolset that correctly accepts a credential_store to enable
  persistent authentication during a server session.
  """
  def __init__(
      self,
      client_id: Optional[str] = None,
      client_secret: Optional[str] = None,
      tool_filter: Optional[Union[ToolPredicate, List[str]]] = None,
      service_account: Optional[ServiceAccount] = None,
      credential_store: Optional[MySimpleCredentialStore] = None,
  ):
    super().__init__(
        api_name="calendar",
        api_version="v3",
        client_id=client_id,
        client_secret=client_secret,
        tool_filter=tool_filter,
        service_account=service_account,
        credential_store=credential_store,
    )