FROM mitmproxy/mitmproxy:12

COPY addon.py /addons/addon.py
COPY claude_code_auth.py /addons/claude_code_auth.py
COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["mitmdump", "--mode", "regular@0.0.0.0:8080", "--mode", "dns@0.0.0.0:53", "-s", "/addons/addon.py"]
