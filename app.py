"""Flask application entry point for the Restock Edge Service.

This module wires together the Flask application, registers the IAM and
Tracking bounded-context Blueprints, and ensures the SQLite database is
initialized when the application starts.

Typical usage::

    flask --app app run
    # or
    python app.py
"""
import atexit
import logging
import signal
import threading

from flask import Flask

import iam.application.services
from devices.interfaces.services import devices_api
from iam.interfaces.services import iam_api
from shared.infrastructure.database import init_db
from shared.infrastructure.mqtt_client import shutdown_mqtt_client, init_mqtt_client
from tracking.interfaces.rest_services import tracking_api

# The Flask application instance.
app = Flask(__name__)

# Configure logging.
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)

# Lock to ensure that shutdown is only called once.
_shutdown_lock = threading.Lock()
_shutdown_done = False


def shutdown_app():
    """ Shuts down the application. """
    global _shutdown_done

    with _shutdown_lock:
        if _shutdown_done:
            return

        _shutdown_done = True

        try:
            shutdown_mqtt_client()
        except Exception as e:
            logging.exception(f"Error during shutdown: {e}")


def signal_handler(signum, frame):
    """ Handles SIGINT and SIGTERM signals to gracefully shut down the application. """
    app.logger.info(f"Received signal {signum}, shutting down server...")
    shutdown_app()

# The IAM bounded-context Blueprint is registered first to ensure its authentication logic is available
app.register_blueprint(iam_api)

# The Tracking bounded-context Blueprint is registered next, followed by the Devices Blueprint.  This ordering allows the Tracking endpoints to delegate authentication to the IAM service before processing device-related requests.
app.register_blueprint(tracking_api)

# The Devices bounded-context Blueprint is registered last, as it may depend on authentication and tracking logic provided by the previously registered Blueprints.  This ordering ensures that all necessary services are available when handling device-related API requests.
app.register_blueprint(devices_api)


def setup():
    """Initialize the database and seed a test device.

    Side effects:
        - Creates the SQLite database file (``restock_edge.db``) if absent.
        - Creates ``devices`` and ``weight_records`` tables when they do not
          exist yet.
        - Inserts the default test device if it has not been created previously.
    """
    init_db()
    init_mqtt_client()
    auth_application_service = iam.application.services.AuthApplicationService()
    auth_application_service.get_or_create_test_device()

# Register the shutdown function to be called when the program exits.
atexit.register(shutdown_app)

# Register the signal handler for SIGINT and SIGTERM.
signal.signal(signal.SIGINT, signal_handler)  # Closing process in the terminal
signal.signal(signal.SIGTERM, signal_handler)  # Closing process in Docker


setup()


if __name__ == "__main__":
    logging.info(app.url_map)
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
