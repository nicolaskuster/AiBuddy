"""Keep real GitHub Copilot OAuth tokens inside the proxy process.

The agent only ever holds stub tokens. Real tokens are injected only into
requests whose *actual upstream host* (``request.host``, not the spoofable
``pretty_host``) is an authorized Copilot endpoint, and captured token
responses are stubbed fail-closed so a real token never reaches the agent.
"""

from __future__ import annotations

import json
from pathlib import Path

from mitmproxy import http

from token_store import OAuthBrokerAddon

# OpenCode and Pi use different GitHub OAuth apps for Copilot. The token
# endpoint is shared, so the capture addon must recognize both client IDs.
COPILOT_CLIENT_IDS = {
    "Ov23li8tweQw6odWQebz",  # OpenCode
    "Iv1.b507a08c87ecfe98",  # Pi
}
API_HOST = "api.githubcopilot.com"
INDIVIDUAL_API_HOST = "api.individual.githubcopilot.com"
API_HOSTS = {API_HOST, INDIVIDUAL_API_HOST}
TOKEN_EXCHANGE_HOST = "api.github.com"
TOKEN_EXCHANGE_PATH_PREFIX = "/copilot_internal/"
TOKEN_STORE = Path("/home/mitmproxy/.mitmproxy-token/github-copilot-token.json")

STUB_ACCESS_TOKEN = "ghu_STUB000000000000000000000000000000000000"
STUB_SESSION_TOKEN = (
    "tid=STUB0000000000000000000000000000000000;"
    "exp=4102444800;proxy-ep=proxy.individual.githubcopilot.com;stub=1"
)


class GitHubCopilotAuthInterceptor(OAuthBrokerAddon):
    label = "GitHub Copilot"
    store_path = TOKEN_STORE

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._session_token: str | None = None
        self._session_stub_token = STUB_SESSION_TOKEN
        self._session_api_host: str | None = None

    def _apply_stored_tokens(self, tokens: dict) -> None:
        access_token = tokens.get("access_token")
        session_token = tokens.get("session_token")
        if isinstance(access_token, str) and access_token:
            self._access_token = access_token
        if isinstance(session_token, str) and session_token:
            self._session_token = session_token
            self._session_stub_token = self._build_session_stub_token(session_token)
            self._session_api_host = self._api_host_from_session_token(session_token)

    def request(self, flow: http.HTTPFlow) -> None:
        if not self._is_authorized_host(flow.request):
            return

        authorization = flow.request.headers.get("authorization")
        if not authorization:
            return

        if authorization == f"Bearer {STUB_ACCESS_TOKEN}":
            self._inject(flow, self._access_token, "OAuth")
            return

        if authorization == f"Bearer {self._session_stub_token}":
            self._inject(flow, self._session_token, "session")
            return

        # Fail-closed: an authorized Copilot host must only ever see our stubs.
        # Any other bearer is anomalous and rejected so a real token cannot be
        # smuggled back out through this path.
        flow.response = self._reject(
            "ai-buddy: unexpected credential on Copilot host; "
            "only stub tokens are allowed"
        )

    def _inject(self, flow: http.HTTPFlow, real_token: str | None, kind: str) -> None:
        if real_token:
            flow.request.headers["authorization"] = f"Bearer {real_token}"
            return

        flow.response = self._reject(
            f"GitHub Copilot {kind} token mapping is not available; re-login required"
        )

    def _is_authorized_host(self, request: http.Request) -> bool:
        # Gate on the real upstream host, never the spoofable Host header.
        if request.host in API_HOSTS:
            return True

        if self._session_api_host and request.host == self._session_api_host:
            return True

        return (
            request.host == TOKEN_EXCHANGE_HOST
            and request.path.startswith(TOKEN_EXCHANGE_PATH_PREFIX)
        )

    def response(self, flow: http.HTTPFlow) -> None:
        if flow.response is None:
            return

        if self._is_token_exchange_request(flow.request):
            self._sanitize_session_response(flow.response)

    def set_access_token(self, token: str) -> None:
        self._access_token = token
        self._persist_token()

    def _sanitize_session_response(self, response: http.Response) -> None:
        if not response.content:
            return

        body = self._parse_json_object(response)
        if body is None:
            self._block(response, "session token response could not be sanitized")
            return

        token = body.get("token")
        if not isinstance(token, str) or not token:
            # No token present (e.g. an error response); safe to pass through.
            return

        self._session_token = token
        self._session_stub_token = self._build_session_stub_token(token)
        self._session_api_host = self._api_host_from_session_token(token)
        body["token"] = self._session_stub_token
        self._persist_token()
        response.text = json.dumps(body)

    @staticmethod
    def _build_session_stub_token(token: str) -> str:
        proxy_endpoint = GitHubCopilotAuthInterceptor._proxy_endpoint_from_token(token)
        if proxy_endpoint is None:
            return STUB_SESSION_TOKEN

        return (
            "tid=STUB0000000000000000000000000000000000;"
            f"exp=4102444800;proxy-ep={proxy_endpoint};stub=1"
        )

    @staticmethod
    def _api_host_from_session_token(token: str) -> str | None:
        proxy_endpoint = GitHubCopilotAuthInterceptor._proxy_endpoint_from_token(token)
        if proxy_endpoint is None:
            return None
        return proxy_endpoint.replace("proxy.", "api.", 1)

    @staticmethod
    def _proxy_endpoint_from_token(token: str) -> str | None:
        for part in token.split(";"):
            if not part.startswith("proxy-ep="):
                continue
            proxy_endpoint = part.removeprefix("proxy-ep=").strip()
            if proxy_endpoint:
                return proxy_endpoint
        return None

    @staticmethod
    def _is_token_exchange_request(request: http.Request) -> bool:
        return (
            request.host == TOKEN_EXCHANGE_HOST
            and request.path.startswith(TOKEN_EXCHANGE_PATH_PREFIX)
        )

    def _persist_token(self) -> None:
        self._persist(
            {
                "access_token": self._access_token,
                "session_token": self._session_token,
            }
        )
