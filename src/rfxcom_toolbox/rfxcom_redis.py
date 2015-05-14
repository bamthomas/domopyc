from datetime import datetime
import logging
import asyncio
from statistics import mean

from asyncio_redis.protocol import ZScoreBoundary
from current_cost.sensor.current_cost_async import AsyncRedisSubscriber
from daq import rfxcom_emiter_receiver
import asyncio_redis


root = logging.getLogger()
logging.basicConfig()
root.setLevel(logging.INFO)

logger = logging.getLogger('rfxcom')


def now(): return datetime.now()


@asyncio.coroutine
def create_redis_pool():
    connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=4)
    return connection


class RedisTimeCappedSubscriber(object):
    def __init__(self, redis_conn, indicator_name, max_data_age_in_seconds=0, pubsub_key=rfxcom_emiter_receiver.RFXCOM_KEY,
                 indicator_key='temperature'):
        self.indicator_key = indicator_key
        self.max_data_age_in_seconds = max_data_age_in_seconds
        self.indicator_name = indicator_name
        self.redis_subscriber = AsyncRedisSubscriber(redis_conn, self, pubsub_key)

    @asyncio.coroutine
    def handle(self, message):
        yield from self.redis_subscriber.redis_conn.zadd(self.indicator_name, {str(message[self.indicator_key]): message['date'].timestamp()})
        if self.max_data_age_in_seconds:
            yield from self.redis_subscriber.redis_conn.zremrangebyscore(self.indicator_name, ZScoreBoundary('-inf'),
                                                        ZScoreBoundary(now().timestamp() - self.max_data_age_in_seconds))

    @asyncio.coroutine
    def get_average(self):
        val = yield from self.redis_subscriber.redis_conn.zrange(self.indicator_name, 0, -1)
        d = yield from val.asdict()
        return mean((float(v) for v in list(d))) if d else 0.0

