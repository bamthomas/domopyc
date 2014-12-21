from datetime import datetime, timedelta
from json import dumps
import unittest
from current_cost.site import current_cost_server
from current_cost.site.current_cost_server import get_current_cost_data, REDIS, LiveDataMessageHandler

__author__ = 'bruno'


class RedisGetDataOfDay(unittest.TestCase):
    def setUp(self):
        self.myredis = REDIS
        self.myredis.delete('current_cost_%s' % datetime.now().strftime('%Y-%m-%d'))

    def test_get_data_of_current_day(self):
        expected_json = {'date': datetime.now().isoformat(), 'watt': 305, 'temperature': 21.4}
        self.myredis.lpush('current_cost_%s' % datetime.now().strftime('%Y-%m-%d'), dumps(expected_json))

        data = get_current_cost_data()
        self.assertEquals(len(data), 1)
        self.assertEquals(data, [expected_json])
        self.myredis.lpush('current_cost_%s' % datetime.now().strftime('%Y-%m-%d'),
            dumps({'date': datetime.now().isoformat(), 'watt': 432, 'temperature': 20}))
        self.assertEquals(len(get_current_cost_data()), 2)


class RedisGetLiveData(unittest.TestCase):
    def setUp(self):
        self.myredis = REDIS
        self.myredis.delete('current_cost_live')

    def tearDown(self):
        self.myredis.delete('current_cost_live')

    def test_get_live_data(self):
        live_data_handler = LiveDataMessageHandler(self.myredis)
        live_data_handler.handle(dumps({'watt': 100, 'temperature':20.0}))

        data = live_data_handler.get_data()

        self.assertEqual(1, len(data))
        self.assertEqual({'watt': 100, 'temperature':20.0}, data[0])

    def test_get_live_data_keeps_one_hour_data(self):
        now = datetime.now()
        live_data_handler = LiveDataMessageHandler(self.myredis)

        current_cost_server.now = lambda: now
        live_data_handler.handle(dumps({'watt': 100}))

        current_cost_server.now = lambda: now + timedelta(minutes=30)
        live_data_handler.handle(dumps({'watt': 200}))

        current_cost_server.now = lambda: now + timedelta(minutes=61)
        live_data_handler.handle(dumps({'watt': 300}))

        self.assertEqual(2, len(live_data_handler.get_data(since_minutes=60)))
        self.assertEqual(1, len(live_data_handler.get_data(since_minutes=30)))


    def test_get_live_data_with_float_period(self):
        live_data_handler = LiveDataMessageHandler(self.myredis, 6.666)
        live_data_handler.handle(dumps({'watt': 100}))

        self.assertEqual(1, len(live_data_handler.get_data(since_minutes=1)))

