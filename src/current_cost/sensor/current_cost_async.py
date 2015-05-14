# coding=utf-8
from datetime import datetime, timedelta
from daq.current_cost_sensor import AsyncCurrentCostReader, DEVICE
from functools import reduce
from json import loads, dumps
import logging
import asyncio

import serial
from iso8601_json import with_iso8601_date, Iso8601DateEncoder


__author__ = 'bruno'
CURRENT_COST = 'current_cost'

logging.basicConfig(format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
LOGGER = logging.getLogger('current_cost')


def now(): return datetime.now()


class AsyncRedisSubscriber(object):
    infinite_loop = lambda i: True
    wait_value = lambda n: lambda i: i < n

    def __init__(self, redis_conn, message_handler, pubsub_key):
        self.pubsub_key = pubsub_key
        self.message_handler = message_handler
        self.redis_conn = redis_conn
        self.subscriber = None
        self.message_loop_task = None
        asyncio.async(self.setup_subscriber())

    @asyncio.coroutine
    def setup_subscriber(self):
        self.subscriber = yield from self.redis_conn.start_subscribe()
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


class MysqlAverageMessageHandler(AverageMessageHandler):
    CREATE_TABLE_SQL = '''CREATE TABLE IF NOT EXISTS `current_cost` (
                            `id` mediumint(9) NOT NULL AUTO_INCREMENT,
                            `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            `watt` int(11) DEFAULT NULL,
                            `minutes` int(11) DEFAULT NULL,
                            `nb_data` int(11) DEFAULT NULL,
                            `temperature` float DEFAULT NULL,
                            PRIMARY KEY (`id`)
                            ) ENGINE=MyISAM DEFAULT CHARSET=utf8'''

    def __init__(self, db, average_period_minutes=0, loop=asyncio.get_event_loop()):
        super(MysqlAverageMessageHandler, self).__init__(average_period_minutes)
        self.db = db
        self.loop = loop
        asyncio.async(self.setup_db())

    @asyncio.coroutine
    def setup_db(self):
        with (yield from self.db) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute(MysqlAverageMessageHandler.CREATE_TABLE_SQL)
            yield from cur.fetchone()
            yield from cur.close()

    @asyncio.coroutine
    def save(self, average_message):
        with (yield from self.db) as conn:
            cursor = yield from conn.cursor()
            yield from cursor.execute(
                'INSERT INTO current_cost (timestamp, watt, minutes, nb_data, temperature) values (\'%s\', %s, %s, %s, %s) ' % (
                    average_message['date'].strftime('%Y-%m-%d %H:%M:%S'), average_message['watt'], average_message['minutes'],
                    average_message['nb_data'],
                    average_message['temperature']))
            yield from cursor.close()


if __name__ == '__main__':
    serial_drv = serial.Serial(DEVICE, baudrate=57600,
                               bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                               timeout=10)

    class LoggingPublisher(object):
        def handle(self, event):
            LOGGER.info(event)

    reader = AsyncCurrentCostReader(serial_drv, LoggingPublisher())

    asyncio.get_event_loop().run_forever()
