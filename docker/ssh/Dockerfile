# Image d'un environnement loué, accessible en SSH — Séance S6/S10 (intégration réelle).
# BASE est fourni à la construction : ubuntu:24.04, debian:13 ou alpine:latest.
ARG BASE=ubuntu:24.04
FROM ${BASE}

# Installer openssh-server (apt pour Ubuntu/Debian, apk pour Alpine)
RUN set -eux; \
    if command -v apt-get >/dev/null 2>&1; then \
        apt-get update && apt-get install -y --no-install-recommends openssh-server && \
        mkdir -p /run/sshd && rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
        apk add --no-cache openssh bash shadow && ssh-keygen -A; \
    fi

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
