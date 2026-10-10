# Monte un cluster k3d mono-noeud et deploie Shellter (version Kubernetes) pour la demo.
# Pre-requis : Docker Desktop demarre, kubectl, k3d.
# Lancer depuis la RACINE du depot, sur la branche kubernetes :
#     .\k8s\local-k3d\setup.ps1
$ErrorActionPreference = "Stop"

# --- localiser k3d (chemin connu en priorite, sinon PATH) ---
$k3d = "$env:LOCALAPPDATA\k3d\k3d.exe"
if (-not (Test-Path $k3d)) {
  $cmd = Get-Command k3d -ErrorAction SilentlyContinue
  if ($cmd) { $k3d = $cmd.Source }
}
if (-not (Test-Path $k3d)) {
  throw "k3d introuvable. Telecharge k3d-windows-amd64.exe depuis https://github.com/k3d-io/k3d/releases et place-le dans $env:LOCALAPPDATA\k3d\k3d.exe"
}
Write-Host "k3d : $k3d" -ForegroundColor DarkGray

Write-Host "== 1/4  Cluster k3d 'shellter' ==" -ForegroundColor Cyan
$exists = (& $k3d cluster list 2>$null | Select-String "^shellter\s")
if (-not $exists) { & $k3d cluster create shellter --servers 1 --agents 0 --wait }
else { Write-Host "  (cluster deja present)" }

Write-Host "== 2/4  Build + import des images (Flask + SSH Ubuntu) ==" -ForegroundColor Cyan
docker build -q -t shellter-flask:local -f docker/Dockerfile .
docker build -q -t shellter-ssh-ubuntu:local --build-arg BASE=ubuntu:24.04 docker/ssh
& $k3d image import shellter-flask:local shellter-ssh-ubuntu:local -c shellter

Write-Host "== 3/4  Deploiement de la stack ==" -ForegroundColor Cyan
kubectl apply -f k8s/00-namespace.yaml -f k8s/rbac.yaml -f k8s/secret.example.yaml
kubectl apply -f k8s/local-k3d/configmap.yaml
kubectl apply -f k8s/postgres-service.yaml -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/flask-service.yaml -f k8s/local-k3d/flask-deployment.yaml
kubectl apply -f k8s/local-k3d/expiration-cronjob.yaml
kubectl -n shellter rollout status deployment/flask --timeout=180s

Write-Host "== 4/4  Pret ! ==" -ForegroundColor Green
Write-Host "Dans un terminal :  kubectl -n shellter port-forward svc/flask 8080:80"
Write-Host "Puis ouvre http://localhost:8080   (admin / admin123)"
