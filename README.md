# AI Buddy

`AI Buddy` is a Docker-based dev container setup that gives you a ready-to-use shell with AI CLIs installed.

Included tools:
- `claude`
- `opencode`
- `pi`
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
- `build` builds the agent and proxy images via `docker compose`.
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

Compose mounts `~/.gitconfig` from the host read-only into the container so Git commits use your existing author configuration. The file must exist before starting AI Buddy.

## Network Isolation & Proxy

The agent container is attached only to an internal Docker network (`agent-net`, subnet `100.100.0.0/24`) with no direct route to the internet. The `proxy` service is the only container attached to both that network and an externally routed network.

mitmproxy provides two listeners on its static IP `100.100.0.10`:

- TCP `8080` is the regular HTTP/HTTPS proxy selected through `HTTP_PROXY` and `HTTPS_PROXY`.
- TCP/UDP `53` is the DNS server selected through the container's DNS configuration.

TLS is intercepted so HTTP, HTTPS, and DNS traffic can be inspected with mitmproxy. The proxy does not currently restrict or modify requests or responses.

The proxy exports only its public CA certificate through a shared volume. The agent entrypoint installs that certificate into its system trust store before dropping privileges. Startup fails closed if the proxy or CA is not ready, and the CA private key remains in a proxy-only volume.

Applications which ignore the HTTP proxy variables still cannot connect directly to the internet because `agent-net` is internal. Their DNS traffic is sent through mitmproxy and is visible as DNS flows.

The proxy itself has unrestricted external connectivity. It can therefore reach public internet services as well as other destinations reachable from the Docker host's network.

Notes:
- Compose starts the proxy dependency automatically and waits for its healthcheck. The proxy keeps running after the agent session ends and is shared by parallel sessions.
- `/home/buddy` is persistent, including the agent CLI installations and their configuration. Rebuilding the image does not replace CLI files already present in an existing home volume.
- If the host UID or GID changes, recreate the `agent-home` volume or correct its numeric ownership.
- From the AI Buddy repository, stop it with `docker compose -f docker-compose.yml down`.
- From the AI Buddy repository, inspect traffic with `docker compose -f docker-compose.yml logs proxy`.

## Quick Reference

```bash
ai-buddy build   # build the image
ai-buddy start   # mount current directory into /workspace
```
