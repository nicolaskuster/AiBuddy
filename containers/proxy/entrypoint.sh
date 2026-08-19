#!/bin/sh
set -eu

owner=$(stat -c '%u:%g' /home/mitmproxy/.mitmproxy)
chown "$owner" /home/mitmproxy/.mitmproxy-public /home/mitmproxy/.mitmproxy-token

exec docker-entrypoint.sh "$@"
