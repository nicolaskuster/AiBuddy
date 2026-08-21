FROM mitmproxy/mitmproxy:12

COPY addon.py /addons/addon.py
COPY token_store.py /addons/token_store.py
COPY github_oauth.py /addons/github_oauth.py
COPY claude_code_auth.py /addons/claude_code_auth.py
COPY github_copilot_auth.py /addons/github_copilot_auth.py
COPY github_cli_auth.py /addons/github_cli_auth.py
COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["mitmdump", "--mode", "regular@0.0.0.0:8080", "--mode", "dns@0.0.0.0:53", "-s", "/addons/addon.py"]
