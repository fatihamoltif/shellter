# S10 — Registre privé et SBOM (P1)

## Objectif

Pousser les images Docker taguées dans un registre privé, générer le SBOM
(Software Bill of Materials) de chaque image avec Syft, et le publier en
artefact de build. Preuve attendue : l'image du commit X se trouve dans le
registre, avec son SBOM.

## Registre choisi : GitHub Container Registry (ghcr.io)

Choisi plutôt que Docker Hub ou un registre externe car l'authentification
est automatique dans GitHub Actions (`secrets.GITHUB_TOKEN`), sans compte ni
secret supplémentaire à gérer. Les images sont publiées en privé sous le
compte/organisation du dépôt.

## Ce qui a été ajouté dans `.github/workflows/docker-build.yml`

- `permissions: packages: write` sur le job, nécessaire pour que le
  `GITHUB_TOKEN` du run ait le droit de publier sur `ghcr.io`.
- Connexion au registre (`docker/login-action@v3`) avant le build, ignorée
  sur les pull requests (`if: github.event_name != 'pull_request'`).
- Chaque image buildée est retaguée en
  `ghcr.io/<owner>/shellter-<image>:<sha-court>` (+ `:latest`, et
  `:<tag-git>` si le push correspond à un tag `v*.*.*`), puis poussée.
- Génération du SBOM de chaque image avec **Syft**, via l'action
  `anchore/sbom-action@v0` (format CycloneDX JSON), publié automatiquement
  comme artefact du run (`sbom-<image>-<sha>.json`).

Le matrix build a aussi dû être corrigé pour correspondre à l'arborescence
réelle de `docker/` sur cette branche (contextes de build différents selon
l'image, Dockerfile de l'agent récupéré depuis la branche d'Alijamai — absent
jusque-là) et pour fournir `SSH_USER`/`SSH_PASSWORD` au smoke test des images
SSH (ubuntu/debian/alpine), exigés par leur `entrypoint.sh`.

## Preuve (commit `0b1affc`, run #8 "Build and Test Docker Images")

Les 5 images sont publiées dans le registre avec le tag du commit :

Pour récupérer une image avec son SBOM :

```bash
docker pull ghcr.io/fatihamoltif/shellter-ubuntu:0b1affc
# SBOM : artefact "sbom-ubuntu-0b1affc.json" du run Actions associé au commit 0b1affc
```
