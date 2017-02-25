""" Messaging module

Us to send messages between process and thread
"""

import abc
import queue

class Messaging(object):
    """ Message class """

    def __init__(self, handler=None):
        self._handler = handler

    def send(self, message):
        """ Send a message to all the listener """
        if not self._handler:
            raise ValueError("No handler configured")

        self._handler.send(message)

    def listen(self):
        """ Listen for incomming messages """

        if not self._handler:
            raise ValueError("No handler configured")

        yield from self._handler.listen()

    def set_handler(self, handler):
        """ Set the handler to use """

        self._handler = handler

    def stop(self):
        """ Stop the message listener """

        if not self._handler:
            raise ValueError("No handler configured")

        self._handler.stop()


class Handler(metaclass=abc.ABCMeta):
    """ Abstract class for creating new handler """

    @abc.abstractmethod
    def send(self, _message):
        """ How the handler handle the message delivery """

    @abc.abstractmethod
    def listen(self):
        """ How the handler listen for incomming message """


class PythonHandler(Handler):
    """ Python handler use when using the server in only one process """

    def __init__(self):
        self._queue = queue.Queue()

    def send(self, message):
        """ Send the message to the queue """

        self._queue.put(message)

    def listen(self):
        """ Process message from the queue """

        while True:
            message = self._queue.get()
            if message is None:
                break

            yield message
            self._queue.task_done()

    def stop(self):
        """ Stop the listener by adding a None element to the queue """

        self._queue.put(None)


_MESSAGING = Messaging()

def set_handler(handler):
    """ Add an handler to the global message class """

    _MESSAGING.set_handler(handler)

def send(message):
    """ Send a message with the global message class """

    _MESSAGING.send(message)

def listen():
    """ Listen for message with the global message class """

    yield from _MESSAGING.listen()


def stop():
    """ Stop to listen """

    _MESSAGING.stop()
