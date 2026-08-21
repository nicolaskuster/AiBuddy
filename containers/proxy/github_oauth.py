"""Shared handling for GitHub's OAuth device-flow token-exchange endpoint.

``github.com/login/oauth/access_token`` is shared by every GitHub OAuth app
(GitHub Copilot, GitHub CLI, ...). This addon captures token responses once,
routes them by the request's client_id, and only returns stubs to the agent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable
from urllib.parse import parse_qsl, urlencode

from mitmproxy import http

TOKEN_HOST = "github.com"
TOKEN_PATH = "/login/oauth/access_token"


@dataclass(frozen=True)
class GitHubOAuthClient:
    label: str
    stub_access_token: str
    accept_access_token: Callable[[str], None]


class GitHubOAuthCapture:
    """Capture known GitHub OAuth tokens and block unknown token leaks."""

    def __init__(self, clients: dict[str, GitHubOAuthClient]) -> None:
        self._clients = clients

    def response(self, flow: http.HTTPFlow) -> None:
        if flow.response is None or not is_token_endpoint(flow.request):
            return

        access_token = access_token_of(flow.response)
        if access_token is None:
            if not token_response_is_safely_understood(flow.response):
                _block(flow.response, "GitHub OAuth token response could not be sanitized")
            return

        client_id = client_id_of(flow.request)
        client = self._clients.get(client_id) if client_id is not None else None
        if client is None:
            _block(flow.response, "unknown GitHub OAuth client_id; token response blocked")
            return

        if not replace_access_token(flow.response, client.stub_access_token):
            _block(flow.response, "GitHub OAuth token response could not be sanitized")
            return

        client.accept_access_token(access_token)


def client_id_of(request: http.Request) -> str | None:
    """Best-effort read of the ``client_id`` field from a request body.

    Used to disambiguate OAuth apps sharing GitHub's generic
    ``/login/oauth/access_token`` endpoint by the app that issued the
    request, not by response shape.
    """
    if not request.content:
        return None

    content_type = request.headers.get("content-type", "").lower()
    if "application/x-www-form-urlencoded" in content_type:
        fields = parse_qsl(request.get_text(), keep_blank_values=True)
        return next((value for key, value in fields if key == "client_id" and value), None)

    if "json" in content_type:
        try:
            body = json.loads(request.get_text())
        except (TypeError, ValueError):
            return None
        if isinstance(body, dict):
            value = body.get("client_id")
            return value if isinstance(value, str) and value else None

    return None


def is_token_endpoint(request: http.Request) -> bool:
    return request.host == TOKEN_HOST and request.path.split("?", 1)[0] == TOKEN_PATH


def access_token_of(response: http.Response) -> str | None:
    if not response.content:
        return None

    content_type = response.headers.get("content-type", "").lower()
    if "json" in content_type:
        try:
            body = json.loads(response.get_text())
        except (TypeError, ValueError):
            return None
        if isinstance(body, dict):
            access_token = body.get("access_token")
            return access_token if isinstance(access_token, str) and access_token else None

    if "application/x-www-form-urlencoded" in content_type:
        fields = parse_qsl(response.get_text(), keep_blank_values=True)
        return next((value for key, value in fields if key == "access_token" and value), None)

    return None


def token_response_is_safely_understood(response: http.Response) -> bool:
    if not response.content:
        return True

    content_type = response.headers.get("content-type", "").lower()
    if "json" in content_type:
        try:
            return isinstance(json.loads(response.get_text()), dict)
        except (TypeError, ValueError):
            return False

    if "application/x-www-form-urlencoded" in content_type:
        parse_qsl(response.get_text(), keep_blank_values=True)
        return True

    return False


def replace_access_token(response: http.Response, stub: str) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    if "json" in content_type:
        try:
            body = json.loads(response.get_text())
        except (TypeError, ValueError):
            return False
        if not isinstance(body, dict):
            return False
        if isinstance(body.get("access_token"), str):
            body["access_token"] = stub
            response.text = json.dumps(body)
        return True

    if "application/x-www-form-urlencoded" in content_type:
        fields = parse_qsl(response.get_text(), keep_blank_values=True)
        response.text = urlencode(
            [(key, stub if key == "access_token" else value) for key, value in fields]
        )
        return True

    return False


def _block(response: http.Response, message: str) -> None:
    response.status_code = 502
    for header in ("set-cookie", "www-authenticate", "authorization"):
        response.headers.pop(header, None)
    response.headers["content-type"] = "text/plain"
    response.text = f"ai-buddy: {message}"
