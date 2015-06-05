import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest import TestCase

import aiomysql
from subscribers.mysql_toolbox import MysqlAverageMessageHandler
from test_utils.ut_async import async_coro
from web.current_cost_mysql_service import CurrentCostDatabaseReader


class GetCurrentCostData(TestCase):
    @async_coro
    def setUp(self):
        self.pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
                                                    user='test', password='test', db='test',
                                                    loop=asyncio.get_event_loop())

        self.message_handler = MysqlAverageMessageHandler(self.pool)
        self.current_cost_service = CurrentCostDatabaseReader(self.pool)
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("truncate current_cost")

    @async_coro
    def test_get_history_three_days(self):
        yield from self.message_handler.save({'date': datetime(2015, 5, 28, 12, 0, 0, tzinfo=timezone.utc), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.2})
        yield from self.message_handler.save({'date': datetime(2015, 5, 29, 10, 10, 0, tzinfo=timezone.utc), 'watt': 1000, 'minutes': 120, 'nb_data': 120, 'temperature': 20.2})
        yield from self.message_handler.save({'date': datetime(2015, 5, 29, 12, 10, 0, tzinfo=timezone.utc), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.2})
        yield from self.message_handler.save({'date': datetime(2015, 5, 30, 12, 20, 0, tzinfo=timezone.utc), 'watt': 1000, 'minutes': 180, 'nb_data': 120, 'temperature': 20.2})

        data = yield from self.current_cost_service.get_history()

        self.assertEqual(3, len(data))
        self.assertEqual((datetime(2015, 5, 28, 0, 0), Decimal(1)), data[0])
        self.assertEqual((datetime(2015, 5, 29, 0, 0), Decimal(3)), data[1])
        self.assertEqual((datetime(2015, 5, 30, 0, 0), Decimal(3)), data[2])
