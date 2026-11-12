FROM debian:trixie-slim

ARG USER_UID=1000
ARG USER_GID=1000
ARG DOTNET_VERSION=11.0

# System dependencies
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive DEBCONF_NOWARNINGS=yes apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        jq \
        less \
        libicu76 \
        libssl3t64 \
        libgssapi-krb5-2 \
        procps \
        tzdata \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# Development tools: .NET SDK (version via build arg)
RUN mkdir -p /usr/share/dotnet \
    && curl -fsSL https://builds.dotnet.microsoft.com/dotnet/scripts/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
    && bash /tmp/dotnet-install.sh --channel "${DOTNET_VERSION}" --install-dir /usr/share/dotnet \
    && ln -s /usr/share/dotnet/dotnet /usr/bin/dotnet \
    && rm /tmp/dotnet-install.sh \
    && dotnet --version

ENV DOTNET_ROOT=/usr/share/dotnet
ENV PATH="/usr/share/dotnet:${PATH}"

# Node.js 24
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version \
    && npm --version

# Docker CLI with buildx and compose plugins (no daemon)
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && printf '%s\n' \
        'Types: deb' \
        'URIs: https://download.docker.com/linux/debian' \
        'Suites: trixie' \
        'Components: stable' \
        "Architectures: $(dpkg --print-architecture)" \
        'Signed-By: /etc/apt/keyrings/docker.asc' \
        > /etc/apt/sources.list.d/docker.sources \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        docker-ce-cli \
        docker-buildx-plugin \
        docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/* \
    && docker --version \
    && docker buildx version \
    && docker compose version

# Session user
# UID/GID match the host user (the image is built per machine). -o tolerates IDs
# that already exist in the base image, e.g. macOS GID 20 (dialout in Debian).
RUN groupadd -o -g "${USER_GID}" buddy \
    && useradd -o -m -u "${USER_UID}" -g "${USER_GID}" -s /bin/bash buddy \
    && mkdir -p /workspace /state \
    && chown buddy:buddy /workspace /state

# Runtime configuration
ENV HOME=/home/buddy

COPY --chmod=755 welcome.sh /usr/local/bin/welcome.sh
RUN echo '/usr/local/bin/welcome.sh' >> /etc/bash.bashrc

WORKDIR /workspace

USER buddy

# OpenCode
ENV PATH="/home/buddy/.opencode/bin:${PATH}"
RUN curl -fsSL https://opencode.ai/v2/install | bash \
    && opencode --version

# Pi
ENV PATH="/home/buddy/.pi/agent/bin:${PATH}"
RUN curl -fsSL https://pi.dev/install.sh | bash \
    && pi --version

# Claude Code
ENV PATH="/home/buddy/.local/bin:${PATH}"
RUN curl -fsSL https://claude.ai/install.sh | bash \
    && claude --version

CMD ["/bin/bash"]
