"""Keep the real GitHub CLI (gh) OAuth token inside the proxy process.

The agent only ever holds a stub token. The real token is injected only
into requests whose *actual upstream host* (``request.host``, not the
spoofable ``pretty_host``) is an authorized GitHub CLI endpoint:

* ``api.github.com`` (REST/GraphQL) — ``Authorization: token <stub>`` or
  ``Bearer <stub>``, scheme preserved, value swapped.
* ``github.com`` (git-over-HTTPS via gh's git-credential-helper) and
  ``nuget.pkg.github.com`` (the private NuGet feed) — HTTP Basic auth; only
  the password slot ever carries our stub (gh's credential helper and the
  documented ``dotnet nuget`` command both put the token there), so only
  the password is swapped and the username is passed through unchanged.
"""

from __future__ import annotations

import base64
import binascii
import logging
from pathlib import Path

from mitmproxy import http

from token_store import OAuthBrokerAddon

logger = logging.getLogger(__name__)

TOKEN_HOST = "github.com"
TOKEN_PATH = "/login/oauth/access_token"
API_HOST = "api.github.com"
NUGET_HOST = "nuget.pkg.github.com"

TOKEN_SCHEME_HOSTS = {API_HOST}
BASIC_AUTH_HOSTS = {TOKEN_HOST, NUGET_HOST}

TOKEN_STORE = Path("/home/mitmproxy/.mitmproxy-token/github-cli-token.json")

STUB_ACCESS_TOKEN = "gho_STUB0000000000000000000000000000000000"

# Empirically captured from a real `gh auth login` device flow against the
# running proxy. github.com/login/oauth/access_token is shared by every OAuth
# app that uses GitHub's device flow, so this avoids stealing/stubbing another
# app's token exchange.
GH_CLI_CLIENT_ID = "178c6fc778ccc68e1d6a"
COPILOT_TOKEN_EXCHANGE_PATH_PREFIX = "/copilot_internal/"


class GitHubCliAuthInterceptor(OAuthBrokerAddon):
    label = "GitHub CLI"
    store_path = TOKEN_STORE

    def __init__(self) -> None:
        self._access_token: str | None = None
        if GH_CLI_CLIENT_ID.startswith("REPLACE_ME"):
            logger.warning(
                "[ai-buddy] GH_CLI_CLIENT_ID is still a placeholder; "
                "gh auth login token exchanges will not be captured or "
                "authorized until it is set to the real client_id"
            )

    def _apply_stored_tokens(self, tokens: dict) -> None:
        access_token = tokens.get("access_token")
        if isinstance(access_token, str) and access_token:
            self._access_token = access_token

    def request(self, flow: http.HTTPFlow) -> None:
        if flow.request.host == TOKEN_HOST and flow.request.path.split("?", 1)[0] == TOKEN_PATH:
            return

        host = flow.request.host
        if host in TOKEN_SCHEME_HOSTS:
            if flow.request.path.startswith(COPILOT_TOKEN_EXCHANGE_PATH_PREFIX):
                return
            self._inject_token_scheme(flow)
        elif host in BASIC_AUTH_HOSTS:
            self._inject_basic_auth(flow)

    def set_access_token(self, token: str) -> None:
        self._access_token = token
        self._persist_token()

    # -- api.github.com: "token"/"Bearer" scheme, scheme-preserving swap ---

    def _inject_token_scheme(self, flow: http.HTTPFlow) -> None:
        authorization = flow.request.headers.get("authorization")
        if not authorization:
            return

        scheme, _, value = authorization.partition(" ")
        if scheme.lower() not in ("token", "bearer") or value != STUB_ACCESS_TOKEN:
            # Fail-closed: an authorized GitHub API host must only ever see
            # our stub. Any other credential is anomalous and rejected so a
            # real token cannot be smuggled back out through this path.
            flow.response = self._reject(
                "ai-buddy: unexpected credential on GitHub API host; "
                "only the stub token is allowed"
            )
            return

        if not self._access_token:
            flow.response = self._reject(
                "GitHub CLI token mapping is not available; re-login required"
            )
            return

        flow.request.headers["authorization"] = f"{scheme} {self._access_token}"

    # -- github.com (git) / nuget.pkg.github.com: Basic auth password swap -

    def _inject_basic_auth(self, flow: http.HTTPFlow) -> None:
        authorization = flow.request.headers.get("authorization")
        if not authorization:
            return

        scheme, _, encoded = authorization.partition(" ")
        if scheme.lower() != "basic":
            flow.response = self._reject(
                "ai-buddy: unexpected auth scheme on GitHub host; "
                "only Basic auth with the stub token is allowed"
            )
            return

        try:
            decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            flow.response = self._reject("ai-buddy: malformed Basic auth credential")
            return

        username, sep, password = decoded.partition(":")
        if not sep or password != STUB_ACCESS_TOKEN:
            # Fail-closed: the password slot must always carry our stub (gh's
            # git-credential-helper and `dotnet nuget` both put the token
            # there). Any other password is anomalous and rejected; the
            # username varies (gh login or "x-access-token") and is passed
            # through unchanged.
            flow.response = self._reject(
                "ai-buddy: unexpected credential on GitHub host; "
                "only the stub token is allowed"
            )
            return

        if not self._access_token:
            flow.response = self._reject(
                "GitHub CLI token mapping is not available; re-login required"
            )
            return

        new_encoded = base64.b64encode(
            f"{username}:{self._access_token}".encode()
        ).decode("ascii")
        flow.request.headers["authorization"] = f"Basic {new_encoded}"

    def _persist_token(self) -> None:
        self._persist({"access_token": self._access_token})
