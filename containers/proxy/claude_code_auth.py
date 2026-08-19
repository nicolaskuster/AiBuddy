"""Keep real Claude Code OAuth tokens inside the proxy process.

The agent only ever holds stub tokens. Real tokens live here and are injected
only into requests whose *actual upstream host* (``request.host``, not the
spoofable ``pretty_host``) is the Anthropic API or the OAuth token endpoint.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

from mitmproxy import http

from token_store import OAuthBrokerAddon

logger = logging.getLogger(__name__)

TOKEN_HOST = "platform.claude.com"
TOKEN_PATH = "/v1/oauth/token"
API_HOST = "api.anthropic.com"
TOKEN_STORE = Path("/home/mitmproxy/.mitmproxy-token/claude-code-tokens.json")

STUB_ACCESS_TOKEN = "sk-ant-oat01-STUB000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000-AA"
STUB_REFRESH_TOKEN = "sk-ant-ort01-STUB000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000-AA"


class ClaudeCodeAuthInterceptor(OAuthBrokerAddon):
    label = "Claude Code"
    store_path = TOKEN_STORE

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    def _apply_stored_tokens(self, tokens: dict) -> None:
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        if isinstance(access_token, str) and access_token:
            self._access_token = access_token
        if isinstance(refresh_token, str) and refresh_token:
            self._refresh_token = refresh_token

    def request(self, flow: http.HTTPFlow) -> None:
        if flow.request.host == API_HOST:
            self._broker_api_request(flow)
            return

        if not self._is_token_request(flow.request):
            return

        self._replace_refresh_token(flow.request)

    def response(self, flow: http.HTTPFlow) -> None:
        if not self._is_token_request(flow.request) or flow.response is None:
            return

        self._sanitize_token_response(flow.response)

    @staticmethod
    def _is_token_request(request: http.Request) -> bool:
        # Gate on the real upstream host, never the spoofable Host header.
        return (
            request.host == TOKEN_HOST
            and request.path.split("?", 1)[0] == TOKEN_PATH
        )

    def _broker_api_request(self, flow: http.HTTPFlow) -> None:
        authorization = flow.request.headers.get("authorization")
        if authorization is None:
            # Nothing brokered here (e.g. an x-api-key request); leave it alone.
            return

        if authorization != f"Bearer {STUB_ACCESS_TOKEN}":
            # Fail-closed: on the Anthropic API host the agent must only ever
            # carry the stub. Any other bearer is anomalous and rejected so a
            # real token cannot be smuggled back out through this path.
            flow.response = self._reject(
                "ai-buddy: unexpected credential on Anthropic API host; "
                "only stub tokens are allowed"
            )
            return

        if not self._access_token:
            flow.response = self._reject(
                "Claude Code OAuth token mapping is not available; re-login required"
            )
            return

        flow.request.headers["authorization"] = f"Bearer {self._access_token}"

    def _replace_refresh_token(self, request: http.Request) -> None:
        if not self._refresh_token or not request.content:
            return

        content_type = request.headers.get("content-type", "").lower()
        if "json" in content_type:
            self._replace_json_refresh_token(request)
        elif "application/x-www-form-urlencoded" in content_type:
            self._replace_form_refresh_token(request)

    def _replace_json_refresh_token(self, request: http.Request) -> None:
        try:
            body = json.loads(request.get_text())
        except (TypeError, ValueError):
            return

        if not isinstance(body, dict) or body.get("refresh_token") != STUB_REFRESH_TOKEN:
            return

        body["refresh_token"] = self._refresh_token
        request.text = json.dumps(body)

    def _replace_form_refresh_token(self, request: http.Request) -> None:
        fields = parse_qsl(request.get_text(), keep_blank_values=True)
        if not any(
            key == "refresh_token" and value == STUB_REFRESH_TOKEN
            for key, value in fields
        ):
            return

        request.text = urlencode(
            [
                (key, self._refresh_token if key == "refresh_token" else value)
                for key, value in fields
            ]
        )

    def _sanitize_token_response(self, response: http.Response) -> None:
        if not response.content:
            return

        body = self._parse_json_object(response)
        if body is None:
            # The OAuth token endpoint answers with JSON. Anything else could be
            # carrying the real token in a shape we do not stub, so never forward
            # it to the agent.
            self._block(response, "token response could not be sanitized; blocked")
            return

        access_token = body.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            # No token present (e.g. an error response); safe to pass through.
            return

        self._access_token = access_token
        body["access_token"] = STUB_ACCESS_TOKEN

        refresh_token = body.get("refresh_token")
        if isinstance(refresh_token, str) and refresh_token:
            self._refresh_token = refresh_token
            body["refresh_token"] = STUB_REFRESH_TOKEN

        self._persist_tokens()
        response.text = json.dumps(body)

    def _persist_tokens(self) -> None:
        self._persist(
            {
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
            }
        )
