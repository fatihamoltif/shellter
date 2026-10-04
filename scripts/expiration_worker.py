import logging
import os
import time

from app import create_app
from app.expiration_manager import expire_due_rentals


logging.basicConfig(level=logging.INFO)

CHECK_INTERVAL = int(
    os.environ.get("EXPIRATION_CHECK_INTERVAL", "10")
)


def main():
    app = create_app()

    while True:
        with app.app_context():
            count = expire_due_rentals()

            if count:
                logging.info(
                    "%s location(s) expirée(s)",
                    count,
                )

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()