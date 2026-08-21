#!/bin/bash
set -euo pipefail

# Runs as root so it can align the session user and update the system trust
# store, then drops to the non-root buddy user for the actual session (see
# docker-compose.yml and the Dockerfile for how the CA cert gets here).

# ── Align buddy with whoever owns the mounted workspace ─────────────────────
# Bind mounts pass numeric UIDs through untranslated, so the session user has to
# carry the host user's UID/GID or the agent cannot write to the mounted code.
# The image ships buddy as 1000:1000; adjusting it here keeps the image itself
# host-independent.
want_uid=$(stat -c %u /workspace 2>/dev/null || echo 1000)
want_gid=$(stat -c %g /workspace 2>/dev/null || echo 1000)

# No workspace mounted: /workspace is the image's root-owned WORKDIR, and root
# is not a UID to adopt.
if [ "$want_uid" = 0 ]; then
  want_uid=1000
  want_gid=1000
fi

have_uid=$(id -u buddy)
have_gid=$(id -g buddy)

# -o allows an ID that is already taken, e.g. when the host UID collides with a
# system user in here. groupmod runs first because it also fixes the primary
# group of matching /etc/passwd entries.
if [ "$want_gid" != "$have_gid" ]; then
  groupmod -o -g "$want_gid" buddy
fi
if [ "$want_uid" != "$have_uid" ]; then
  usermod -o -u "$want_uid" buddy
fi

# usermod migrates only files it already owns, and the group is never migrated
# automatically. /etc/passwd is container-local, so on a host with a UID other
# than 1000 this block runs on every start — hence the filter on entries that
# are actually stale, which makes repeat starts a read-only walk.
if [ "$want_uid" != "$have_uid" ] || [ "$want_gid" != "$have_gid" ]; then
  find /home/buddy \( ! -uid "$want_uid" -o ! -gid "$want_gid" \) -print0 \
    | xargs -0 --no-run-if-empty chown -h "$want_uid:$want_gid"
fi

# ── Trust the proxy CA ──────────────────────────────────────────────────────
CA_SRC=/run/ai-buddy-ca/ai-buddy-ca.crt
CA_DST=/usr/local/share/ca-certificates/ai-buddy-ca.crt

if [ ! -s "$CA_SRC" ]; then
  echo "error: ai-buddy proxy CA not found at $CA_SRC" >&2
  exit 1
fi

if ! cmp -s "$CA_SRC" "$CA_DST" 2>/dev/null; then
  cp "$CA_SRC" "$CA_DST"
  update-ca-certificates >/dev/null
fi

exec runuser -u buddy -- "$@"
