# File: my_custom_toolsets.py
# This file contains a "mimicked" version of the ADK's GoogleApiToolset
# that has been corrected to support a persistent credential store.

from __future__ import annotations
import logging
from typing import List, Optional, Union

# --- CORRECTED ABSOLUTE IMPORTS ---
# Using the exact structure you requested, expanded for all necessary classes.
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.auth.auth_credential import ServiceAccount
from google.adk.auth.auth_schemes import OpenIdConnectWithConfig
from google.adk.tools.base_toolset import BaseToolset, ToolPredicate
from google.adk.tools.openapi_tool import OpenAPIToolset
from google.adk.tools.google_api_tool.google_api_tool import GoogleApiTool
from google.adk.tools.google_api_tool.googleapi_to_openapi_converter import GoogleApiToOpenApiConverter

from google.oauth2.credentials import Credentials
from typing_extensions import override

logger = logging.getLogger("google_adk." + __name__)


class SimpleCredentialStore:
    """A simple in-memory credential store for the local development server."""
    def __init__(self):
        self._store = {}
    def read(self, key: str) -> Optional[Credentials]:
        return self._store.get(key)
    def write(self, key: str, creds: Credentials):
        self._store[key] = creds
    def clear(self):
        self._store = {}


# ==============================================================================
# THE MIMICKED `GoogleApiToolset`
# This is a direct copy of the source code you provided, modified to handle
# the credential store correctly.
# ==============================================================================
class PersistentGoogleApiToolset(BaseToolset):
  """
  A custom base toolset that mimics the ADK's GoogleApiToolset but is
  modified to correctly handle a credential_store.
  """
  def __init__(
      self,
      api_name: str,
      api_version: str,
      client_id: Optional[str] = None,
      client_secret: Optional[str] = None,
      tool_filter: Optional[Union[ToolPredicate, List[str]]] = None,
      service_account: Optional[ServiceAccount] = None,
      credential_store: Optional[SimpleCredentialStore] = None, # <-- THE ADDED ARGUMENT
  ):
    self.api_name = api_name
    self.api_version = api_version
    self._client_id = client_id
    self._client_secret = client_secret
    self._service_account = service_account
    # Save the credential store to the instance FIRST.
    self._credential_store = credential_store
    self.tool_filter = tool_filter
    # Now, this call will use OUR overridden version of the method below.
    self._openapi_toolset = self._load_toolset_with_oidc_auth()

  @override
  async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> List[GoogleApiTool]:
    """Get all tools in the toolset."""
    return [
        GoogleApiTool(tool, self._client_id, self._client_secret, self._service_account)
        for tool in await self._openapi_toolset.get_tools(readonly_context)
        if self._is_tool_selected(tool, readonly_context)
    ]

  # THIS IS THE MODIFIED METHOD - The key to the solution
  def _load_toolset_with_oidc_auth(self) -> OpenAPIToolset:
    """Loads the toolset and correctly injects the credential store."""
    spec_dict = GoogleApiToOpenApiConverter(self.api_name, self.api_version).convert()
    scope = list(spec_dict['components']['securitySchemes']['oauth2']['flows']['authorizationCode']['scopes'].keys())[0]
    return OpenAPIToolset(
        spec_dict=spec_dict,
        spec_str_type='yaml',
        auth_scheme=OpenIdConnectWithConfig(
            authorization_endpoint='https://accounts.google.com/o/oauth2/v2/auth',
            token_endpoint='https://oauth2.googleapis.com/token',
            userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
            revocation_endpoint='https://oauth2.googleapis.com/revoke',
            token_endpoint_auth_methods_supported=['client_secret_post', 'client_secret_basic'],
            grant_types_supported=['authorization_code'],
            scopes=[scope],
        ),
        # THE CRUCIAL INJECTION OF THE STORE:
        credential_store=self._credential_store
    )

  def configure_auth(self, client_id: str, client_secret: str):
    self._client_id = client_id
    self._client_secret = client_secret

  @override
  async def close(self):
    if self._openapi_toolset:
      await self._openapi_toolset.close()

# ==============================================================================
# Your final Calendar Toolset
# It inherits from our new, corrected base class.
# ==============================================================================
class MyCalendarToolset(PersistentGoogleApiToolset):
  """
  Our custom calendar tool that inherits persistence capabilities from our
  newly defined PersistentGoogleApiToolset base class.
  """
  def __init__(
      self,
      client_id: Optional[str] = None,
      client_secret: Optional[str] = None,
      tool_filter: Optional[Union[ToolPredicate, List[str]]] = None,
      service_account: Optional[ServiceAccount] = None,
      credential_store: Optional[SimpleCredentialStore] = None,
  ):
    # Pass all arguments, including the credential store, up to our
    # new PersistentGoogleApiToolset base class. This will no longer cause an error.
    super().__init__(
        api_name="calendar",
        api_version="v3",
        client_id=client_id,
        client_secret=client_secret,
        tool_filter=tool_filter,
        service_account=service_account,
        credential_store=credential_store,
    )