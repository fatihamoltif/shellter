# 📘 Documentation S4 : Déploiement de l'Application et Base de Données

## 1. Présentation de l'environnement

Notre infrastructure applicative pour cette séance est hébergée sur la machine virtuelle Vagrant principale (**shellter-control**).

Le déploiement s'appuie sur **Docker Compose** et orchestre deux services essentiels :
- **web** : L'application web développée en Flask.
- **db** : La base de données relationnelle utilisant l'image `postgres:16-alpine`.

---

## 2. Procédure d'installation stricte (Step-by-step)

Pour garantir un déploiement sans erreur, suivez précisément ces étapes sur la machine `shellter-control`.

### A. Emplacement de travail
Vous devez impérativement vous placer dans le répertoire partagé par Vagrant (qui contient les sources du projet) :
```bash
cd /vagrant
```

### B. Configuration des variables d'environnement
La création du fichier `.env` (en le copiant depuis `.env.example`) est **obligatoire**. Ce fichier doit contenir les variables suivantes :
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `SECRET_KEY`

⚠️ **Attention** : Sans ce fichier `.env` correctement renseigné, le service de base de données refusera de démarrer !

### C. Lancement des conteneurs
Une fois la configuration prête, exécutez la commande suivante (avec les privilèges administrateur) pour construire et démarrer les services en arrière-plan :
```bash
sudo docker compose up -d --build
```

---

## 3. Initialisation de la base de données (SQLAlchemy)

Une fois les conteneurs en cours d'exécution, il faut créer les tables correspondantes à nos modèles (comme `User` et `Distribution`) dans la base de données. 

Voici les commandes exactes à exécuter pour appliquer les migrations via SQLAlchemy :

1. **Initialisation** *(à faire uniquement si le dossier `migrations` est absent)* :
   ```bash
   sudo docker compose exec web flask db init
   ```
2. **Génération du script de migration** :
   ```bash
   sudo docker compose exec web flask db migrate -m "Initialisation"
   ```
3. **Application des modifications** en base de données :
   ```bash
   sudo docker compose exec web flask db upgrade
   ```

---

## 4. Guide de dépannage (Troubleshooting) - Séance 4

Voici les problèmes classiques rencontrés lors de cette séance et leurs solutions :

- 💥 **Crash du conteneur web (Exit 0 / Restarting)**
  Vérifiez que le fichier `app/__init__.py` n'est pas vide. Il doit absolument initialiser l'application Flask et faire le lien avec la base de données via `db.init_app(app)`.

- 🐛 **Erreur "No module named psycopg"**
  Vérifiez votre fichier `docker-compose.yml`. La variable d'environnement `DATABASE_URL` doit utiliser le dialecte exact correspondant à la dépendance installée, c'est-à-dire : `postgresql+psycopg2://...`.

- 🌐 **Timeout réseau lors du build**
  Si `pip` échoue lors du téléchargement des dépendances Python, cela est souvent lié à des instabilités du réseau de la VM. Il suffit généralement de relancer la commande de build (`sudo docker compose up -d --build`) ou de configurer un délai d'attente (timeout) plus long pour `pip`.

---

## 5. Validation des modèles

Pour s'assurer que l'application communique correctement avec la base de données et que nos modèles fonctionnent, nous allons créer un utilisateur de test.

Ouvrez le shell interactif Flask au sein du conteneur `web` :
```bash
sudo docker compose exec web flask shell
```

Puis, exécutez le bloc de code Python suivant pour tester la création d'un utilisateur et le hachage sécurisé de son mot de passe :

```python
from app.models import db, User

# Création de l'utilisateur
u = User(username='admin', email='admin@shellter.local')

# Définition et hachage du mot de passe
u.set_password('mon_super_mot_de_passe')

# Ajout à la session et sauvegarde en base de données
db.session.add(u)
db.session.commit()

print(f"L'utilisateur {u.username} a été créé avec succès !")
```
