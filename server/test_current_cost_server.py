from datetime import datetime, timedelta
from json import dumps
import unittest
from current_cost_server import REDIS, get_current_cost_data

__author__ = 'bruno'


class RedisGetDataOfDay(unittest.TestCase):

    def setUp(self):
        self.myredis = REDIS
        self.myredis.delete('current_cost_%s' % datetime.now().strftime('%Y-%m-%d'))

    def test_get_data_of_current_day(self):
        expected_json = dumps({'date': datetime.now().isoformat(), 'watt': 305, 'temperature': 21.4})
        self.myredis.lpush('current_cost_%s' % datetime.now().strftime('%Y-%m-%d'), expected_json)

        data = get_current_cost_data()
        self.assertEquals(len(data), 1)
        self.assertEquals(data, [expected_json])
        self.myredis.lpush('current_cost_%s' % datetime.now().strftime('%Y-%m-%d'), dumps({'date': datetime.now().isoformat(), 'watt': 432, 'temperature': 20}))
        self.assertEquals(len(get_current_cost_data()), 2)