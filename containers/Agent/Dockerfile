FROM debian:bookworm-slim

ARG USER_NAME=buddy
ARG USER_UID=1000
ARG USER_GID=1000
ARG DOTNET_VERSION=10.0
ARG DOTNET_INSTALL_DIR=/usr/share/dotnet

# Install system dependencies
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive DEBCONF_NOWARNINGS=yes apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        libicu-dev \
        procps \
        wget \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g ${USER_GID} ${USER_NAME} \
    && useradd -m -u ${USER_UID} -g ${USER_GID} -s /bin/bash ${USER_NAME}

# Install .NET (system-wide)
RUN mkdir -p ${DOTNET_INSTALL_DIR} \
    && wget -q https://builds.dotnet.microsoft.com/dotnet/scripts/v1/dotnet-install.sh -O ${DOTNET_INSTALL_DIR}/dotnet-install.sh \
    && chmod +x ${DOTNET_INSTALL_DIR}/dotnet-install.sh \
    && bash ${DOTNET_INSTALL_DIR}/dotnet-install.sh --version latest --channel ${DOTNET_VERSION} --install-dir ${DOTNET_INSTALL_DIR} \
    && ln -s ${DOTNET_INSTALL_DIR}/dotnet /usr/bin/dotnet \
    && rm ${DOTNET_INSTALL_DIR}/dotnet-install.sh \
    && dotnet --version

# Welcome message (system-wide hook)
COPY ./welcome.sh /usr/local/bin/welcome.sh
RUN chmod +x /usr/local/bin/welcome.sh \
    && echo '/usr/local/bin/welcome.sh' >> /etc/bash.bashrc

WORKDIR /workspace
RUN chown ${USER_NAME}:${USER_NAME} /workspace

# Switch to non-root user for the CLI installs
USER ${USER_NAME}
ENV HOME=/home/${USER_NAME}
ENV PATH="/home/${USER_NAME}/.local/bin:/home/${USER_NAME}/.opencode/bin:${PATH}"

# Install OpenCode CLI
RUN curl -fsSL https://opencode.ai/install | bash \
    && opencode --version

# Install Claude Code CLI
RUN curl -fsSL https://claude.ai/install.sh | bash \
    && claude --version

CMD ["/bin/bash"]
