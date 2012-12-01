from Queue import Queue, Empty
from json import dumps
import unittest
from current_cost import CURRENT_COST, RedisSubscriber, CurrentCostReader
from datetime import datetime
import current_cost
import redis

__author__ = 'bruno'

class RedisSubscriberTest(unittest.TestCase):
    def setUp(self):
        self.queue = Queue()
        def test_callback(event):
            self.queue.put(event)
        self.myredis = redis.Redis()
        self.subscriber = RedisSubscriber(self.myredis, test_callback)
        self.subscriber.start()

    def tearDown(self):
        self.subscriber.stop()
        self.subscriber.join()

    def test_reader(self):
        expected = {'date': datetime.now().isoformat(), 'watt': '123', 'temperature': '23.4'}

        self.myredis.publish(CURRENT_COST, dumps(expected))

        event = self.queue.get()
        self.assertIsNotNone(event)
        self.assertDictEqual(event, expected)

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
        def publish_func_test(channel, event):
            self.queue.put(event)
        self.mockserial = MockSerial()
        self.current_cost_reader = CurrentCostReader(self.mockserial, publish_func_test)
        self.current_cost_reader.start()

    def tearDown(self):
        self.current_cost_reader.stop()
        self.current_cost_reader.join()

    def test_read_sensor(self):
        self.mockserial.send('<msg><src>CC128-v1.29</src><dsb>00302</dsb><time>02:57:28</time><tmpr>21.4</tmpr><sensor>1</sensor><id>00126</id><type>1</type><ch1><watts>00305</watts></ch1></msg>')

        self.assertDictEqual(self.queue.get(timeout=1), {'date': (current_cost.now().isoformat()), 'watt': 305, 'temperature':'21.4'})



