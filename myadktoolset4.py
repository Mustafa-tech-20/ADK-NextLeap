# File: my_custom_toolsets.py
# This is the final, corrected version with the proper class structure.

from __future__ import annotations
import json
import logging
from typing import Any, Dict, List, Literal, Optional, Union, Final

# --- CORRECTED ABSOLUTE IMPORTS ---
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.auth.auth_credential import AuthCredential, ServiceAccount
from google.adk.auth.auth_schemes import AuthScheme, OpenIdConnectWithConfig
from google.adk.tools.base_toolset import BaseToolset, ToolPredicate
from google.adk.tools.openapi_tool.openapi_spec_parser import OpenApiSpecParser
from google.adk.tools.openapi_tool.openapi_spec_parser.rest_api_tool import RestApiTool
from google.adk.tools.openapi_tool.openapi_spec_parser import OpenApiSpecParser, ParsedOperation
from google.adk.tools.openapi_tool.openapi_spec_parser.tool_auth_handler import ToolAuthHandler


from google.adk.tools.google_api_tool.google_api_tool import GoogleApiTool
from google.adk.tools.google_api_tool.googleapi_to_openapi_converter import GoogleApiToOpenApiConverter
from google.oauth2.credentials import Credentials
from typing_extensions import override
import yaml
import requests


logger = logging.getLogger("google_adk." + __name__)


class SimpleCredentialStore:
    """
    A simple in-memory store that implements the correct interface with the
    correct method signatures expected by the ADK's ToolAuthHandler.
    """
    def __init__(self):
        self._store = {}
        print("Initialized SimpleCredentialStore with corrected method signatures.")

    def _get_key(self, auth_scheme: AuthScheme, auth_credential: AuthCredential) -> str:
        """Creates a unique key from the auth objects."""
        # This logic is based on how the ADK creates keys internally.
        if auth_scheme:
            return f"{auth_scheme.type_.name}_{hash(auth_scheme.model_dump_json())}"
        if auth_credential:
            return f"user_provided_{hash(auth_credential.model_dump_json())}"
        return "default_key"

    def get_credential(
        self, auth_scheme: AuthScheme, auth_credential: AuthCredential
    ) -> Optional[Credentials]:
        """
        Gets a credential from the store. This method signature now correctly
        matches the ADK framework's call.
        """
        key = self._get_key(auth_scheme, auth_credential)
        print(f"STORE: Getting credential for key: {key}")
        return self._store.get(key)

    def set_credential(
        self, auth_scheme: AuthScheme, auth_credential: AuthCredential, creds: Credentials
    ):
        """
        Saves a credential to the store. This method signature now correctly
        matches the ADK framework's call.
        """
        key = self._get_key(auth_scheme, auth_credential)
        print(f"STORE: Setting credential for key: {key}")
        self._store[key] = creds




# ==============================================================================
# STEP 2: THE MIMICKED `RestApiTool`
# This class correctly injects the store into the ToolAuthHandler.
# ==============================================================================
class PersistentRestApiTool(RestApiTool):
    """A mimicked RestApiTool that correctly handles a credential_store."""
    def __init__(self, credential_store: Optional[SimpleCredentialStore] = None, **kwargs):
        self.credential_store = credential_store
        super().__init__(**kwargs)

    @classmethod
    def from_parsed_operation(
        cls, parsed: ParsedOperation,
        credential_store: Optional[SimpleCredentialStore] = None
    ) -> "PersistentRestApiTool":
        """Creates an instance and attaches the credential store."""
        # Helper to get the snake_case name
        tool_name = "_".join(parsed.operation.operationId.lower().split())

        generated = cls(
            name=tool_name[:60],
            description=parsed.operation.description or parsed.operation.summary or "",
            endpoint=parsed.endpoint, operation=parsed.operation,
            auth_scheme=parsed.auth_scheme, auth_credential=parsed.auth_credential,
            credential_store=credential_store,
        )
        return generated

    @override
    async def call(self, *, args: dict[str, Any], tool_context: Optional[ReadonlyContext]) -> Dict[str, Any]:
        """Executes the call, injecting the credential store into the auth handler."""
        tool_auth_handler = ToolAuthHandler.from_tool_context(
            tool_context, self.auth_scheme, self.auth_credential
        )
        # *** The Core Fix ***
        # We assign our store to the handler *after* it's created.
        # This will now work because our store has the get_credential method.
        if self.credential_store:
            tool_auth_handler.credential_store = self.credential_store

        auth_result = await tool_auth_handler.prepare_auth_credentials()
        if auth_result.state == "pending":
            return {"pending": True, "message": "Needs your authorization."}

        # The rest of the logic remains the same
        api_params, api_args = self._operation_parser.get_parameters().copy(), args
        if auth_result.auth_credential:
            auth_param, auth_args = self._prepare_auth_request_params(
                auth_result.auth_scheme, auth_result.auth_credential
            )
            if auth_param and auth_args:
                api_params = [auth_param[0]] + api_params if isinstance(auth_param, list) else [auth_param] + api_params
                api_args.update(auth_args)
        request_params = self._prepare_request_params(api_params, api_args)
        response = requests.request(**request_params)
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError:
            return {"error": f"Tool {self.name} failed: {response.content.decode('utf-8')}"}
        except ValueError:
            return {"text": response.text}



