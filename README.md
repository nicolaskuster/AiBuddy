# AI Buddy

`AI Buddy` is a Docker-based dev container setup that gives you a ready-to-use shell with AI CLIs installed.

Included tools:
- `claude`
- `opencode`
- `.NET SDK`

The main entry point is the `ai-buddy` script.

## Requirements

- Docker must be installed and running.
- Docker Compose (v2, the `docker compose` command) must be available.
- You need to build the images once before starting the container.
- Copy `.env.example` to `.env` and fill in your `ANTHROPIC_API_KEY`. This is
  the only place a real secret lives - see
  [Security & network architecture](#security--network-architecture) below.

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
- `build` always uses this repository as the Docker build context.
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

## Persistent AI Config

The container mounts a Docker volume:

- `ai-buddy-shared:/home/buddy/.ai-buddy`

This keeps AI-related config files across container restarts.

Currently used for:
- Claude config
- OpenCode auth (see [Security & network architecture](#security--network-architecture) - this one is still a real secret today)

`ai-buddy start` mounts `~/.gitconfig` from the host read-only into the container so Git commits use your existing author configuration.

## Security & network architecture

The agent container holds **no real secrets** and has **no direct internet
access**. All network traffic is routed through a dedicated, long-running
`proxy` container:

```
agent (network: internal, no direct internet) ──▶ proxy ──▶ real internet
```

- `internal` is a Docker network with no route to the internet - the agent
  can only ever reach the `proxy` service on it.
- `proxy` is the only container attached to both `internal` and `egress`
  (which does have internet access). It's shared by every `ai-buddy start`
  instance, including several running in parallel for different projects.
- The proxy terminates TLS using its own, locally generated CA certificate.
  The agent trusts its **public** certificate only, shared read-only via the
  `ai-buddy-proxy-ca` volume - the CA's private key never leaves the proxy
  container.
- For a small set of known hosts (configured in `container/proxy/rules.yaml`),
  the proxy injects real secrets into outgoing requests. Those secrets live
  only in `.env`, which is only ever loaded into the `proxy` container
  (see `docker-compose.yml`'s `env_file`) - never into the agent.
- Every other destination is forwarded unmodified (default-allow). The proxy
  doesn't currently block or restrict destinations, it only ever *adds*
  headers for the hosts it's configured to handle. Request logging for
  everything else is planned as a follow-up.

Covered today:
- **Claude Code** (`api.anthropic.com`, API-key auth). The agent only ever
  sees a placeholder `ANTHROPIC_API_KEY` - the real key lives in `.env` and
  is injected by the proxy.

Known gap (tracked for a follow-up iteration):
- **OpenCode** (e.g. GitHub Copilot) still uses its real credentials from the
  `ai-buddy-shared` volume - its OAuth/token-refresh flow isn't covered by
  the proxy yet.

Useful commands:

```bash
docker compose logs -f proxy                          # see what's being requested/injected
docker compose up -d --force-recreate proxy           # pick up a changed .env
```

## Quick Reference

```bash
ai-buddy build   # build the agent + proxy images
ai-buddy start   # ensure the proxy is running, then mount current directory into /workspace
```
