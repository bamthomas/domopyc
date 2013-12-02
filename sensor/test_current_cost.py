from Queue import Queue, Empty
from json import dumps, loads
import unittest
from current_cost import CURRENT_COST, CurrentCostReader
from datetime import datetime
import current_cost
import redis

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
        self.assertDictEqual(loads(event), expected)

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

class AverageMessageHandlerTestWithoutAverage(unittest.TestCase):
    def setUp(self):
        self.myredis = redis.Redis()
        self.message_handler = current_cost.RedisAverageMessageHandler(self.myredis)

    def tearDown(self):
        self.myredis.delete('current_cost_2012-12-13')

    def test_save_event_redis_function(self):
        self.message_handler.handle(dumps({'date': '2012-12-13T21:59:10', 'watt': 305, 'temperature':21.4}))

        self.assertTrue(int(self.myredis.ttl('current_cost_2012-12-13')) <=  5 * 24 * 3600)
        self.assertEqual(dumps({'date': '2012-12-13T21:59:10', 'watt': 305, 'temperature':21.4, 'nb_data': 1, 'minutes': 0}),
            self.myredis.lpop('current_cost_2012-12-13'))

    def test_save_event_redis_function_no_ttl_if_not_first_element(self):
        self.myredis.lpush('current_cost_2012-12-13', 'not used')
        self.message_handler.handle(dumps({'date': (current_cost.now().isoformat()), 'watt': 305, 'temperature':21.4}))

        self.assertIsNone(self.myredis.ttl('current_cost_2012-12-13'))

class AverageMessageHandlerTest(unittest.TestCase):
    def setUp(self):
        current_cost.now = lambda: datetime(2012, 12, 13, 14, 2, 0)
        self.myredis = redis.Redis()
        self.message_handler = current_cost.RedisAverageMessageHandler(self.myredis, average_period_minutes=10)

    def tearDown(self):
        self.myredis.delete('current_cost_2012-12-13')

    def test_next_plain(self):
        _14h04 = datetime(2012, 12, 13, 14, 4, 0)
        self.assertEquals(datetime(2012, 12, 13, 14, 10), self.message_handler.next_plain(10, _14h04))
        self.assertEquals(datetime(2012, 12, 13, 14, 15), self.message_handler.next_plain(15, _14h04))
        self.assertEquals(datetime(2012, 12, 13, 14, 5 ), self.message_handler.next_plain(5 , _14h04))

    def test_average(self):
        self.message_handler.handle(dumps({'date': '2012-12-13T14:00:07', 'watt': 100, 'temperature':20.0}))
        self.assertEquals(0, self.myredis.llen('current_cost_2012-12-13'))

        current_cost.now = lambda: datetime(2012, 12, 13, 14, 3, 0)
        self.message_handler.handle(dumps({'date': '2012-12-13T14:03:07', 'watt': 200, 'temperature':30.0}))
        self.assertEquals(0, self.myredis.llen('current_cost_2012-12-13'))

        current_cost.now = lambda: datetime(2012, 12, 13, 14, 10, 0, 1)
        self.message_handler.handle(dumps({'date': '2012-12-13T14:10:07', 'watt': 900, 'temperature':10.0}))

        self.assertEqual(dumps({'date': '2012-12-13T14:10:07', 'watt': 400, 'temperature':20.0, 'nb_data': 3, 'minutes': 10}),
            self.myredis.lpop('current_cost_2012-12-13'))
