# AMQP RPC Client

This package provides an easy way to use remote procedure calls in microservice 
architectures. The underlying library is `pika` which is fully written in python.

The client uses events and threads to stop blocking the main thread while waiting
for responses from other services