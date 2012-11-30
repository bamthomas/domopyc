from Queue import Queue
from json import dumps
import unittest
from current_cost import CURRENT_COST, RedisSubscriber
from datetime import datetime
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




