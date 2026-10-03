"""FAILLE VOLONTAIRE (branche demo-vuln, S9) — secret en dur.

Ne JAMAIS committer de clé secrète. Doit être bloqué par gitleaks.
Correctif : variable d'environnement / Secret CI / Ansible Vault + révoquer la clé.
"""

AWS_ACCESS_KEY_ID = "AKIA2E4XZ9QWERTY1234"
AWS_SECRET_ACCESS_KEY = "wJalrXabc123FEMI+K7MDENGbPxRfiCYsecretKEY"
