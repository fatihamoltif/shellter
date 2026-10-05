#!/bin/bash
set -e

: "${SSH_USER:?Variable SSH_USER manquante}"
: "${SSH_PASSWORD:?Variable SSH_PASSWORD manquante}"

# Cree l'utilisateur seulement s'il n'existe pas deja (utile si le conteneur redemarre)
if ! id "$SSH_USER" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$SSH_USER"
fi

# Definit le mot de passe recu depuis l'exterieur, jamais ecrit dans l'image
echo "${SSH_USER}:${SSH_PASSWORD}" | chpasswd

# sshd a besoin de ce dossier pour la separation de privileges
mkdir -p /run/sshd

# Genere les cles hote SSH au demarrage (pas au build : sinon toutes les
# locations partageraient la meme cle, ce qui declenche des alertes
# "possible attaque MITM" cote client SSH)
ssh-keygen -A

# "exec" remplace le process actuel par sshd : ainsi sshd devient le PID 1
# du conteneur et recoit correctement les signaux d'arret (docker stop)
exec /usr/sbin/sshd -D -e
