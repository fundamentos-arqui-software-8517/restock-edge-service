import json
import logging
import os

from dotenv import load_dotenv
from paho.mqtt import client as mqtt_client

# Loads environment variables from a .env file if it exists, to configure the MQTT client.
load_dotenv()

# Define the topics which the app will subscribe
SUBSCRIPTIONS = [
    "stores/+/telemetry/weight",
    "stores/+/telemetry/environment",
    "stores/+/health"
]



def on_message(client, userdata, msg):
    """
    Method to handle incoming MQTT messages.
    In this, depending on the device topic, the message is processed accordingly to its correspondent context.

    :param client: The MQTT client
    :param userdata: The user data
    :param msg: The MQTT message received, containing the topic and the payload
    """

    try:
        topic_parts = msg.topic.split("/")

        if len(topic_parts) < 3:
            logging.warning("Invalid MQTT topic: %s", msg.topic)
            return

        device_topic = topic_parts[2]

        match device_topic:
            case "telemetry":
                from tracking.interfaces.mqtt_services import on_tracking_telemetry_message
                on_tracking_telemetry_message(msg, topic_parts)

            case "health":
                logging.info("Health message received from topic %s", msg.topic)

            case _:
                logging.warning("Unknown MQTT topic: %s", msg.topic)
            
    except Exception as ex:
        logging.exception("Error while processing MQTT message: %s", ex)


def on_connect(client, userdata, flags, rc, properties=None):
    """
    Function that triggers when the client connects to the broker.

    :param client: The MQTT client.
    :param userdata: The user data.
    :param flags: The connection flags.
    :param rc: The return code.
    :param properties: The properties.
    """

    if rc != 0:
        logging.error("MQTT error detected for response code %s",rc)
        return

    logging.info("Connected to MQTT Broker! Subscribing to topics:")

    for topic in SUBSCRIPTIONS:
        client.subscribe(topic, qos=1)
        logging.info("Subscribed to topic %s",topic)


def on_disconnect(client, userdata, flags, rc, properties=None):
    """
    Function that triggers when the client disconnects from the broker.

    :param properties: The properties.
    :param client: The MQTT client.
    :param userdata: The user data.
    :param flags: The disconnection flags.
    :param rc: The return code.
    """

    logging.info("Disconnected from MQTT Broker with response code %s", rc)


class MQTTClient:
    """
    Class to handle the MQTT client.

    Attributes:
        host (str): The MQTT broker host.
        port (int): The MQTT broker port.
        connected (bool): Flag indicating whether the client is connected.
        client (mqtt_client.Client): The MQTT client instance.
    """

    def __init__(self):
        """
        Initializes the MQTTClient with the given configuration.
        """

        self.host = os.getenv('MQTT_HOST')
        self.port = int(os.getenv('MQTT_PORT', '1883').strip(''))
        self.connected = False
        self.client = mqtt_client.Client(
            client_id=os.getenv('MQTT_CLIENT_ID'),
            callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,
        )

        self.configure()

    def configure(self):
        """
        Configures the MQTT client with the necessary callbacks and authentication.
        """

        self.client.username_pw_set(os.getenv('MQTT_USERNAME'), os.getenv('MQTT_PASSWORD')) # Only if the broker is configured with authentication
        self.client.on_connect = on_connect
        self.client.on_message = on_message
        self.client.on_disconnect = on_disconnect

    def connect(self):
        """
        Connects to the MQTT broker and starts the loop to listen for messages.
        This also subscribes to the specified topics in the configuration.
        """

        if self.connected:
            return

        self.client.connect(self.host, self.port)
        self.client.loop_start()
        self.connected = True

        logging.info(
            "Connected to MQTT at %s:%s",
            self.host,
            self.port
        )

    def publish(self, topic, payload, qos=1):
        """
        Function to publish a message to a specified topic.

        :param topic: The topic to publish the message to.
        :param payload: The message to be published.
        :param qos: The quality of service level.
        """

        self.client.publish(topic, json.dumps(payload), qos=qos)


# A singleton instance of the MQTTClient
mqtt_service = MQTTClient()


def init_mqtt_client():
    """ Initializes the MQTT client."""
    if os.getenv('USE_MQTT') != 'true':
        return

    mqtt_service.connect()
    logging.info("MQTT Client Initialized")


def shutdown_mqtt_client():
    """ Shuts down the MQTT client. """
    if os.getenv('USE_MQTT') != 'true':
        return

    mqtt_service.client.disconnect()
    mqtt_service.client.loop_stop()
    mqtt_service.connected = False
    logging.info("MQTT Client Shutdown")
