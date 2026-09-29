# S7 — Résilience & haute disponibilité (P4)

> **Auteur : Jamai Ali (P4)** · Binômes : P1+P4 / P2+P3
> **Output prof de la séance :** `docker kill` sur une instance louée → réparation automatique,
> accès SSH restauré.

---

## 1. Contexte et objectif

La S7 rend le service **résilient** : si un conteneur crashe ou si un worker tombe, le service se
répare tout seul. Ma partie (P4) est la **reprise sur un autre worker** : quand un worker passe
OFFLINE, ses instances actives sont recréées ailleurs.

- P1 → heartbeat + détection OFFLINE · P2 → watcher des conteneurs (redémarrage) · P3 → gestionnaire
  d'expiration · **P4 → reprise sur un autre worker**.

**Preuve attendue :** scénario `vagrant halt worker1` → worker1 OFFLINE → l'instance repart sur
worker2.

---

## 2. Ma partie P4 en détail (`app/recovery.py`)

### 2.1 Détection OFFLINE — `mark_stale_workers_offline()`
Passe **OFFLINE** tout worker dont le heartbeat est plus vieux que 30 s (ou absent).
> C'est la logique de heartbeat, qui sera portée à terme par l'endpoint `/workers/heartbeat` de P1.
> Je l'inclus ici pour pouvoir **déclencher et tester** la reprise de bout en bout.

### 2.2 Reprise — `recover_instances()`
Pour chaque worker OFFLINE, pour chacune de ses instances actives :
```
1. instance -> status "recovering"
2. Resource Manager choisit un AUTRE worker (les OFFLINE sont exclus)
   └─ si aucun worker dispo -> l'instance reste "recovering"
3. l'agent recrée le conteneur sur le nouveau worker
   (durée de location préservée, nouveau port SSH libre)
   └─ si l'agent échoue -> instance "error"
4. mise à jour de l'instance : nouveau worker_id, nouveau ssh_port, nouveau container_id,
   status "running"  -> l'utilisateur voit le nouveau host/port dans son dashboard
```

**Pourquoi ça marche sans changer le Resource Manager :** `select_worker()` exclut déjà les workers
OFFLINE et choisit le moins chargé → l'instance repart naturellement sur un worker sain.

**Cohérence garantie :**
- L'instance passe par `recovering` (état intermédiaire visible) avant de revenir `running`.
- La **durée de location** (`rental.end_time`) est conservée : l'utilisateur ne perd pas de temps.
- Si aucun worker n'est disponible, l'instance **reste `recovering`** (pas de `running` mensonger).

---

## 3. Les tests (`tests/test_recovery.py`) — 5 tests

| Test | Ce qu'il prouve |
|---|---|
| `test_mark_stale_worker_offline` | un worker sans heartbeat récent passe OFFLINE |
| `test_fresh_worker_stays_available` | un worker avec heartbeat récent reste AVAILABLE |
| `test_recover_moves_instance_to_other_worker` | l'instance d'un worker OFFLINE repart sur un autre worker (nouveau conteneur) |
| `test_recover_without_target_stays_recovering` | sans autre worker, l'instance reste `recovering` |
| `test_full_scenario_halt_worker1` | **scénario prof** : halt worker1 → OFFLINE → instance sur worker2 |

L'agent est **mocké** (fixture `fake_agent`) : on teste toute la logique de reprise sans vrai
conteneur Docker.

---

## 4. Comment tester
```bash
pip install -r requirements-dev.txt
pytest -v          # 33 passed (5 résilience + 13 location + 8 auth + 7 modèles)
```

Extrait du scénario testé :
```python
# instance sur worker1, worker1 ne donne plus de heartbeat (= vagrant halt worker1)
mark_stale_workers_offline()      # worker1 -> OFFLINE
recover_instances()               # instance recréée sur worker2
assert inst.worker_id == worker2.id and inst.status == "running"
```

---

## 5. Preuve obtenue
- **Scénario prof reproduit** (en test) : `vagrant halt worker1` → worker1 OFFLINE → l'instance
  repart bien sur **worker2**, avec un nouveau conteneur et un nouveau port.
- **CI verte** (33 tests).

---

## 6. Ce qu'il reste pour le test réel (démo)
Le `docker kill` / `vagrant halt worker1` **sur l'infra réelle** nécessite :
- le **heartbeat réel** de P1 (`POST /workers/heartbeat` qui alimente `last_heartbeat`) ;
- l'**agent réel** de P3 (`POST /containers`) pour recréer le conteneur ;
- un **déclencheur périodique** (watchdog / scheduler) qui appelle `mark_stale_workers_offline()`
  puis `recover_instances()` toutes les quelques secondes.

Ma logique de reprise est prête et branchée sur la couture agent : dès que le heartbeat et l'agent
réels sont là, le scénario tourne sur les VM sans changer mon code.
