# coding=utf-8
import asyncio
from asyncio import Queue
from socket import socketpair
import functools


def async_coro(f):
    def wrap(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            coro = asyncio.coroutine(f)
            future = coro(*args, **kwargs)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(future)
        return wrapper
    return wrap(f)


class DummySerial(object):
    def __init__(self):
        self.internal_sock, self.serial = socketpair()
        self.fd = self.internal_sock
        self.internal_sock.settimeout(2)
        self.serial.settimeout(2)

    def read(self, bytes=1):
        return self.internal_sock.recv(bytes)

    def write(self, data):
        self.internal_sock.send(data)

    def close(self):
        self.internal_sock.close()
        self.serial.close()


class TestMessageHandler(object):
    queue = Queue()

    @asyncio.coroutine
    def handle(self, message):
        yield from self.queue.put(message)


class QueuePublisher(object):
    queue = Queue()

    @asyncio.coroutine
    def publish(self, event):
        yield from self.queue.put(event)


class TestExceptionMessageHandler(object):
    queue = Queue()

    @asyncio.coroutine
    def handle(self, message):
        yield from self.queue.put(message)
        raise Exception("an exception occured in handle message")