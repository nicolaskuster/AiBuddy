# AI Buddy

`AI Buddy` is a Docker-based dev container setup that gives you a ready-to-use shell with AI CLIs installed.

Included tools:
- `claude`
- `opencode`
- `.NET SDK`

The main entry point is the `ai-buddy` script.

## Requirements

- Docker must be installed and running.
- You need to build the image once before starting the container.

## Usage

Build the image:

```bash
./ai-buddy build
```

Start the container in your current directory:

```bash
./ai-buddy start
```

Important:
- `build` builds the `agent` image via `docker compose` using `containers/Agent/` as the Docker build context.
- `start` always mounts your current directory into the container as `/workspace`.
- That means you can run `ai-buddy start` from any project directory.

## Add It To Your PATH

If you want to use `ai-buddy` globally, symlink it into a directory that is already in your `PATH`.

Example using `~/.local/bin`:

```bash
ln -s /workspace/ai-buddy ~/.local/bin/ai-buddy
```

If `~/.local/bin` is not in your `PATH` yet, add it in your shell configuration.

After that, you can use it from anywhere:

```bash
ai-buddy build
ai-buddy start
```

Typical workflow inside a project directory:

```bash
cd ~/code/my-project
ai-buddy start
```

Your project directory will then be available inside the container at `/workspace`.

## Git Config

`ai-buddy start` mounts `~/.gitconfig` from the host read-only into the container so Git commits use your existing author configuration.

## Network Isolation & Proxy

The agent container is attached to an internal Docker network (`agent-net`, subnet `100.100.0.0/24`) with no direct route to the internet. All outbound traffic goes through the `proxy` service, a [mitmproxy](https://mitmproxy.org/) container reachable at the static IP `100.100.0.10:8080` (set via `HTTP_PROXY`/`HTTPS_PROXY` in the agent).

Currently the proxy runs as a pure passthrough tunnel (`--ignore-hosts '.*'`) — TLS is not intercepted, so no CA setup is needed inside the agent. This is the place where token injection and request logging/tracing will be added later (requires enabling TLS interception and trusting the mitmproxy CA in the agent).

Notes:
- `ai-buddy start` starts the proxy automatically (compose dependency). The proxy keeps running after the agent session ends and is shared by parallel sessions.
- Stop it with `docker compose -f docker-compose.yml down`.
- Inspect proxied traffic with `docker compose -f docker-compose.yml logs proxy`.

## Quick Reference

```bash
ai-buddy build   # build the image
ai-buddy start   # mount current directory into /workspace
```
