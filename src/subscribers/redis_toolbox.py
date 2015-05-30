# coding=utf-8
from datetime import datetime, timedelta
from statistics import mean
from json import loads, dumps
import logging
import asyncio
import time

from asyncio_redis import ZScoreBoundary
import asyncio_redis
from daq import rfxcom_emiter_receiver
from daq.current_cost_sensor import AsyncCurrentCostReader, DEVICE
from functools import reduce
import serial
from iso8601_json import with_iso8601_date, Iso8601DateEncoder


__author__ = 'bruno'
CURRENT_COST = 'current_cost'

logging.basicConfig(format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
LOGGER = logging.getLogger('current_cost')


now = datetime.now


@asyncio.coroutine
def create_redis_pool():
    connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=4)
    return connection


class AsyncRedisSubscriber(object):
    infinite_loop = lambda i: True
    wait_value = lambda n: lambda i: i < n

    def __init__(self, pubsub_conn, message_handler, pubsub_key):
        self.pubsub_key = pubsub_key
        self.message_handler = message_handler
        self.pubsub_conn = pubsub_conn
        self.subscriber = None
        self.message_loop_task = None
        asyncio.new_event_loop().run_until_complete(self.setup_subscriber())

    @asyncio.coroutine
    def setup_subscriber(self):
        self.subscriber = yield from self.pubsub_conn.start_subscribe()
        yield from self.subscriber.subscribe([self.pubsub_key])

    def start(self, for_n_messages=0):
        predicate = AsyncRedisSubscriber.infinite_loop if for_n_messages == 0 else AsyncRedisSubscriber.wait_value(
            for_n_messages)
        self.message_loop_task = asyncio.async(self.message_loop(predicate))
        return self

    @asyncio.coroutine
    def message_loop(self, predicate):
        i = 0
        while predicate(i):
            i += 1
            message_str = yield from self.subscriber.next_published()
            message = loads(message_str.value, object_hook=with_iso8601_date)
            yield from self.message_handler.handle(message)


class AverageMessageHandler(object):
    def __init__(self, average_period_minutes=0):
        self.delta_minutes = timedelta(minutes=average_period_minutes)
        self.next_save_date = average_period_minutes == 0 and now() or self.next_plain(average_period_minutes, now())
        self.messages = []

    @staticmethod
    def next_plain(minutes, dt):
        return dt - timedelta(minutes=dt.minute % minutes - minutes, seconds=dt.second, microseconds=dt.microsecond)

    def handle(self, json_message):
        message = loads(json_message, object_hook=with_iso8601_date)
        self.messages.append(message)
        if now() >= self.next_save_date:
            average_json_message = self.get_average_json_message(message['date'])
            self.next_save_date = self.next_save_date + self.delta_minutes
            self.messages = []
            return asyncio.async(self.save(average_json_message))

    def get_average_json_message(self, date):
        watt_and_temp = map(lambda msg: (msg['watt'], msg['temperature']), self.messages)

        def add_tuple(x_t, y_v):
            x, t = x_t
            y, v = y_v
            return x + y, t + v

        watt_sum, temp_sum = reduce(add_tuple, watt_and_temp)
        nb_messages = len(self.messages)
        return {'date': date, 'watt': watt_sum / nb_messages, 'temperature': temp_sum / nb_messages,
                'nb_data': nb_messages, 'minutes': int(self.delta_minutes.total_seconds() / 60)}

    @asyncio.coroutine
    def save(self, average_message):
        raise NotImplementedError


class RedisAverageMessageHandler(AverageMessageHandler):
    def __init__(self, db, average_period_minutes=0):
        super(RedisAverageMessageHandler, self).__init__(average_period_minutes)
        self.redis_conn = db

    @asyncio.coroutine
    def save(self, average_message):
        key = 'current_cost_%s' % average_message['date'].strftime('%Y-%m-%d')
        lpush_return = yield from self.redis_conn.lpush(key, [dumps(average_message, cls=Iso8601DateEncoder)])
        if lpush_return == 1:
            yield from self.redis_conn.expire(key, 5 * 24 * 3600)


class RedisTimeCappedSubscriber(AsyncRedisSubscriber):
    def __init__(self, redis_conn, indicator_name, max_data_age_in_seconds=0,
                 pubsub_key=rfxcom_emiter_receiver.RFXCOM_KEY,
                 indicator_key='temperature'):
        super().__init__(redis_conn, self, pubsub_key)
        self.indicator_key = indicator_key
        self.max_data_age_in_seconds = max_data_age_in_seconds
        self.indicator_name = indicator_name

    @asyncio.coroutine
    def handle(self, message):
        yield from self.pubsub_conn.zadd(self.indicator_name,
                                        {str(message[self.indicator_key]): message['date'].timestamp()})
        if self.max_data_age_in_seconds:
            yield from self.pubsub_conn.zremrangebyscore(self.indicator_name, ZScoreBoundary('-inf'),
                                                        ZScoreBoundary(
                                                            now().timestamp() - self.max_data_age_in_seconds))

    @asyncio.coroutine
    def get_average(self):
        val = yield from self.pubsub_conn.zrange(self.indicator_name, 0, -1)
        d = yield from val.asdict()
        return mean((float(v) for v in list(d))) if d else 0.0

    @asyncio.coroutine
    def get_data(self, conn, since_seconds=60):
        t = yield from conn.zrangebyscore(self.indicator_name,
                                                            ZScoreBoundary(now().timestamp() - since_seconds),
                                                            ZScoreBoundary(now().timestamp()))
        data_set = yield from t.asdict()
        return list(map(lambda value: {self.indicator_key: int(value)}, list(data_set)))



if __name__ == '__main__':
    serial_drv = serial.Serial(DEVICE, baudrate=57600,
                               bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                               timeout=10)

    class LoggingPublisher(object):
        def handle(self, event):
            LOGGER.info(event)

    reader = AsyncCurrentCostReader(serial_drv, LoggingPublisher())

    asyncio.get_event_loop().run_forever()
