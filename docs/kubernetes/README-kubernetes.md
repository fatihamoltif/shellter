# Shellter sur Kubernetes — déploiement & démo

Guide de la branche `kubernetes` (séance K5, partie P4). Voir aussi
[`architecture.md`](architecture.md), [`PLAN.md`](PLAN.md) et [`REPARTITION.md`](REPARTITION.md).

> ## État de la branche
> **Code complet et validé par la CI** (lint des manifests `kubeconform`, build + push
> des images, scan Trivy, tests unitaires — tous verts). Réimplémentation entière de
> l'orchestration avec k3s : manifests, client API Kubernetes (`app/k8s_client.py`),
> RBAC, Ingress HTTPS, self-healing natif, expiration par CronJob, CI dédiée.
>
> **Déploiement sur cluster réel : non réalisé.** Pas pour une raison de code, mais de
> **ressources** : un cluster k3s à 4 nœuds (serveur API + etcd + agents + pods) ne tient
> pas sur nos VM Vagrant de dev (hôte 16 Go qui sature/swappe → l'API k3s n'arrive pas à
> démarrer). La **démonstration live** de Shellter se fait donc sur la branche **`main`**
> (location → vrai conteneur → SSH réel, self-healing, expiration, HTTPS — testée de bout
> en bout). La présente branche vaut comme **preuve de conception** : elle montre que
> l'architecture « maison » correspond bien aux mécanismes natifs de Kubernetes (voir le
> tableau de mapping dans [`architecture.md`](architecture.md)).
>
> Les étapes ci-dessous sont la **procédure de déploiement** prévue, à exécuter sur un
> cluster suffisamment dimensionné.

## 1. Monter le cluster k3s (séance K1)
```bash
cd ansible
ansible-playbook -i hosts.ini k3s.yml --ask-vault-pass
# le kubeconfig est déposé dans k8s/kubeconfig
export KUBECONFIG=$PWD/../k8s/kubeconfig
kubectl get nodes          # -> 4 nœuds Ready
```

## 2. Déployer la stack (séances K2/K3/K4)
```bash
# secrets (ne pas versionner) + TLS de l'Ingress
cp k8s/secret.example.yaml k8s/secret.yaml   # puis éditer les valeurs
openssl req -x509 -nodes -newkey rsa:2048 -days 365 -subj "/CN=shellter.local" \
  -keyout tls.key -out tls.crt

kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/secret.yaml -f k8s/configmap.yaml -f k8s/rbac.yaml
kubectl -n shellter create secret tls shellter-tls --cert=tls.crt --key=tls.key
kubectl apply -f k8s/postgres-service.yaml -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/flask-service.yaml -f k8s/flask-deployment.yaml -f k8s/ingress.yaml
kubectl apply -f k8s/expiration-cronjob.yaml -f k8s/reconciler-cronjob.yaml
```
Ajouter `192.168.56.10  shellter.local` dans `/etc/hosts`, puis :
```bash
curl -k https://shellter.local/health      # -> {"status":"ok","db":"up"}
```

## 3. Scénario de démo
1. **Cluster** : `kubectl get nodes` → 4 Ready.
2. **Location** : se connecter à `https://shellter.local`, louer Ubuntu → la page affiche
   `ssh shellter@<node-ip> -p <nodeport>` ; `kubectl -n shellter get deploy,svc` montre
   `env-<id>` + son Service NodePort.
3. **SSH** : se connecter au conteneur ; `cat /etc/os-release` confirme la distro.
4. **Self-healing** : `kubectl -n shellter delete pod -l shellter.instance_id=<id>` → le
   Deployment recrée le pod automatiquement ; le réconciliateur remet l'instance `running`.
5. **Panne de nœud** : `vagrant halt worker1` → les pods de ce nœud sont reschedulés ailleurs.
6. **Expiration** : louer 2 min → le CronJob supprime l'env à l'échéance, base cohérente.

## 4. Ce qui change dans le code vs la branche `main`
- `app/k8s_client.py` **remplace** `agent_client` (crée Deployment + Service NodePort).
- `/rent` et `/stop` basculent sur K8s quand `ORCHESTRATOR=k8s` (ConfigMap) ; la branche
  `main` (agent) reste utilisable avec `ORCHESTRATOR=agent`.
- Quota, prolongation, rôle admin, chiffrement SSH, migrations : **réutilisés tels quels**.

## 5. CI/CD (séance K5)
`.github/workflows/k8s-ci.yml` : lint `kubeconform` → build & push (Flask + 3 images SSH,
taguées par SHA) → scan **Trivy** → déploiement `kubectl apply` (si le secret `KUBECONFIG`
est fourni au dépôt).
