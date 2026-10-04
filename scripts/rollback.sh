#!/usr/bin/env bash
# Rollback vers une version précédente — Séance S10 (P4).
#
# Principe : chaque déploiement correspond à un tag Git + une image taguée (SHA/tag).
# En cas de problème, on redéploie le tag précédent, puis on rejoue le smoke test.
#
# Usage :
#   scripts/rollback.sh <tag_cible>        # ex : scripts/rollback.sh v1.0
#   scripts/rollback.sh                    # liste les tags disponibles
set -euo pipefail

TARGET="${1:-}"

if [ -z "$TARGET" ]; then
  echo "Usage : $0 <tag_cible>"
  echo "Tags disponibles (du plus récent au plus ancien) :"
  git tag --sort=-creatordate | head -10
  exit 1
fi

echo "==> Rollback vers le tag : $TARGET"
git fetch --tags --quiet
if ! git rev-parse "refs/tags/$TARGET" >/dev/null 2>&1; then
  echo "ERREUR : le tag '$TARGET' n'existe pas."
  exit 1
fi

# 1) se positionner sur la version cible
git checkout --quiet "tags/$TARGET"
echo "    code positionné sur $TARGET ($(git rev-parse --short HEAD))"

# 2) redéployer cette version
#    En production : via le pipeline / Ansible, en pullant l'image taguée.
#      ansible-playbook -i ansible/hosts.ini ansible/deploy.yml -e "version=$TARGET"
#    En local (démo) : relancer la stack avec le code de ce tag.
echo "    redéploiement de la version $TARGET..."
docker compose -f docker-compose.ci.yml up -d --build

# 3) vérifier que le rollback est sain
echo "    smoke test post-rollback..."
python scripts/smoke_test.py

echo "==> Rollback vers $TARGET TERMINÉ avec succès."
