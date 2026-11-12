# AI Buddy

`AI Buddy` is a Docker-based dev container setup that gives you a ready-to-use shell with AI CLIs installed.

Included tools:
- `claude`
- `opencode`
- `pi`
- `.NET SDK`
- `Node.js`
- Docker CLI with `buildx` and `compose` plugins, connected to an isolated rootless Docker engine

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
- `build` builds the agent image for your machine. Docker Compose pulls the latest stable rootless Docker engine image when needed.
- `start` always mounts your current directory into the container as `/workspace`.
- That means you can run `ai-buddy start` from any project directory.
- The setup supports one active AI Buddy session at a time. Concurrent starts are not blocked and would share the same Docker engine.

## Add It To Your PATH

If you want to use `ai-buddy` globally, symlink it into a directory that is already in your `PATH`.

Example using `~/.local/bin`:

```bash
ln -s ~/code/ai-buddy/ai-buddy ~/.local/bin/ai-buddy
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

## Image Build

The image is built on each machine and is not meant to be portable. `ai-buddy build` passes your numeric UID/GID (`id -u` / `id -g`) as build args, so the `buddy` user in the image matches your host user and files created in the bind-mounted workspace belong to you. If `ai-buddy start` has to build the image implicitly (no image yet), the defaults `1000:1000` are used — run `ai-buddy build` first.

The .NET SDK version is a build arg as well, set in `docker-compose.yml` (`DOTNET_VERSION`, currently `11.0`; the newest SDK of that version is installed). Node.js comes in version 24 from NodeSource, the base image is `debian:trixie-slim`.

## Persistence

The CLIs and `/home/buddy` are part of the image, so `ai-buddy build` delivers CLI updates and anything else written to `$HOME` is discarded when the session ends.

Configuration, credentials, session history and caches live in the named volume `agent-state`, mounted at `/state`. The tools are pointed there via environment variables in `docker-compose.yml`:

| Variable | Path |
| --- | --- |
| `XDG_CONFIG_HOME` | `/state/config` |
| `XDG_DATA_HOME` | `/state/data` |
| `XDG_STATE_HOME` | `/state/state` |
| `XDG_CACHE_HOME` | `/state/cache` |
| `CLAUDE_CONFIG_DIR` | `/state/claude` |
| `PI_CODING_AGENT_DIR` | `/state/pi/agent` |
| `PI_CODING_AGENT_SESSION_DIR` | `/state/pi/sessions` |

Tools that ignore these variables and write directly to `$HOME` (e.g. `~/.gitconfig`, `~/.nuget/packages`, shell history) are not persisted.

## Docker & Testcontainers

`ai-buddy start` starts the latest stable `docker:dind-rootless` sidecar. The daemon listens only on a Unix socket, which it places in the shared `docker-socket` volume; the agent reaches it via `DOCKER_HOST=unix:///docker-socket/docker.sock`. There is no TCP API, nothing is published on the host, and the host Docker socket is never mounted. The rootlesskit runtime directory stays inside the sidecar — only the socket is shared.

The `docker-socket` volume is a 16 MB tmpfs owned by the rootless daemon user (`1000:1000`, mode `0750`). The agent joins group `1000` (`group_add`), so the socket is usable even if your host UID is not 1000. Note that `driver_opts` only take effect when the volume is created; after changing them, remove it with `docker volume rm ai-buddy_docker-socket`.

The engine is rootless internally, but Docker currently requires its outer sidecar container to run with `privileged: true`. This is a materially safer boundary than giving the agent the host Docker socket: agent code controls only the nested engine, which has no host paths or agent state mounted into it. It is not equivalent to VM isolation against malicious code that can exploit the kernel.

The Docker engine data is persisted in the `docker-data` volume, so subsequent sessions can reuse pulled images. Because the fixed Compose project supports only one active session, concurrent agents would share and could modify each other's Docker resources.

`docker compose` and `docker buildx` are available in the agent and talk to the same nested engine. Bind mounts are resolved by the daemon, i.e. inside the `docker-engine` container, where `/workspace` does not exist — bind mounts from `/workspace` in `volumes:` will not contain your files. Use named volumes or `COPY` in a build instead; build contexts work normally because the CLI uploads them.

Testcontainers needs two extra variables, both preset:

- `TESTCONTAINERS_HOST_OVERRIDE=docker-engine` — published ports of test containers are bound inside the `docker-engine` container, not on the agent's `localhost`.
- `TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE=/docker-socket/docker.sock` — the socket path as seen by the daemon. Ryuk bind-mounts it from there to clean up resources after each test run.

### Security Boundaries

The container boundary protects the host and the host network. It does not protect the credentials inside the container. Egress is unrestricted and the CLI credentials sit in the shared `agent-state` volume, readable by every session in every project. Everything running in the container can therefore reach those credentials and send them anywhere. Treat every credential the container can see as exposed to whatever the agents run.

- **The host Docker socket is deliberately not mounted.** The agent can control only the rootless DinD engine. Since the sidecar is privileged, this improves isolation but is not a hard VM-like security boundary.
- **Network access is unrestricted.** The agent and nested Docker engine can connect directly to destinations reachable from the Docker host.

Notes:
- Compose starts the Docker dependency automatically and waits for its healthcheck. Containers are stopped when the agent exits; named volumes remain available for the next session.
- Agent CLI credentials are shared globally by all agent sessions through the `agent-state` volume. Logging into the same CLI from two parallel sessions can overwrite the other session's state.
- Git is installed but not configured: there is no identity and no credential helper. Since `~/.gitconfig` is not persisted, configure Git via `$XDG_CONFIG_HOME/git/config` (`/state/config/git/config`) if it should survive the session.

## Quick Reference

```bash
ai-buddy build   # build the image
ai-buddy start   # mount current directory into /workspace
```
