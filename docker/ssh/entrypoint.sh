#!/bin/sh
# Crée l'utilisateur SSH à partir des variables fournies à chaque location, puis lance sshd.
# Aucun mot de passe n'est figé dans l'image.
set -e

SSH_USER="${SSH_USER:-shellter}"
SSH_PASSWORD="${SSH_PASSWORD:-changeme}"

# Créer l'utilisateur (useradd pour Debian/Ubuntu, adduser pour Alpine)
if command -v useradd >/dev/null 2>&1; then
    id "$SSH_USER" >/dev/null 2>&1 || useradd -m -s /bin/bash "$SSH_USER"
else
    id "$SSH_USER" >/dev/null 2>&1 || adduser -D -s /bin/sh "$SSH_USER"
fi
echo "$SSH_USER:$SSH_PASSWORD" | chpasswd

# Autoriser l'authentification par mot de passe
if [ -f /etc/ssh/sshd_config ]; then
    sed -i 's/#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config || true
fi

# S'assurer que les clés d'hôte existent (surtout Alpine)
[ -f /etc/ssh/ssh_host_rsa_key ] || ssh-keygen -A 2>/dev/null || true
mkdir -p /run/sshd 2>/dev/null || true

exec /usr/sbin/sshd -D -e
