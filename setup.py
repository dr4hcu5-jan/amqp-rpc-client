from setuptools import setup

setup(
    name='amqp-rpc-client',
    version='1.0.0',
    packages=['amqp_rpc_client'],
    url='',
    license='BSD-3-Clause',
    author='Jan Eike Suchard',
    author_email='jan-eike.suchard@magenta.de',
    description='An Event-based asynchronous AMQP client working with RabbitMQ',
    install_requires=['pika~=1.2.0']
)
