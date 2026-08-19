FROM debian:bookworm-slim

ARG USER_UID=1000
ARG USER_GID=1000
ARG DOTNET_VERSION=10.0
ARG DOTNET_INSTALL_DIR=/usr/share/dotnet
ENV HOME=/home/buddy
ENV NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/ai-buddy-ca.crt

# Install system dependencies
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive DEBCONF_NOWARNINGS=yes apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        libicu72 \
        procps \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for the Pi coding agent.
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version \
    && npm --version

# Create non-root user
RUN groupadd -g ${USER_GID} buddy \
    && useradd -m -u ${USER_UID} -g ${USER_GID} -s /bin/bash buddy

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
USER buddy
ENV PATH="/home/buddy/.local/bin:/home/buddy/.opencode/bin:${PATH}"

RUN curl -fsSL https://opencode.ai/install | bash \
    && opencode --version

RUN curl -fsSL https://pi.dev/install.sh | bash \
    && pi --version

RUN curl -fsSL https://claude.ai/install.sh | bash \
    && claude --version

USER root

# ── Entrypoint: trust the proxy CA at container start, then drop to buddy ───
# Needs root to update the system trust store (see entrypoint.sh); it execs
# the actual CMD as buddy via runuser once that's done.
COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/bin/bash"]
