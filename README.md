## Shellter - Plateforme de location d'environnements Linux

## Présentation du projet

Dans le cadre de ce projet, nous cherchons à répondre à un besoin simple : permettre à un utilisateur d'accéder rapidement et temporairement à un environnement Linux sans avoir à installer lui-même une nouvelle distribution sur sa machine.

L'idée est donc de proposer une application web depuis laquelle un utilisateur peut choisir une distribution, par exemple Ubuntu ou Debian, ainsi qu'une durée de location. Le système crée ensuite automatiquement un environnement Linux isolé auquel l'utilisateur peut accéder en SSH.

Nous avons choisi d'utiliser des conteneurs Docker afin de créer ces environnements de manière rapide, légère et reproductible.

---

## Problématique

Le problème ne consiste pas seulement à lancer un conteneur Docker.

Il faut également répondre à plusieurs questions :

- comment permettre à plusieurs utilisateurs de demander des environnements en parallèle ?
- comment savoir quel conteneur appartient à quel utilisateur ?
- comment gérer automatiquement la durée de vie d'une location ?
- comment éviter de configurer manuellement chaque machine ?
- comment réagir si une machine hébergeant des conteneurs devient indisponible ?
- comment rendre l'ensemble reproductible sur une autre machine ?

Notre objectif est donc de construire une plateforme capable de gérer automatiquement le cycle de vie complet d'une location.

---

## Solution proposée

Nous séparons le projet en deux grandes parties :

### 1. Le plan de contrôle

Le plan de contrôle contient les composants qui prennent les décisions et mémorisent l'état du système.

Il comprend :

- **Flask**, qui fournit l'application web et reçoit les demandes des utilisateurs ;
- **PostgreSQL**, qui conserve les informations sur les utilisateurs, les locations et les Workers ;
- un **Provisioner**, chargé de créer et supprimer les conteneurs ;
- un **Watchdog**, chargé de surveiller les expirations et les éventuelles pannes.

### 2. Le plan d'exécution

Le plan d'exécution correspond aux machines qui exécutent réellement les environnements Linux.

Ces machines sont appelées des **Workers**.

Chaque Worker possède Docker et peut héberger plusieurs conteneurs utilisateurs.

Par exemple :

Worker 1
├── Conteneur Ubuntu - utilisateur A
├── Conteneur Ubuntu - utilisateur B
└── Conteneur Debian - utilisateur C
