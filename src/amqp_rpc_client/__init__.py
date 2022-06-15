"""An asynchronous RabbitMQ client usable for RPC calls"""
import logging
import secrets
import sys
import threading
import time
import typing

import pika
import pika.exceptions
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties


class Client:
    __messaging_lock = threading.Lock()
    """Lock used to handle the switching between sending and receiving messages"""

    __responses: typing.Dict[str, bytes] = {}
    """Dictionary containing the received messages"""

    __events: typing.Dict[str, threading.Event] = {}
    """Dictionary containing the events which shall be set to true if an message was received"""

    def __init__(
        self,
        amqp_dsn: str,
        client_name: typing.Optional[str] = secrets.token_urlsafe(nbytes=16),
        additional_properties: typing.Optional[typing.Dict[str, str]] = None,
        mute_pika: typing.Optional[bool] = False,
        data_processing_wait_time: typing.Union[float, None] = 0.01,
    ):
        """Initialize a new RPC Client and open the connection to the message broker

        :param amqp_dsn: The Data Source Name pointing to the message broker installation. This
            Data Source Name should contain credentials, if not the standardized credentials (User:
            `guest`, Password: `guest`) will be used for authentication
        :type amqp_dsn: str
        :param client_name: Optional name of the client which will be visible in the management
            platform of the message broker, if the platform supports this
        :type client_name: str, optional
        :param additional_properties: Optional additional client properties which may be set
        :type additional_properties: dict[str, str], optional
        """
        # Get a logger for this client
        self._allow_messages = threading.Event()
        self._stop_event = threading.Event()
        self._data_event_wait_time = data_processing_wait_time
        if additional_properties is None:
            self._additional_properties = {}
        else:
            self._additional_properties = additional_properties
        self._logger = logging.getLogger("amqp_rpc_client")
        # = Check if the Data Source Name is a valid data source name =
        self._logger.debug('Validating the following parameter: "amqp_dsn"')
        # Check if the supplied string is not none
        self._logger.debug("Checking if the parameter is not None")
        if amqp_dsn is None:
            raise ValueError("The amqp_dsn is a required parameter")
        # Check if the supplied string does not contain whitespaces only
        self._logger.debug("Checking if the parameter is not empty")
        if len(amqp_dsn.strip()) == 0:
            raise ValueError("The amqp_dsn may not be an empty string")
        self._amqp_dsn = amqp_dsn
        # = Check finished =
        self._logger.debug('All checks for parameter "amqp_dsn" passed')
        if mute_pika:
            self._logger.debug("Muting the underlying pika library completely")
            logging.getLogger("pika").setLevel("CRITICAL")
        self._connect()
        self._logger.info("Startup process finished. The client may now be used to send messages")

    def _handle_data_events(self):
        """Handle new data events and cancel the communication with the message broker if the
        event was set"""
        # Process some data events from the start on and allow messages to be sent
        self._allow_messages.set()
        try:
            self._channel.start_consuming()
        except pika.exceptions.ConnectionClosed:
            self._logger.warning("The connection between the client and message broker has been closed")

    def _handle_new_message(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        content: bytes,
    ):
        """Handle a new incoming message

        This will add the response to the response dictionary and will set the event to true

        :param channel: The channel used to retrieve the message
        :param method: Information about the delivery
        :param properties: Properties of the message
        :param content: The content of the retrieved message
        """
        # Check if the response contained a correlation id if not reject it and log it
        if not properties.correlation_id:
            self._logger.critical(
                "The received message did not contain a correlation id. This "
                "message is therefore not accepted and will be rejected"
            )
            channel.basic_reject(method.delivery_tag, requeue=False)
        else:
            self._logger.debug("Saving the response body to the message list")
            self.__responses.update({properties.correlation_id: content})
            self._logger.debug("Setting the event correlating to the message to received")
            if self.__events.get(properties.correlation_id) is None:
                self._logger.critical(
                    "Error in the messaging events. Unable to find event associated with this correlation id"
                )
                channel.basic_reject(method.delivery_tag, requeue=True)
            else:
                self.__events.get(properties.correlation_id).set()
                channel.basic_ack(method.delivery_tag)

    def send(self, content: str, exchange: str, routing_key: str = "") -> typing.Union[str, None]:
        """Send a message to the exchange and get the created message id

        :param routing_key: The routing key used to send the message to the right queue [optional for fanout queues]
        :param content: The content which shall be sent to the message broker
        :param exchange:  The exchange in which the message shall be published
        :return: The message id created to identify the request
        """
        # Acquire the messaging lock for the whole operation
        with self.__messaging_lock:
            if not self._connection.is_open:
                # Since the connection was not opened connect again
                self._logger.warning(
                    "WARN_NO_BROKER_CONNECTION - The client was not connected to the message broker. Trying to connect "
                    "to the message broker"
                )
                self._connect()
            # Since sending messages is allowed start by creating a new message id
            message_id = secrets.token_urlsafe(nbytes=32)
            self._logger.debug("Created new message id: %s", message_id)
            # Create a new event signalizing if the message has been received
            self.__events.update({message_id: threading.Event()})
            self._logger.debug("Created new event for the message to be sent")
            # Now check if the channel used to send the message is still open
            if not self._channel.is_open:
                self._logger.warning(
                    "WARN_NO_OPEN_CHANNEL - The channel to the message broker is not open. Trying to reconnect "
                    "to the message broker"
                )
                self._connect()
            if not self._allow_messages.wait(timeout=10.0):
                self._logger.error(
                    "ERR_NO_MESSAGES_ALLOWED - Unable to send messages since the initial connection flow has not "
                    "finished "
                )
                return None
            try:
                self._channel.basic_publish(
                    exchange=exchange,
                    routing_key=routing_key,
                    body=content.encode("utf-8"),
                    properties=pika.BasicProperties(
                        reply_to=self._response_queue_name, correlation_id=message_id, content_encoding="utf-8"
                    ),
                )
                self._logger.debug(
                    "Published the message with the following properties:\nExchange: %s\nRouting "
                    "Key: %s\nCorrelation ID:%s\nBody:%s\n",
                    exchange,
                    routing_key,
                    message_id,
                    content,
                )
            except Exception as e:
                self._logger.exception(
                    "PUBLISH_ERROR - An exception was thrown during the sending of the message", exc_info=e
                )
                raise e
            return message_id

    def get_response(self, message_id: str) -> typing.Optional[bytes]:
        """Get a response from the response list

        This method will try to get the response content from the dictionary of responses.
        If the response is found it will be removed from the response dictionary

        :param message_id: The id of the message which was created during the sending
        :return: The message body if it already has a response else None
        """
        # Check if the response is already available
        self._logger.debug("%s - Checking if the response was already received", message_id)
        response = self.__responses.pop(message_id, None)
        if response is None:
            self._logger.debug("%s - The response for the message has not been received yet", message_id)
        return response

    def await_response(self, message_id: str, timeout: float = None) -> typing.Optional[bytes]:
        """Wait for the response to be handled and return it

        This will remove the response from the list of responses

        :param message_id: The id of the message which was created during the sending process
        :param timeout: Time to wait for the event to be set
        :return: The message if the timeout was not reached
        """
        # Check if the message id is in the event dictionary
        if message_id not in self.__events:
            raise ValueError("%s - A message with this ID has not been sent", message_id)
        self._logger.info("%s - Waiting for the response to the message", message_id)
        # Try to get the event
        message_returned = self.__events.get(message_id)
        if not message_returned.wait(timeout=timeout):
            self._logger.warning(
                "%s - The waiting operation timed out after %s seconds and no " "response was received",
                message_id,
                timeout,
            )
            return None
        self._logger.debug("%s - Found Response for the message", message_id)
        response = self.__responses.pop(message_id, None)
        return response

    def _connect(self):
        # Parse the amqp_dsn into preliminary parameters
        self._connection_parameters = pika.URLParameters(self._amqp_dsn)
        # Create a new connection name which is added to the client properties later on
        self.connection_name = "amqp-rpc-client#" + secrets.token_hex(nbytes=8)
        self._logger.debug("Created connection name for new connection: %s", self.connection_name)
        # Combine the additional client properties with those set manually here
        _client_properties = self._additional_properties | {
            "connection_name": self.connection_name,
            "product": "AMQP-RPC Client",
            "platform": "Python {}".format(sys.version),
            "information": "Licensed under the 3-Clause BSD License. See the LICENSE file "
            "supplied with this library",
            "copyright": "Copyright (c) Jan Eike Suchard",
        }
        self._logger.debug("Setting the following client properties: %s", _client_properties)
        # Set the client properties to the connection parameters
        self._connection_parameters.client_properties = _client_properties
        # Create a new blocking connection
        self._logger.info("Starting the connection to the message broker")
        self._logger.debug("Creating a new BlockingConnection")
        self._connection = pika.BlockingConnection(self._connection_parameters)
        # Open a new channel to the message broker
        self._logger.debug("Opening a new channel with the BlockingConnection")
        self._channel = self._connection.channel()
        # Create a new queue which is exclusive to this client and will be deleted if the client
        # disconnects. This queue is used for reading responses
        self._logger.debug("Declaring a new exclusive auto-deleting queue in the opened channel")
        self._queue = self._channel.queue_declare("", False, False, True, True)
        # Save the name generated by the broker as response queue name
        self._response_queue_name = self._queue.method.queue
        self._logger.info("Connected to the message broker")
        self._consumer = self._channel.basic_consume(
            queue=self._response_queue_name,
            on_message_callback=self._handle_new_message,
            auto_ack=False,
            exclusive=True,
        )
        self._data_event_handler = threading.Thread(target=self._handle_data_events, daemon=True)
        self._stop_handler_watching = threading.Event()
        self._logger.debug("Starting the data handling thread")
        self._data_event_handler.start()

    def _reconnect(self):
        self._connect()

    def stop(self):
        """
        Stop the client and close all connections to the message broker
        """
        # Set the stop event since the thread will handle the disconnection flow
        self._channel.stop_consuming(self._consumer)
