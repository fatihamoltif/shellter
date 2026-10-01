#!/bin/sh
set -e

: "${SSH_USER:?Variable SSH_USER manquante}"
: "${SSH_PASSWORD:?Variable SSH_PASSWORD manquante}"

# adduser -D = pas de mot de passe impose a la creation (on le definit juste apres)
# -s /bin/sh = shell par defaut d'Alpine (bash n'est pas installe de base)
if ! id "$SSH_USER" >/dev/null 2>&1; then
  adduser -D -s /bin/sh "$SSH_USER"
fi

echo "${SSH_USER}:${SSH_PASSWORD}" | chpasswd

mkdir -p /run/sshd
ssh-keygen -A

exec /usr/sbin/sshd -D -e

