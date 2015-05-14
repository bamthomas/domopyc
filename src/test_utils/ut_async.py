# coding=utf-8
import asyncio
from asyncio import Queue
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


class TestMessageHandler(object):
    queue = Queue()
    @asyncio.coroutine
    def handle(self, message):
        yield from self.queue.put(message)