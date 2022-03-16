# AMQP RPC Client
[![CodeQL](https://github.com/j-suchard/amqp-rpc-client/actions/workflows/code-analysis.yaml/badge.svg)](https://github.com/j-suchard/amqp-rpc-client/actions/workflows/code-analysis.yaml/badge.svg)
[![OSSAR](https://github.com/j-suchard/amqp-rpc-client/actions/workflows/ossar.yaml/badge.svg)](https://github.com/j-suchard/amqp-rpc-client/actions/workflows/ossar.yaml)
[![Pylint](https://github.com/j-suchard/amqp-rpc-client/actions/workflows/pylint.yaml/badge.svg?branch=main)](https://github.com/j-suchard/amqp-rpc-client/actions/workflows/pylint.yaml)

This library offers a Remote-Procedure-Call client which communicates its messages via a message
broker which uses the AMQPv0-9-1 protocol. 

This library is currently only tested with RabbitMQ since the underlying package `pika` is only 
tested with the RabbitMQ server

## Usage
### General
This AMQP RPC Client uses an extra thread in which it handles data events like new messages or 
sending keep-alive messages. Therefore, your code will continue to execute after sending a message 
without waiting for a response. See the attached examples for how to use the library

### Examples

<details><summary>Create a new client</summary>

```python
from amqp_rpc_client import Client

# The Data Source Name which is used to connect to the message broker. The virtual host currently
# is "/". Special characters need to be url-encoded
AMQP_DSN = 'amqp://<<your-username>>:<<your-password>>@<<your-message-broker-address>>/%2F'

# Create the new client with the data source name
rpc_client = Client(AMQP_DSN)

```

</details>

<details><summary>Send a message to another exchange</summary>

```python
from amqp_rpc_client import Client

# The Data Source Name which is used to connect to the message broker. The virtual host currently
# is "/". Special characters need to be url-encoded
AMQP_DSN = 'amqp://<<your-username>>:<<your-password>>@<<your-message-broker-address>>/%2F'

# The exchange into which the message shall be posted
TARGET_EXCHANGE = 'hello_world'

# Create the new client with the data source name
rpc_client = Client(AMQP_DSN)

# Send a message to the specified exchange
rpc_client.send('my_message_content_string', TARGET_EXCHANGE)
```

</details>

<details><summary>Send a message to another exchange and wait for the answer</summary>

```python
from amqp_rpc_client import Client

# The Data Source Name which is used to connect to the message broker. The virtual host currently
# is "/". Special characters need to be url-encoded
AMQP_DSN = 'amqp://<<your-username>>:<<your-password>>@<<your-message-broker-address>>/%2F'

# The exchange into which the message shall be posted
TARGET_EXCHANGE = 'hello_world'

# Create the new client with the data source name
rpc_client = Client(AMQP_DSN)

# Send a message to the specified exchange. This will return a message id which can be used to wait
# for a response
message_id = rpc_client.send('my_message_content_string', TARGET_EXCHANGE)

# Wait indefinitely and receive the response bytes
response: bytes = rpc_client.await_response(message_id)
```

</details>

<details><summary>Send a message to another exchange and wait for the answer with an timeout</summary>

```python
from amqp_rpc_client import Client

# The Data Source Name which is used to connect to the message broker. The virtual host currently
# is "/". Special characters need to be url-encoded
AMQP_DSN = 'amqp://<<your-username>>:<<your-password>>@<<your-message-broker-address>>/%2F'

# The exchange into which the message shall be posted
TARGET_EXCHANGE = 'hello_world'

# The timeout in seconds as to how long the answer shall be awaited
ANSWER_TIMEOUT: float = 10.0

# Create the new client with the data source name
rpc_client = Client(AMQP_DSN)

# Send a message to the specified exchange. This will return a message id which can be used to wait
# for a response
message_id = rpc_client.send('my_message_content_string', TARGET_EXCHANGE)

# Wait indefinitely and receive the response bytes
response: bytes = rpc_client.await_response(message_id, ANSWER_TIMEOUT)

# Check if a response was received
if response is None:
    print('No response received')
else:
    print(response)
```

</details>

<details><summary>Directly get the response content if it is available</summary>

```python
from amqp_rpc_client import Client

# The Data Source Name which is used to connect to the message broker. The virtual host currently
# is "/". Special characters need to be url-encoded
AMQP_DSN = 'amqp://<<your-username>>:<<your-password>>@<<your-message-broker-address>>/%2F'

# The exchange into which the message shall be posted
TARGET_EXCHANGE = 'hello_world'

# The timeout in seconds as to how long the answer shall be awaited
ANSWER_TIMEOUT: float = 10.0

# Create the new client with the data source name
rpc_client = Client(AMQP_DSN)

# Send a message to the specified exchange. This will return a message id which can be used to wait
# for a response
message_id = rpc_client.send('my_message_content_string', TARGET_EXCHANGE)

# Try to get the response
response: bytes = rpc_client.get_response(message_id)

# Check if a response was received
if response is None:
    print('No response received')
else:
    print(response)
```

</details>
