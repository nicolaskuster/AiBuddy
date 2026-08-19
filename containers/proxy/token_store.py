"""Shared machinery for the OAuth credential brokers.

Centralises the two things both broker addons must get right:

* atomic, owner-only (``0o600``) persistence of the captured real tokens, and
* the fail-closed helpers that make sure a real token never reaches the agent.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from mitmproxy import http

logger = logging.getLogger(__name__)


def load_token_store(path: Path, label: str) -> dict:
    """Read a token store, returning an empty mapping on any problem."""
    try:
        raw = path.read_text()
    except FileNotFoundError:
        return {}
    except OSError as exc:
        logger.warning("[ai-buddy] could not read %s token store: %s", label, exc)
        return {}

    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("[ai-buddy] %s token store has an invalid format", label)
        return {}

    if not isinstance(data, dict):
        logger.warning("[ai-buddy] %s token store has an invalid format", label)
        return {}

    return data


def persist_token_store(path: Path, tokens: dict, label: str) -> None:
    """Atomically write ``tokens`` to ``path`` with ``0o600`` permissions."""
    temporary = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w") as file:
            json.dump(tokens, file)
        temporary.replace(path)
    except OSError as exc:
        logger.warning("[ai-buddy] could not persist %s tokens: %s", label, exc)


class OAuthBrokerAddon:
    """Base for addons that swap real OAuth tokens for stubs and back.

    Subclasses set ``label`` and ``store_path`` and implement
    :meth:`_apply_stored_tokens`; they call :meth:`_persist` to save state.
    """

    label: str = "oauth"
    store_path: Path

    def load(self, loader) -> None:  # noqa: ARG002 - mitmproxy hook signature
        self._apply_stored_tokens(load_token_store(self.store_path, self.label))

    def _apply_stored_tokens(self, tokens: dict) -> None:
        raise NotImplementedError

    def _persist(self, tokens: dict) -> None:
        persist_token_store(self.store_path, tokens, self.label)

    @staticmethod
    def _parse_json_object(message: http.Message) -> dict | None:
        try:
            body = json.loads(message.get_text())
        except (TypeError, ValueError):
            return None
        return body if isinstance(body, dict) else None

    @staticmethod
    def _reject(message: str) -> http.Response:
        """Build a fail-closed 401 response for the agent."""
        return http.Response.make(
            401,
            message.encode(),
            {"content-type": "text/plain"},
        )

    @staticmethod
    def _block(response: http.Response, message: str) -> None:
        """Replace a response in place so no real token can leak through it."""
        response.status_code = 502
        for header in ("set-cookie", "www-authenticate", "authorization"):
            response.headers.pop(header, None)
        response.headers["content-type"] = "text/plain"
        response.text = f"ai-buddy: {message}"
