*****
Usage
*****

This chapter will contain information about how to use the server and
what things are necessary to be able to use it.


AMQP Connection Properties
==========================

For successfully starting a server you need to create a Data Source Name pointing to the message
broker. The data source name should contain credentials for connecting to the message broker. If
you do not supply credentials with the data source name the underlying :mod:`pika` package will use
``guest`` as username and password.

.. code-block:: python

    AMQP_DSN = 'amqp://<<your-username>>:<<your-password>>@<<message-broker-host>>:<<port>>/%2F'
    """A schema for a valid AMQP Data Source Name"""

    AMQP_EXCHANGE_NAME = '<<your-exchange-name>>'
    """The your exchange name into which the messages will be published"""

Full example
============

This example will demonstrate how a complete code artifact will look, if you create a new server

.. code-block:: python

    import logging
    import time

    from amqp_rpc_client import Client

    AMQP_DSN = "amqp://<<your-username>>:<<your-password>>@<<message-broker-host>>:<<port>>/%2F"
    """The Data Source Name pointing to the message broker which should contain credentials"""

    EXCHANGE_NAME = "example-exchange"
    """The name of the exchange into which the rpc client publishes its messages""


    # Protect the script part of the application from being executed during imports
    if __name__ == "__main__":

        logging.basicConfig(
            level=logging.DEBUG,
            format='%(levelname)s - %(asctime)s %(name)s - %(funcName)s - %(lineno)s : %(message)s'
        )

        # Create a new rpc client
        rpc_client = Client(
            AMQP_DSN
        )

        while True:
            try:
                time.sleep(0.5)
                rpc_client.send('hello', EXCHANGE_NAME)
            except KeyboardInterrupt:
                # Stop the server if CTRL-C as sent to the python interpreter
                break
