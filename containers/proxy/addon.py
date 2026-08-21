"""Export mitmproxy's public CA certificate for the agent container."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import github_oauth
from claude_code_auth import ClaudeCodeAuthInterceptor
from github_cli_auth import GitHubCliAuthInterceptor
from github_cli_auth import GH_CLI_CLIENT_ID
from github_cli_auth import STUB_ACCESS_TOKEN as GH_CLI_STUB_ACCESS_TOKEN
from github_copilot_auth import COPILOT_CLIENT_IDS
from github_copilot_auth import GitHubCopilotAuthInterceptor
from github_copilot_auth import STUB_ACCESS_TOKEN as COPILOT_STUB_ACCESS_TOKEN

logger = logging.getLogger(__name__)

MITM_CA_CERT = Path("/home/mitmproxy/.mitmproxy/mitmproxy-ca-cert.pem")
PUBLIC_CA_DIR = Path("/home/mitmproxy/.mitmproxy-public")
PUBLIC_CA_DEST = PUBLIC_CA_DIR / "ai-buddy-ca.crt"


def _read_ca_cert() -> bytes | None:
    try:
        return MITM_CA_CERT.read_bytes()
    except OSError:
        return None


class PublicCaExporter:
    def __init__(self) -> None:
        self._export_task: asyncio.Task[None] | None = None

    def running(self) -> None:
        self._export_task = asyncio.create_task(self._export_when_ready())

    async def _export_when_ready(self) -> None:
        cert = None
        for _ in range(30):
            cert = _read_ca_cert()
            if cert is not None:
                break
            await asyncio.sleep(0.5)

        if cert is None:
            logger.warning("[ai-buddy] could not read generated CA certificate")
            return

        self._export(cert)

    def _export(self, cert: bytes) -> None:
        try:
            if PUBLIC_CA_DEST.exists() and PUBLIC_CA_DEST.read_bytes() == cert:
                return
            PUBLIC_CA_DIR.mkdir(parents=True, exist_ok=True)
            temporary_dest = PUBLIC_CA_DEST.with_suffix(".tmp")
            temporary_dest.write_bytes(cert)
            temporary_dest.replace(PUBLIC_CA_DEST)
        except OSError as exc:
            logger.warning("[ai-buddy] could not export public CA certificate: %s", exc)
            return

        logger.info("[ai-buddy] exported public CA certificate to %s", PUBLIC_CA_DEST)

    def done(self) -> None:
        if self._export_task is not None:
            self._export_task.cancel()


github_copilot = GitHubCopilotAuthInterceptor()
github_cli = GitHubCliAuthInterceptor()

github_oauth_clients = {
    GH_CLI_CLIENT_ID: github_oauth.GitHubOAuthClient(
        label="GitHub CLI",
        stub_access_token=GH_CLI_STUB_ACCESS_TOKEN,
        accept_access_token=github_cli.set_access_token,
    ),
}

for client_id in COPILOT_CLIENT_IDS:
    github_oauth_clients[client_id] = github_oauth.GitHubOAuthClient(
        label="GitHub Copilot",
        stub_access_token=COPILOT_STUB_ACCESS_TOKEN,
        accept_access_token=github_copilot.set_access_token,
    )

addons = [
    PublicCaExporter(),
    ClaudeCodeAuthInterceptor(),
    github_copilot,
    github_cli,
    github_oauth.GitHubOAuthCapture(github_oauth_clients),
]
