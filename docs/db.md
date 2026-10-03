# Modèle de données:

## 1. Table users

Attributs :

- id : entier
- username : chaîne de caractères
- email : chaîne de caractères
- password_hash : chaîne de caractères
- created_at : date/heure

Contraintes :

- id : clé primaire
- username : unique
- email : unique

## 2. Table distributions

Attributs :
-id : entier

- name : chaîne de caractères
- docker_image : chaîne de caractères
- version : chaîne de caractères
  -status : chaîne de caractères
  --> **Valeurs possibles : enabled/disabled**

Contraintes:

- id : clé primaire

## 3. Table workers

Attributs :

- id : entier
- hostname : chaîne de caractères
- ip : chaîne de caractères
  -status : chaîne de caractères
  --> **Valeurs possibles : AVAILABLE/BUSY/OFFLINE**
- cpu : nombre
- memory : nombre
- last_heartbeat : date/heure
- max_instances : entier
- agent_url : chaîne de caractères

Contraintes :

- hostname : unique
- id : clé primaire

## 4. Table instances

Attributs :

- id : entier
- container_id : chaîne de caractères
- worker_id : entier → référence workers.id
- distribution_id : entier → référence distributions.id
- ssh_port : entier
  -status : chaîne de caractères
  --> **Valeurs possibles : pending / creating / running / recovering / stopped / deleted / error**
- created_at : date/heure
- ssh_user : chaîne de caractères
- ssh_secret : chaîne de caractères

Contraintes:

- id : clé primaire

Clés étrangères :

- worker_id → workers.id
- distribution_id → distributions.id

## 5. Table rentals

Attributs :

- id :entier
- user_id : entier
- instance_id : entier
- start_time :date/heure
- end_time : date/heure
  -status : chaîne de caractères
  --> **Valeurs possibles : ACTIVE / EXPIRED / CANCELLED**

Contraintes:

- id : clé primaire

Clés étrangères :
-user_id : entier → référence users.id
-instance_id : entier → référence instances.id

## Relations

- Un utilisateur peut avoir plusieurs locations.
- Une location appartient à un utilisateur.
- Une location correspond à une instance.
- Une instance utilise une distribution.
- Une instance est hébergée sur un worker.
- Un worker peut héberger plusieurs instances.

## Cycle de vie d'une instance

pending → creating → running → stopped → deleted

En cas d'échec pendant la création :

creating → error

En cas de panne :

running → recovering → running
