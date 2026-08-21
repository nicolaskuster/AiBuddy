FROM debian:bookworm-slim

ARG DOTNET_VERSION=10.0
ARG DOTNET_INSTALL_DIR=/usr/share/dotnet
# Trust the proxy CA everywhere. Node reads its own variable; Python tooling
# (pip, requests, httpx) ships its own CA bundle and ignores the system store,
# so it needs to be pointed at the bundle entrypoint.sh regenerates.
ENV NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/ai-buddy-ca.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Install system dependencies
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

# Install Node.js for the Pi coding agent.
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version \
    && npm --version

# Create non-root user. The UID is fixed here and adjusted at container start to
# match whoever owns the mounted workspace (see entrypoint.sh), which keeps the
# image itself independent of the host it was built on.
RUN groupadd -g 1000 buddy \
    && useradd -m -u 1000 -g 1000 -s /bin/bash buddy

# Welcome message (system-wide hook)
COPY --chmod=755 welcome.sh /usr/local/bin/welcome.sh
RUN echo '/usr/local/bin/welcome.sh' >> /etc/bash.bashrc

WORKDIR /workspace

# Install .NET (system-wide)
RUN mkdir -p ${DOTNET_INSTALL_DIR} \
    && curl -fsSL https://builds.dotnet.microsoft.com/dotnet/scripts/v1/dotnet-install.sh -o ${DOTNET_INSTALL_DIR}/dotnet-install.sh \
    && bash ${DOTNET_INSTALL_DIR}/dotnet-install.sh --version latest --channel ${DOTNET_VERSION} --install-dir ${DOTNET_INSTALL_DIR} \
    && ln -s ${DOTNET_INSTALL_DIR}/dotnet /usr/bin/dotnet \
    && rm ${DOTNET_INSTALL_DIR}/dotnet-install.sh \
    && dotnet --version

# Install the agent CLIs as the unprivileged user.
#
# The installers are pointed at ${AI_BUDDY_TOOLS} rather than /home/buddy on
# purpose: docker-compose.yml mounts the persistent agent-home volume over
# /home/buddy, and Docker seeds a named volume from the image only while that
# volume is still empty. Installing into $HOME would let the volume shadow the
# image copies from the second start onwards, so `ai-buddy build` would never
# deliver a CLI update again. Tools therefore live in the image; only config,
# credentials and session history live in the volume.
ENV AI_BUDDY_TOOLS=/opt/ai-buddy
RUN mkdir -p ${AI_BUDDY_TOOLS} && chown buddy:buddy ${AI_BUDDY_TOOLS}

USER buddy
# /home/buddy/.local/bin stays first so a CLI that updates itself into the
# persistent home wins over the image copy underneath it.
ENV PATH="/home/buddy/.local/bin:${AI_BUDDY_TOOLS}/.local/bin:${AI_BUDDY_TOOLS}/.opencode/bin:${PATH}"
ENV HOME=/home/buddy

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

USER root

# ── Entrypoint: trust the proxy CA at container start, then drop to buddy ───
# Needs root to update the system trust store (see entrypoint.sh); it execs
# the actual CMD as buddy via runuser once that's done.
COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/bin/bash"]
