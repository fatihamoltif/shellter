#!/usr/bin/env bash
# check_network.sh — vérifie la connectivité ping + SSH entre toutes les VM Shellter.
# Auteur : P4 (Jamai Ali) — Séance S2.
#
# Usage :
#   bash scripts/check_network.sh
#
# À lancer depuis le poste (ou le control node) qui a accès SSH aux VM Vagrant.
# Variables d'environnement optionnelles :
#   SSH_USER  (défaut: vagrant)
#   SSH_KEY   (défaut: $HOME/.vagrant.d/insecure_private_key)
#
# Code de sortie : 0 si tout passe, 1 sinon.

set -uo pipefail

SSH_USER="${SSH_USER:-vagrant}"
SSH_KEY="${SSH_KEY:-$HOME/.vagrant.d/insecure_private_key}"
SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
          -o ConnectTimeout=10 -o BatchMode=yes -i "$SSH_KEY")

# Nom -> IP (aligné sur ansible/hosts.ini et docs/architecture.md)
NAMES=(controller worker1 worker2 worker3)
declare -A IP=(
  [controller]=192.168.56.10
  [worker1]=192.168.56.11
  [worker2]=192.168.56.12
  [worker3]=192.168.56.13
)

fail=0
pass() { printf '  \033[32mOK\033[0m   %s\n' "$1"; }
ko()   { printf '  \033[31mKO\033[0m   %s\n' "$1"; fail=$((fail + 1)); }

echo "== 1. Ping depuis ce poste vers chaque VM =="
for n in "${NAMES[@]}"; do
  if ping -c1 -W2 "${IP[$n]}" >/dev/null 2>&1; then
    pass "ping $n (${IP[$n]})"
  else
    ko "ping $n (${IP[$n]})"
  fi
done

echo "== 2. SSH depuis ce poste vers chaque VM =="
for n in "${NAMES[@]}"; do
  if ssh "${SSH_OPTS[@]}" "$SSH_USER@${IP[$n]}" 'hostname' >/dev/null 2>&1; then
    pass "ssh $n"
  else
    ko "ssh $n"
  fi
done

echo "== 3. Connectivité entre VM (ping + port SSH 22) =="
for src in "${NAMES[@]}"; do
  for dst in "${NAMES[@]}"; do
    [ "$src" = "$dst" ] && continue
    dip="${IP[$dst]}"
    if ssh "${SSH_OPTS[@]}" "$SSH_USER@${IP[$src]}" \
        "ping -c1 -W2 $dip >/dev/null 2>&1 && timeout 3 bash -c 'echo > /dev/tcp/$dip/22'" \
        >/dev/null 2>&1; then
      pass "$src -> $dst (ping + ssh:22)"
    else
      ko "$src -> $dst (ping + ssh:22)"
    fi
  done
done

echo
if [ "$fail" -eq 0 ]; then
  echo "✅ Tous les tests réseau sont PASSÉS."
  exit 0
else
  echo "❌ $fail test(s) en échec — voir ci-dessus."
  exit 1
fi
