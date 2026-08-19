"""Keep real Claude Code OAuth tokens inside the proxy process."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

from mitmproxy import http

logger = logging.getLogger(__name__)

TOKEN_HOST = "platform.claude.com"
TOKEN_PATH = "/v1/oauth/token"
API_HOST = "api.anthropic.com"
TOKEN_STORE = Path("/home/mitmproxy/.mitmproxy-token/claude-code-tokens.json")

STUB_ACCESS_TOKEN = "sk-ant-oat01-STUB000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000-AA"
STUB_REFRESH_TOKEN = "sk-ant-ort01-STUB000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000-AA"


class ClaudeCodeAuthInterceptor:
    def __init__(self) -> None:
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    def load(self, loader) -> None:
        try:
            tokens = json.loads(TOKEN_STORE.read_text())
        except FileNotFoundError:
            return
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("[ai-buddy] could not read Claude Code token store: %s", exc)
            return

        if not isinstance(tokens, dict):
            logger.warning("[ai-buddy] Claude Code token store has an invalid format")
            return

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        if isinstance(access_token, str) and access_token:
            self._access_token = access_token
        if isinstance(refresh_token, str) and refresh_token:
            self._refresh_token = refresh_token

    def request(self, flow: http.HTTPFlow) -> None:
        if flow.request.pretty_host == API_HOST:
            self._replace_api_access_token(flow.request)
            return

        if not self._is_token_request(flow.request):
            return

        self._replace_refresh_token(flow.request)

    def response(self, flow: http.HTTPFlow) -> None:
        if (
            not self._is_token_request(flow.request)
            or flow.response is None
            or not flow.response.content
        ):
            return

        self._capture_and_replace_tokens(flow.response)

    @staticmethod
    def _is_token_request(request: http.Request) -> bool:
        return (
            request.pretty_host == TOKEN_HOST
            and request.path.split("?", 1)[0] == TOKEN_PATH
        )

    def _replace_api_access_token(self, request: http.Request) -> None:
        if (
            self._access_token
            and request.headers.get("authorization")
            == f"Bearer {STUB_ACCESS_TOKEN}"
        ):
            request.headers["authorization"] = f"Bearer {self._access_token}"

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

    def _capture_and_replace_tokens(self, response: http.Response) -> None:
        try:
            body = json.loads(response.get_text())
        except (TypeError, ValueError):
            return

        if not isinstance(body, dict):
            return

        access_token = body.get("access_token")
        if not isinstance(access_token, str) or not access_token:
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
        tokens = {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
        }
        temporary_store = TOKEN_STORE.with_suffix(".tmp")

        try:
            TOKEN_STORE.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(
                temporary_store,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                0o600,
            )
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w") as file:
                json.dump(tokens, file)
            temporary_store.replace(TOKEN_STORE)
        except OSError as exc:
            logger.warning("[ai-buddy] could not persist Claude Code tokens: %s", exc)
