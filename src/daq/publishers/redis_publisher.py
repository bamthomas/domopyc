# coding=utf-8
import asyncio
from json import dumps


class RedisPublisher(object):

    def __init__(self, redis_conn, key):
        self.key = key
        self.redis_conn = redis_conn

    @asyncio.coroutine
    def publish(self, event):
        yield from self.redis_conn.publish(self.key, dumps(event))
