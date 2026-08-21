# AI Buddy

`AI Buddy` is a Docker-based dev container setup that gives you a ready-to-use shell with AI CLIs installed.

Included tools:
- `claude`
- `opencode`
- `pi`
- `.NET SDK`
- Docker CLI connected to an isolated rootless Docker engine

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
- `build` builds the agent image. Docker Compose pulls the latest stable rootless Docker engine image when needed.
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

`start_buddy.sh` passes your numeric UID/GID to Compose, so the agent process owns files it creates in the bind-mounted workspace. Before the agent starts, a short-lived `init-home` service aligns the persistent `/home/buddy` volume with the same IDs. The agent itself starts directly as that unprivileged user and never needs root or additional capabilities.

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

## Docker & Testcontainers

`ai-buddy start` starts the latest stable `docker:dind-rootless` sidecar. The Docker CLI and Testcontainers clients in the agent connect to it through `tcp://docker-engine:2375` on the private Compose network. The API is not published on the host, and the host Docker socket is never mounted.

The engine is rootless internally, but Docker currently requires its outer sidecar container to run with `privileged: true`. This is a materially safer boundary than giving the agent the host Docker socket: agent code controls only the nested engine, which has no host paths, agent credentials, or agent home mounted into it. It is not equivalent to VM isolation against malicious code that can exploit the kernel.

The Docker engine data is persisted in a named volume, so subsequent sessions can reuse pulled images. Because the fixed Compose project supports only one active session, concurrent agents would share and could modify each other's Docker resources.

Testcontainers for .NET reads the preconfigured `DOCKER_HOST` and host override automatically. Ryuk remains enabled and receives the rootless daemon socket path through `TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE`, allowing it to clean resources after individual test runs during a long-lived agent session.

### Security Boundaries

The container boundary protects the host and the host network. It does not protect the credentials inside the container. Egress is unrestricted, the Claude Code tokens sit in the shared `agent-home` volume readable by every session in every project, and the NuGet feed token is in the process environment where anything can read it out of `/proc`. Everything running in the container can therefore reach those tokens and send them anywhere. Closing that gap is what the future egress policy step is for; until then, treat every credential the container can see as exposed to whatever the agents run.

Passing the NuGet token through the container environment is not a security boundary — it only keeps the credential out of the persistent volume, so it goes away with the session and is re-supplied from your host login on the next start. Note also that it is passed on the `docker compose` command line, so it is visible in `/proc/<pid>/cmdline` to any local user on the host for as long as the session runs.

- **The host Docker socket is deliberately not mounted.** The agent can control only the rootless DinD engine. Since the sidecar is privileged, this improves isolation but is not a hard VM-like security boundary.
- **The Docker API is unencrypted.** It is reachable only within the Compose network and is not exposed as a host port. Any container attached to that network can control the nested engine.
- **Network access is unrestricted.** The agent and nested Docker engine can connect directly to destinations reachable from the Docker host.

Notes:
- The image contains a build-time `buddy` user with UID/GID 1000, but Compose overrides those numeric IDs at runtime. On hosts with different IDs, some tools may display the user numerically because `/etc/passwd` is not modified.
- Compose starts the Docker dependency automatically and waits for its healthcheck. Containers are stopped when the agent exits; named volumes remain available for the next session.
- Agent CLI credentials are shared globally by all agent sessions through the persistent `agent-home` volume. Logging into the same CLI from two parallel sessions can overwrite the other session's state.
- Tools and configuration are split: the CLIs are installed in the image under `/opt/ai-buddy`, while `/home/buddy` is a persistent volume holding configuration, credentials, session history, and plans. `ai-buddy build` therefore delivers CLI updates without touching your logins. On a host whose UID is not 1000, `/opt/ai-buddy` is not writable for the session, so CLIs cannot update themselves in place — updates come from `ai-buddy build`.
- Git is installed but not configured: there is no identity, so `git commit` fails until you set one, and there is no credential helper, so pushing needs credentials you supply yourself. Reading history (`log`, `diff`, `status`, `fetch` over HTTPS) works out of the box. Both are one-time `git config --global` fixes that land in the persistent volume.
- `ai-buddy start` stops its Compose services automatically when the agent exits.

## Quick Reference

```bash
ai-buddy build   # build the image
ai-buddy start   # mount current directory into /workspace
```
