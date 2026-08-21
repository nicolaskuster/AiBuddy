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

The container adapts to whoever owns that directory: the image ships its `buddy` user as UID 1000, and the entrypoint moves it to the owner of the mounted `/workspace` at startup. Files the agent creates therefore belong to you on the host, whatever your UID is, and the same image works on any host.

## Private NuGet Feed (GitHub Packages)

There is no setup step inside the container. The feed itself is declared in your project's own `NuGet.config`, and the credentials are injected for the lifetime of the session: `start_buddy.sh` runs `gh auth token` on the host and hands the result to `docker compose run` as

```
-e NuGetPackageSourceCredentials_galaxus_github=Username=ai-buddy;Password=<token>
```

The GitHub CLI therefore only has to be installed and logged in on your machine — it is deliberately not part of the image. The token exists only in that container's environment: it is never written to a volume, never stored in a `NuGet.config`, and gone when the session ends.

Three things here are easy to get wrong:

- The suffix after `NuGetPackageSourceCredentials_` must exactly match the `key` of the source in your project's `NuGet.config`. NuGet looks up credentials by source name, so a mismatch means they are silently ignored and restore fails with a 401.
- It must be `Password=`, not `ClearTextPassword=`. In this variable the value is used as-is; `ClearTextPassword=` is only recognised inside a `NuGet.config` file and is silently ignored here — again a 401.
- If you are not logged in to `gh` on the host, the password is simply empty and restore fails with a 401 that says nothing about the real cause. Check with `gh auth status` when a restore starts failing out of nowhere.

To point at a different feed, change the source in your project's `NuGet.config` and rename the variable in `scripts/start_buddy.sh` to match.

## Network Isolation & Proxy

The agent container is attached only to an internal Docker network (`agent-net`, subnet `100.100.0.0/24`) with no direct route to the internet. The `proxy` service is the only container attached to both that network and an externally routed network.

mitmproxy provides two listeners on its static IP `100.100.0.10`:

- TCP `8080` is the regular HTTP/HTTPS proxy selected through `HTTP_PROXY` and `HTTPS_PROXY`.
- TCP/UDP `53` is the DNS server selected through the container's DNS configuration.

TLS is intercepted, but the proxy is currently a plain passthrough: it does not stub, capture, or block anything, and all traffic (including the real Claude Code OAuth tokens) is forwarded unmodified. Nothing is persisted either — the only view of the traffic today is `docker compose logs proxy`, which is unstructured and rotates with Docker's default log settings. Real credentials live directly in the agent container's own CLI config files, persisted in the `agent-home` volume, the same way they would without a proxy in front of them.

TLS interception is kept in place as groundwork for a separate, future step that adds a collector for traffic metrics (request host/method/status/duration).

The proxy exports only its public CA certificate through a shared volume. The agent entrypoint installs that certificate into its system trust store before dropping privileges. Startup fails closed if the proxy or CA is not ready, and the CA private key remains in a proxy-only volume.

Applications which ignore the HTTP proxy variables still cannot connect directly to the internet because `agent-net` is internal. Their DNS traffic is sent through mitmproxy and is visible as DNS flows.

The proxy itself has unrestricted external connectivity. It can therefore reach public internet services as well as other destinations reachable from the Docker host's network.

### What the isolation does and does not cover

The container boundary protects the host and the host network. It does not protect the credentials inside the container. Egress is unrestricted, the Claude Code tokens sit in the shared `agent-home` volume readable by every session in every project, and the NuGet feed token is in the process environment where anything can read it out of `/proc`. Everything running in the container can therefore reach those tokens and send them anywhere. Closing that gap is what the future egress policy step is for; until then, treat every credential the container can see as exposed to whatever the agents run.

Passing the NuGet token through the container environment is not a security boundary — it only keeps the credential out of the persistent volume, so it goes away with the session and is re-supplied from your host login on the next start. Note also that it is passed on the `docker compose` command line, so it is visible in `/proc/<pid>/cmdline` to any local user on the host for as long as the session runs.

Further boundaries worth knowing:

- **Git over SSH does not work, by design.** `agent-net` is internal and SSH cannot use an HTTP proxy, so SSH remotes have no route out. Use HTTPS remotes.
- **The Docker socket is deliberately not mounted.** There is no Docker-in-Docker; an agent cannot start sibling containers or escape through the daemon.
- **Build traffic does not go through the proxy.** `docker build` uses the host network, and the CA does not even exist at that point. "All traffic goes through the proxy" holds at runtime, not at image build time.

Notes:
- Compose starts the proxy dependency automatically and waits for its healthcheck. The proxy keeps running after the agent session ends and is shared by parallel sessions.
- Agent CLI credentials are shared globally by all agent sessions through the persistent `agent-home` volume. Logging into the same CLI from two parallel sessions can overwrite the other session's state.
- Tools and configuration are split: the CLIs are installed in the image under `/opt/ai-buddy`, while `/home/buddy` is a persistent volume holding configuration, credentials, session history, and plans. `ai-buddy build` therefore delivers CLI updates without touching your logins. On a host whose UID is not 1000, `/opt/ai-buddy` is not writable for the session, so CLIs cannot update themselves in place — updates come from `ai-buddy build`.
- Git is installed but not configured: there is no identity, so `git commit` fails until you set one, and there is no credential helper, so pushing needs credentials you supply yourself. Reading history (`log`, `diff`, `status`, `fetch` over HTTPS) works out of the box. Both are one-time `git config --global` fixes that land in the persistent volume.
- From the AI Buddy repository, stop it with `docker compose -f docker-compose.yml down`.
- From the AI Buddy repository, inspect traffic with `docker compose -f docker-compose.yml logs proxy`.

## Quick Reference

```bash
ai-buddy build   # build the image
ai-buddy start   # mount current directory into /workspace
```
