from json import dumps, loads
from queue import Queue, Empty
import unittest
from datetime import datetime, timezone
from current_cost.iso8601_json import Iso8601DateEncoder, with_iso8601_date

import redis
from current_cost.sensor import current_cost
from current_cost.sensor.current_cost import CURRENT_COST, CurrentCostReader

__author__ = 'bruno'


class RedisSubscribeLoopTest(unittest.TestCase):
    def setUp(self):
        class TestMessageHandler(object):
            queue = Queue()
            def handle(self, message):
                self.queue.put(message)
        self.message_handler = TestMessageHandler()
        self.myredis = redis.Redis()
        self.pubsub = self.myredis.pubsub()
        self.subscriber = current_cost.RedisSubscriber(self.myredis, self.message_handler)
        self.subscriber.start()

    def tearDown(self):
        self.subscriber.stop()
        self.subscriber.join()

    def test_subscribe_loop(self):
        expected = {'date': datetime.now().isoformat(), 'watt': '123', 'temperature': '23.4'}

        self.myredis.publish(CURRENT_COST, dumps(expected))

        event = self.message_handler.queue.get()
        self.assertIsNotNone(event)
        self.assertDictEqual(loads(event.decode(encoding='UTF-8')), expected)


class MockSerial():
    def __init__(self): self.readqueue = Queue()
    def readline(self, *args, **kwargs):
        try:
            return self.readqueue.get(block=False)
        except Empty: return None
    def send(self, message): self.readqueue.put(message)
    def close(self):pass


class CurrentCostReaderTest(unittest.TestCase):
    def setUp(self):
        current_cost.now = lambda: datetime(2012, 12, 13, 14, 15, 16)
        self.queue = Queue()
        def publish_func_test(event):
            self.queue.put(event)
        self.mockserial = MockSerial()
        self.current_cost_reader = CurrentCostReader(self.mockserial, publish_func_test)
        self.current_cost_reader.start()

    def tearDown(self):
        self.current_cost_reader.stop()
        self.current_cost_reader.join()

    def test_read_sensor(self):
        self.mockserial.send('<msg><src>CC128-v1.29</src><dsb>00302</dsb><time>02:57:28</time><tmpr>21.4</tmpr><sensor>1</sensor><id>00126</id><type>1</type><ch1><watts>00305</watts></ch1></msg>')

        self.assertDictEqual(self.queue.get(timeout=1), {'date': (current_cost.now().isoformat()), 'watt': 305, 'temperature':21.4})

    def test_read_sensor_xml_error_dont_break_loop(self):
        self.mockserial.send('<malformed XML>')
        self.mockserial.send('<msg><src>CC128-v1.29</src><dsb>00302</dsb><time>02:57:28</time><tmpr>21.4</tmpr><sensor>1</sensor><id>00126</id><type>1</type><ch1><watts>00305</watts></ch1></msg>')

        self.assertDictEqual(self.queue.get(timeout=1), {'date': (current_cost.now().isoformat()), 'watt': 305, 'temperature':21.4})


class AverageMessageHandlerTest(unittest.TestCase):
    def setUp(self):
        current_cost.now = lambda: datetime(2012, 12, 13, 14, 2, 0, tzinfo=timezone.utc)
        self.myredis = redis.Redis()
        self.message_handler = current_cost.RedisAverageMessageHandler(self.myredis, average_period_minutes=10)

    def tearDown(self):
        self.myredis.delete('current_cost_2012-12-13')

    def test_save_event_redis_function(self):
        message_handler_without_period = current_cost.RedisAverageMessageHandler(self.myredis)
        now = datetime(2012, 12, 13, 14, 0, 7, tzinfo=timezone.utc)

        message_handler_without_period.handle(dumps({'date': now, 'watt': 305.0, 'temperature':21.4}, cls=Iso8601DateEncoder))

        self.assertTrue(int(self.myredis.ttl('current_cost_2012-12-13')) <=  5 * 24 * 3600)
        self.assertDictEqual(
            {'date': now, 'watt': 305, 'temperature': 21.4, 'nb_data': 1, 'minutes': 0},
            loads(self.myredis.lpop('current_cost_2012-12-13').decode(), object_hook=with_iso8601_date))

    def test_save_event_redis_function_no_ttl_if_not_first_element(self):
        message_handler_without_period = current_cost.RedisAverageMessageHandler(self.myredis)
        self.myredis.lpush('current_cost_2012-12-13', 'not used')
        message_handler_without_period.handle(dumps({'date': (current_cost.now().isoformat()), 'watt': 305, 'temperature':21.4}))

        self.assertIsNone(self.myredis.ttl('current_cost_2012-12-13'))

    def test_next_plain(self):
        _14h04 = datetime(2012, 12, 13, 14, 4, 0)
        self.assertEquals(datetime(2012, 12, 13, 14, 10), self.message_handler.next_plain(10, _14h04))
        self.assertEquals(datetime(2012, 12, 13, 14, 15), self.message_handler.next_plain(15, _14h04))
        self.assertEquals(datetime(2012, 12, 13, 14, 5 ), self.message_handler.next_plain(5 , _14h04))

    def test_average(self):
        current_cost.now = lambda: datetime(2012, 12, 13, 14, 0, 7, tzinfo=timezone.utc)
        self.message_handler.handle(dumps({'date': current_cost.now(), 'watt': 100, 'temperature':20.0}, cls=Iso8601DateEncoder))
        self.assertEquals(0, self.myredis.llen('current_cost_2012-12-13'))

        current_cost.now = lambda: datetime(2012, 12, 13, 14, 3, 0, tzinfo=timezone.utc)
        self.message_handler.handle(dumps({'date': current_cost.now(), 'watt': 200, 'temperature':30.0}, cls=Iso8601DateEncoder))
        self.assertEquals(0, self.myredis.llen('current_cost_2012-12-13'))

        current_cost.now = lambda: datetime(2012, 12, 13, 14, 10, 0, 1, tzinfo=timezone.utc)
        self.message_handler.handle(dumps({'date': current_cost.now(), 'watt': 900, 'temperature':10.0}, cls=Iso8601DateEncoder))

        self.assertEqual({'date': current_cost.now(), 'watt': 400.0, 'temperature':20.0, 'nb_data': 3, 'minutes': 10},
            loads(self.myredis.lpop('current_cost_2012-12-13').decode(), object_hook=with_iso8601_date))