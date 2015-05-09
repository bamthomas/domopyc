from asyncio import Queue
import asyncio
import logging
from json import dumps, loads
import unittest
from datetime import datetime, timezone
import xml.etree.cElementTree as ET

import functools
import asyncio_redis
from current_cost.iso8601_json import Iso8601DateEncoder, with_iso8601_date


logging.basicConfig(format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
LOGGER = logging.getLogger('current_cost')

__author__ = 'bruno'

DEVICE = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'


@asyncio.coroutine
def create_redis_pool():
    connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=4)
    return connection


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


class WithRedis(unittest.TestCase):
    @asyncio.coroutine
    def setUp(self):
        self.connection = yield from create_redis_pool()
        yield from self.connection.flushdb()

    @asyncio.coroutine
    def tearDown(self):
        self.connection.close()


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


def now():
    return datetime.now()


class AsyncCurrentCostReader(object):
    def __init__(self, serial_drv, publisher, event_loop=asyncio.get_event_loop()):
        self.stop_asked = False
        self.event_loop = event_loop
        self.publisher = publisher
        self.serial_drv = serial_drv
        self.create_transport()

    def create_transport(self):
        self.event_loop.add_reader(self.serial_drv, self.read)

    def start(self):
        self.read()

    @asyncio.coroutine
    def read(self):
        while not self.stop_asked:
            line = self.serial_drv.readline()
            if line:
                try:
                    xml_data = ET.fromstring(line)
                    power_element = xml_data.find('ch1/watts')
                    if power_element is not None:
                        power = int(power_element.text)
                        self.publisher.handle({'date': now().isoformat(), 'watt': power,
                                      'temperature': float(xml_data.find('tmpr').text)})
                except ET.ParseError as xml_parse_error:
                    LOGGER.exception(xml_parse_error)

    def stop(self):
        self.stop_asked = True


class RedisSubscribeLoopTest(WithRedis):
    @async_coro
    def setUp(self):
        yield from super().setUp()

        class TestMessageHandler(object):
            queue = Queue()

            @asyncio.coroutine
            def handle(self, message):
                yield from self.queue.put(message)

        self.message_handler = TestMessageHandler()
        self.subscriber = AsyncRedisSubscriber(self.connection, self.message_handler, 'key')

    @async_coro
    def test_subscribe_loop(self):
        self.subscriber.start(1)
        expected = {'date': datetime.now(timezone.utc), 'watt': '123'}

        yield from self.connection.publish('key', dumps(expected, cls=Iso8601DateEncoder))

        event = yield from asyncio.wait_for(self.message_handler.queue.get(), 2)
        self.assertDictEqual(event, expected)


class MockSerial():
    def __init__(self):
        self.readqueue = Queue()

    @asyncio.coroutine
    def readline(self, *args, **kwargs):
        try:
            event = yield from self.readqueue.get(block=0)
            return event
        except asyncio.queues.QueueEmpty:
            return None

    @asyncio.coroutine
    def send(self, message):
        yield from self.readqueue.put(message)

    def close(self):
        pass


class CurrentCostReaderTest(unittest.TestCase):
    def setUp(self):
        now = lambda: datetime(2012, 12, 13, 14, 15, 16)
        self.queue = Queue()

        class TestPublisher(object):
            @asyncio.coroutine
            def handle(self, event):
                yield from self.queue.put(event)
        class AsyncCurrentCostReaderWithoutFileDescriptor(AsyncCurrentCostReader):
            def create_transport(self):
                pass

        self.mockserial = MockSerial()
        self.current_cost_reader = AsyncCurrentCostReaderWithoutFileDescriptor(self.mockserial, TestPublisher())
        self.current_cost_reader.start()

    def tearDown(self):
        self.current_cost_reader.stop()

    def test_read_sensor(self):
        self.mockserial.send(
            '<msg><src>CC128-v1.29</src><dsb>00302</dsb><time>02:57:28</time><tmpr>21.4</tmpr><sensor>1</sensor><id>00126</id><type>1</type><ch1><watts>00305</watts></ch1></msg>')

        event = yield from self.queue.get()
        self.assertDictEqual(event, {'date': (now().isoformat()), 'watt': 305, 'temperature': 21.4})

    def test_read_sensor_xml_error_dont_break_loop(self):
        self.mockserial.send('<malformed XML>')
        self.mockserial.send(
            '<msg><src>CC128-v1.29</src><dsb>00302</dsb><time>02:57:28</time><tmpr>21.4</tmpr><sensor>1</sensor><id>00126</id><type>1</type><ch1><watts>00305</watts></ch1></msg>')

        event = yield from self.queue.get()
        self.assertDictEqual(event, {'date': (now().isoformat()), 'watt': 305, 'temperature': 21.4})
