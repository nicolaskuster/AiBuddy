FROM mitmproxy/mitmproxy:12.2.3

# Only our addon and its (currently minimal) Python dependencies are added
# on top of the upstream image. Everything else - the non-root `mitmproxy`
# user, the `gosu`-based privilege drop, CA generation - is inherited as-is
# from upstream's Dockerfile/entrypoint.
COPY container/proxy/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY container/proxy/addon.py /addons/addon.py
COPY container/proxy/rules.yaml /config/rules.yaml
