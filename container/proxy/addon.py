"""AI Buddy egress proxy addon.

This addon turns mitmproxy into the only way out of the agent's isolated
Docker network:

- For every host configured in rules.yaml, the configured headers are
  injected/overwritten with secret values read from THIS process'
  environment (populated via docker-compose's `env_file: .env`). The agent
  container never holds these values.
- Every other host is forwarded completely unmodified (default-allow, see
  docker-compose.yml comments / README for the reasoning). Request logging
  (OTel) for these is planned as a follow-up, not part of this iteration.
- On startup, the public half of mitmproxy's CA certificate is exported to
  a volume that is (read-only) shared with agent containers, so they can
  trust it. The CA *private key* stays in the proxy's own, agent-inaccessible
  volume at all times.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import yaml
from mitmproxy import ctx, http

RULES_PATH = Path(os.environ.get("AI_BUDDY_RULES_PATH", "/config/rules.yaml"))

# Only the public certificate is ever copied out of here.
CA_CERT_SRC = Path("/home/mitmproxy/.mitmproxy/mitmproxy-ca-cert.pem")
CA_CERT_EXPORT_DIR = Path("/export-ca")
CA_CERT_EXPORT_NAME = "ai-buddy-ca.crt"


class SecretInjector:
    def __init__(self) -> None:
        self.rules: dict[str, dict] = {}

    def load(self, loader) -> None:
        self._load_rules()

    def running(self) -> None:
        # Called once mitmproxy is fully started, i.e. after it has
        # generated its CA (if this is the first run for this confdir).
        self._export_ca_cert()

    # -- setup -------------------------------------------------------------

    def _load_rules(self) -> None:
        if not RULES_PATH.exists():
            ctx.log.warn(f"[ai-buddy] no rules file at {RULES_PATH} - no secrets will be injected")
            self.rules = {}
            return

        data = yaml.safe_load(RULES_PATH.read_text()) or {}
        rules: dict[str, dict] = {}
        for entry in data.get("rules", []):
            host = entry["host"]
            rules[host] = {
                "set_headers": entry.get("set_headers", {}) or {},
                "strip_headers": entry.get("strip_headers", []) or [],
            }
        self.rules = rules
        ctx.log.info(
            f"[ai-buddy] loaded {len(self.rules)} injection rule(s) for: "
            f"{', '.join(self.rules) or '(none)'}"
        )

    def _export_ca_cert(self) -> None:
        if not CA_CERT_SRC.exists():
            ctx.log.warn(f"[ai-buddy] CA cert not found at {CA_CERT_SRC}, cannot export yet")
            return
        CA_CERT_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        dest = CA_CERT_EXPORT_DIR / CA_CERT_EXPORT_NAME
        shutil.copyfile(CA_CERT_SRC, dest)
        ctx.log.info(f"[ai-buddy] exported CA public certificate to {dest}")

    # -- request handling ----------------------------------------------------

    def request(self, flow: http.HTTPFlow) -> None:
        host = flow.request.pretty_host
        rule = self.rules.get(host)
        if rule is None:
            return  # default-allow: forward unmodified, no secrets involved

        for header in rule["strip_headers"]:
            if header in flow.request.headers:
                del flow.request.headers[header]

        injected = []
        for header, value_template in rule["set_headers"].items():
            value = os.path.expandvars(value_template)
            if "$" in value:
                ctx.log.warn(
                    f"[ai-buddy] header '{header}' for {host} references an "
                    "unset environment variable - not sending it. Check your .env file."
                )
                continue
            flow.request.headers[header] = value
            injected.append(header)

        if injected:
            ctx.log.info(
                f"[ai-buddy] {flow.request.method} {host}{flow.request.path} "
                f"-> injected: {', '.join(injected)}"
            )


addons = [SecretInjector()]
