"""Keep real GitHub Copilot OAuth tokens inside the proxy process."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

from mitmproxy import http

logger = logging.getLogger(__name__)

TOKEN_HOST = "github.com"
TOKEN_PATH = "/login/oauth/access_token"
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


class GitHubCopilotAuthInterceptor:
    def __init__(self) -> None:
        self._access_token: str | None = None
        self._session_token: str | None = None
        self._session_stub_token = STUB_SESSION_TOKEN
        self._session_api_host: str | None = None

    def load(self, loader) -> None:
        try:
            tokens = json.loads(TOKEN_STORE.read_text())
        except FileNotFoundError:
            return
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("[ai-buddy] could not read GitHub Copilot token store: %s", exc)
            return

        if not isinstance(tokens, dict):
            logger.warning("[ai-buddy] GitHub Copilot token store has an invalid format")
            return

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
            if self._access_token:
                flow.request.headers["authorization"] = f"Bearer {self._access_token}"
                return

            flow.response = http.Response.make(
                401,
                b"GitHub Copilot OAuth token mapping is not available; re-login required",
                {"content-type": "text/plain"},
            )
            return

        if authorization == f"Bearer {self._session_stub_token}":
            if self._session_token:
                flow.request.headers["authorization"] = f"Bearer {self._session_token}"
                return

            flow.response = http.Response.make(
                401,
                b"GitHub Copilot session token mapping is not available; re-login required",
                {"content-type": "text/plain"},
            )

    def _is_authorized_host(self, request: http.Request) -> bool:
        if request.pretty_host in API_HOSTS:
            return True

        if self._session_api_host and request.pretty_host == self._session_api_host:
            return True

        return (
            request.pretty_host == TOKEN_EXCHANGE_HOST
            and request.path.startswith(TOKEN_EXCHANGE_PATH_PREFIX)
        )

    def response(self, flow: http.HTTPFlow) -> None:
        if flow.response is None or not flow.response.content:
            return

        if self._is_token_request(flow.request):
            self._capture_oauth_token(flow.response)
        elif self._is_token_exchange_request(flow.request):
            self._capture_session_token(flow.response)

    def _capture_oauth_token(self, response: http.Response) -> None:
        content_type = response.headers.get("content-type", "").lower()
        if "json" in content_type:
            self._capture_json_oauth_token(response)
        elif "application/x-www-form-urlencoded" in content_type:
            self._capture_form_oauth_token(response)

    def _capture_json_oauth_token(self, response: http.Response) -> None:
        body = self._parse_json_object(response)
        if body is None:
            return

        access_token = body.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            return

        self._access_token = access_token
        body["access_token"] = STUB_ACCESS_TOKEN
        self._persist_token()
        response.text = json.dumps(body)

    def _capture_form_oauth_token(self, response: http.Response) -> None:
        fields = parse_qsl(response.get_text(), keep_blank_values=True)
        access_token = next(
            (value for key, value in fields if key == "access_token" and value),
            None,
        )
        if access_token is None:
            return

        self._access_token = access_token
        self._persist_token()
        response.text = urlencode(
            [
                (key, STUB_ACCESS_TOKEN if key == "access_token" else value)
                for key, value in fields
            ]
        )

    def _capture_session_token(self, response: http.Response) -> None:
        body = self._parse_json_object(response)
        if body is None:
            return

        token = body.get("token")
        if not isinstance(token, str) or not token:
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
    def _parse_json_object(response: http.Response) -> dict | None:
        try:
            body = json.loads(response.get_text())
        except (TypeError, ValueError):
            return None
        return body if isinstance(body, dict) else None

    @staticmethod
    def _is_token_exchange_request(request: http.Request) -> bool:
        return (
            request.pretty_host == TOKEN_EXCHANGE_HOST
            and request.path.startswith(TOKEN_EXCHANGE_PATH_PREFIX)
        )

    @staticmethod
    def _is_token_request(request: http.Request) -> bool:
        return (
            request.pretty_host == TOKEN_HOST
            and request.path.split("?", 1)[0] == TOKEN_PATH
        )

    def _persist_token(self) -> None:
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
                json.dump(
                    {
                        "access_token": self._access_token,
                        "session_token": self._session_token,
                    },
                    file,
                )
            temporary_store.replace(TOKEN_STORE)
        except OSError as exc:
            logger.warning("[ai-buddy] could not persist GitHub Copilot token: %s", exc)
