FROM debian:bookworm-slim

# System dependencies
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive DEBCONF_NOWARNINGS=yes apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        jq \
        less \
        libicu72 \
        procps \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# Development tools
RUN mkdir -p /usr/share/dotnet \
    && curl -fsSL https://builds.dotnet.microsoft.com/dotnet/scripts/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
    && bash /tmp/dotnet-install.sh --channel LTS --install-dir /usr/share/dotnet \
    && ln -s /usr/share/dotnet/dotnet /usr/bin/dotnet \
    && rm /tmp/dotnet-install.sh \
    && dotnet --version

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version \
    && npm --version

# Only the client is needed; the daemon runs in the rootless DinD sidecar.
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && printf '%s\n' \
        'Types: deb' \
        'URIs: https://download.docker.com/linux/debian' \
        'Suites: bookworm' \
        'Components: stable' \
        "Architectures: $(dpkg --print-architecture)" \
        'Signed-By: /etc/apt/keyrings/docker.asc' \
        > /etc/apt/sources.list.d/docker.sources \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        docker-ce-cli \
    && rm -rf /var/lib/apt/lists/* \
    && docker --version

# Session user
RUN groupadd -g 1000 buddy \
    && useradd -m -u 1000 -g 1000 -s /bin/bash buddy

# Agent CLIs live in the image so the persistent /home/buddy volume cannot
# shadow them. Only configuration, credentials, and history belong in $HOME.
ENV AI_BUDDY_TOOLS=/opt/ai-buddy
RUN mkdir -p ${AI_BUDDY_TOOLS} && chown buddy:buddy ${AI_BUDDY_TOOLS}

# Runtime configuration
COPY --chmod=755 welcome.sh /usr/local/bin/welcome.sh
RUN echo '/usr/local/bin/welcome.sh' >> /etc/bash.bashrc
WORKDIR /workspace

USER buddy
# /home/buddy/.local/bin stays first so a CLI that updates itself into the
# persistent home wins over the image copy underneath it.
ENV HOME=/home/buddy \
    PATH="/home/buddy/.local/bin:${AI_BUDDY_TOOLS}/.local/bin:${AI_BUDDY_TOOLS}/.opencode/bin:${PATH}"

# HOME must prefix `bash`, not `curl` — in a pipeline the assignment only
# applies to the command it precedes. The version check afterwards deliberately
# runs with the real runtime HOME to catch installers that bake $HOME into
# their launcher scripts.
RUN curl -fsSL https://opencode.ai/install | HOME=${AI_BUDDY_TOOLS} bash \
    && opencode --version

RUN curl -fsSL https://pi.dev/install.sh | HOME=${AI_BUDDY_TOOLS} bash \
    && pi --version

RUN curl -fsSL https://claude.ai/install.sh | HOME=${AI_BUDDY_TOOLS} bash \
    && claude --version

CMD ["/bin/bash"]