# ==============================================================================
# STEP 2: MIMIC OF `OpenAPIToolset`
# This version is now changed to create our new `PersistentRestApiTool`.
# ==============================================================================
class PersistentOpenApiToolset(BaseToolset):
  """
  A mimicked OpenAPIToolset that creates PersistentRestApiTools.
  """
  def __init__(
      self, *, spec_dict: Optional[Dict[str, Any]] = None,
      tool_filter: Optional[Union[ToolPredicate, List[str]]] = None,
      credential_store: Optional[SimpleCredentialStore] = None,
      auth_scheme: Optional[AuthScheme] = None,
  ):
    super().__init__(tool_filter=tool_filter)
    self._credential_store = credential_store
    self._tools: Final[List[PersistentRestApiTool]] = list(self._parse(spec_dict))
    if auth_scheme:
        for tool in self._tools:
            tool.configure_auth_scheme(auth_scheme)

  def _parse(self, openapi_spec_dict: Dict[str, Any]) -> List[PersistentRestApiTool]:
    """Overrides the parse method to create our persistent tools."""
    operations = OpenApiSpecParser().parse(openapi_spec_dict)
    return [PersistentRestApiTool.from_parsed_operation(o, self._credential_store) for o in operations]

  @override
  async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> List[PersistentRestApiTool]:
    return [tool for tool in self._tools if self._is_tool_selected(tool, readonly_context)]
  @override
  async def close(self): pass


# ==============================================================================
# STEP 3: MIMIC OF `GoogleApiToolset`
# This version now uses our `PersistentOpenApiToolset`.
# ==============================================================================
class PersistentGoogleApiToolset(BaseToolset):
  """
  A mimicked GoogleApiToolset that uses our PersistentOpenApiToolset.
  """
  def __init__(
      self, api_name: str, api_version: str, client_id: Optional[str] = None,
      client_secret: Optional[str] = None, tool_filter: Optional[Union[ToolPredicate, List[str]]] = None,
      service_account: Optional[ServiceAccount] = None, credential_store: Optional[SimpleCredentialStore] = None,
  ):
    self.api_name, self.api_version = api_name, api_version
    self._client_id, self._client_secret = client_id, client_secret
    self._service_account, self._credential_store = service_account, credential_store
    self.tool_filter = tool_filter
    self._openapi_toolset = self._load_toolset_with_oidc_auth()

  def _load_toolset_with_oidc_auth(self) -> PersistentOpenApiToolset:
    """This method now creates an instance of our PersistentOpenApiToolset."""
    spec_dict = GoogleApiToOpenApiConverter(self.api_name, self.api_version).convert()
    scope = list(spec_dict['components']['securitySchemes']['oauth2']['flows']['authorizationCode']['scopes'].keys())[0]
    return PersistentOpenApiToolset(
        spec_dict=spec_dict,
        auth_scheme=OpenIdConnectWithConfig(
            authorization_endpoint='https://accounts.google.com/o/oauth2/v2/auth',
            token_endpoint='https://oauth2.googleapis.com/token', scopes=[scope],
        ),
        credential_store=self._credential_store,
    )
  @override
  async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> List[GoogleApiTool]:
    return [
        GoogleApiTool(tool, self._client_id, self._client_secret, self._service_account)
        for tool in await self._openapi_toolset.get_tools(readonly_context)
        if self._is_tool_selected(tool, readonly_context)
    ]
  def configure_auth(self, client_id: str, client_secret: str):
    self._client_id, self._client_secret = client_id, client_secret
  @override
  async def close(self):
    if self._openapi_toolset: await self._openapi_toolset.close()


# ==============================================================================
# STEP 4: YOUR FINAL CALENDAR TOOLSET
# This remains the same, inheriting from our new top-level base class.
# ==============================================================================
class MyCalendarToolset(PersistentGoogleApiToolset):
  """Our final custom calendar tool that inherits full persistence capabilities."""
  def __init__(
      self, client_id: Optional[str] = None, client_secret: Optional[str] = None,
      tool_filter: Optional[Union[ToolPredicate, List[str]]] = None, service_account: Optional[ServiceAccount] = None,
      credential_store: Optional[SimpleCredentialStore] = None,
  ):
    super().__init__(
        api_name="calendar", api_version="v3", client_id=client_id, client_secret=client_secret,
        tool_filter=tool_filter, service_account=service_account, credential_store=credential_store,
    )