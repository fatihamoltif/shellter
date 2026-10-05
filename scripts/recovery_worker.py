"""Worker de fond : détection de panne + reprise des instances.

Boucle qui, à intervalle régulier :
  1. passe OFFLINE les workers sans heartbeat récent (mark_stale_workers_offline)
  2. recrée leurs instances actives sur un autre worker (recover_instances)

Rend la détection de panne réelle : couplé au heartbeat des agents, un worker
dont l'agent meurt devient OFFLINE au bout de HEARTBEAT_TIMEOUT_SECONDS et ses
locations sont relancées ailleurs.
"""
import logging
import os
import time

from app import create_app
from app.recovery import mark_stale_workers_offline, recover_instances

logging.basicConfig(level=logging.INFO)

CHECK_INTERVAL = int(os.environ.get("RECOVERY_CHECK_INTERVAL", "15"))


def main():
    app = create_app()
    while True:
        with app.app_context():
            offline = mark_stale_workers_offline()
            if offline:
                logging.info("%s worker(s) passe(s) OFFLINE : %s",
                             len(offline), [w.hostname for w in offline])
                recovered = recover_instances()
                if recovered:
                    logging.info("%s instance(s) recuperee(s)", len(recovered))
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
