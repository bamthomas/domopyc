# coding=utf-8
from datetime import datetime
from json import loads
import logging
import asyncio
import xml.etree.cElementTree as ET

import serial
import asyncio_redis
from current_cost.iso8601_json import with_iso8601_date
from serial import FileLike


__author__ = 'bruno'
CURRENT_COST = 'current_cost'

logging.basicConfig(format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
LOGGER = logging.getLogger('current_cost')

DEVICE = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'


def now(): return datetime.now()

@asyncio.coroutine
def create_redis_pool():
    connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=4)
    return connection


class AsyncRedisSubscriber(object):
    infinite_loop = lambda i: True
    wait_value = lambda n: lambda i: i < n

    def __init__(self, redis_conn, message_handler, pubsub_key):
        self.pubsub_key = pubsub_key
        self.message_handler = message_handler
        self.redis_conn = redis_conn
        self.subscriber = None
        self.message_loop_task = None
        asyncio.new_event_loop().run_until_complete(self.setup_subscriber())

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


class AsyncCurrentCostReader(FileLike):
    def __init__(self, drv, publisher, event_loop=asyncio.get_event_loop()):
        super().__init__()
        self.event_loop = event_loop
        self.publisher = publisher
        self.serial_drv = drv
        self.event_loop.add_reader(self.serial_drv.fd, self.read_callback)

    def read_callback(self):
        line = self.readline()
        if line:
            try:
                xml_data = ET.fromstring(line)
                power_element = xml_data.find('ch1/watts')
                if power_element is not None:
                    power = int(power_element.text)
                    asyncio.async(self.publisher.handle({'date': now().isoformat(), 'watt': power,
                                  'temperature': float(xml_data.find('tmpr').text)}))
            except ET.ParseError as xml_parse_error:
                LOGGER.exception(xml_parse_error)

    def read(self, bytes=1):
        return self.serial_drv.read(bytes)

    def remove_reader(self):
        self.event_loop.remove_reader(self.serial_drv.fd)

if __name__ == '__main__':
    serial_drv = serial.Serial(DEVICE, baudrate=57600,
                          bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                          timeout=10)

    class LoggingPublisher(object):
            @asyncio.coroutine
            def handle(self, event):
                LOGGER.info(event)
    reader = AsyncCurrentCostReader(serial_drv, LoggingPublisher())

    asyncio.get_event_loop().run_forever()