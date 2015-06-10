import asyncio
from datetime import datetime, timezone, time, timedelta
from decimal import Decimal
from unittest import TestCase

import aiomysql
from subscribers.mysql_toolbox import MysqlCurrentCostMessageHandler
from test_utils.ut_async import async_coro
from tzlocal import get_localzone
from web import current_cost_mysql_service
from web.current_cost_mysql_service import CurrentCostDatabaseReader, merge_full_and_empty_hours


class GetCurrentCostData(TestCase):
    @async_coro
    def setUp(self):
        self.pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
                                                    user='test', password='test', db='test',
                                                    loop=asyncio.get_event_loop())

        self.message_handler = MysqlCurrentCostMessageHandler(self.pool)
        self.current_cost_service = CurrentCostDatabaseReader(self.pool, time(8, 0), time(22, 0))
        current_cost_mysql_service.now = lambda: datetime(2015, 6, 1, 12, 0, 0, tzinfo=get_localzone())
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("truncate current_cost")

    @async_coro
    def tearDown(self):
        self.pool.close()
        yield from self.pool.wait_closed()

    @async_coro
    def test_get_history_three_days(self):
        yield from self.message_handler.save({'date': datetime(2015, 5, 28, 12, 0, 0), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.2})
        yield from self.message_handler.save({'date': datetime(2015, 5, 29, 10, 10, 0), 'watt': 1000, 'minutes': 120, 'nb_data': 120, 'temperature': 20.2})
        yield from self.message_handler.save({'date': datetime(2015, 5, 29, 12, 10, 0), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.2})
        yield from self.message_handler.save({'date': datetime(2015, 5, 30, 12, 20, 0), 'watt': 1000, 'minutes': 180, 'nb_data': 120, 'temperature': 20.2})

        data = yield from self.current_cost_service.get_history()

        self.assertEqual(3, len(data))
        self.assertEqual((datetime(2015, 5, 28, 0, 0), Decimal(1)), data[0])
        self.assertEqual((datetime(2015, 5, 29, 0, 0), Decimal(3)), data[1])
        self.assertEqual((datetime(2015, 5, 30, 0, 0), Decimal(3)), data[2])

    @async_coro
    def test_get_costs_since_and_only_empty_hours(self):
        yield from self.message_handler.save({'date': datetime(2015, 5, 28, 12, 0, 0), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.2})
        yield from self.message_handler.save({'date': datetime(2015, 5, 30, 7, 0, 0), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.2})

        data = yield from self.current_cost_service.get_costs(since=datetime(2015, 5, 30, tzinfo=get_localzone()))

        self.assertTupleEqual((datetime(2015, 5, 30), (Decimal(0.0), Decimal(1.0))), data[0])

    @async_coro
    def test_get_costs_without_empty_and_full_hours(self):
        current_cost_service_without_discount_hours = CurrentCostDatabaseReader(self.pool)
        yield from self.message_handler.save({'date': datetime(2015, 5, 28, 12, 0, 0), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.2})
        yield from self.message_handler.save({'date': datetime(2015, 5, 28, 7, 0, 0), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.2})

        data = yield from current_cost_service_without_discount_hours.get_costs(since=datetime(2015, 5, 28, tzinfo=get_localzone()))

        self.assertEqual(1, len(data))
        self.assertEqual((datetime(2015, 5, 28), (Decimal(2.0), Decimal(0.0))), data[0])

    @async_coro
    def test_get_costs_full_and_empty_hours(self):
        yield from self.message_handler.save({'date': datetime(2015, 5, 28, 12, 0, 0), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.2})
        yield from self.message_handler.save({'date': datetime(2015, 5, 28, 7, 0, 0), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.2})
        yield from self.message_handler.save({'date': datetime(2015, 5, 28, 23, 0, 0), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.2})

        data = yield from self.current_cost_service.get_costs(since=datetime(2015, 5, 28, 0, 0, tzinfo=get_localzone()))

        self.assertEqual(1, len(data))
        self.assertEqual((datetime(2015, 5, 28), (Decimal(1.0), Decimal(2.0))), data[0])

    @async_coro
    def test_get_costs_since_16_days_is_grouped_by_week(self):
        current_cost_mysql_service.now = lambda: datetime(2015, 6, 17, 12, 0, 0)
        for i in range(1, 17):
            yield from self.message_handler.save({'date': datetime(2015, 6, i, 12, 0, 0), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.2})

        data = yield from self.current_cost_service.get_costs(since=datetime(2015, 6, 1, 0, 0))

        self.assertEqual(3, len(data))
        self.assertEqual((datetime(2015, 6, 1), (Decimal(6.0), Decimal(0.0))), data[0])
        self.assertEqual((datetime(2015, 6, 7), (Decimal(7.0), Decimal(0.0))), data[1])
        self.assertEqual((datetime(2015, 6, 14), (Decimal(3.0), Decimal(0.0))), data[2])

    @async_coro
    def test_get_costs_since_11_weeks_is_grouped_by_month(self):
        current_cost_mysql_service.now = lambda: datetime(2015, 8, 17, 12, 0, 0)
        for i in range(0, 65):
            yield from self.message_handler.save({'date': datetime(2015, 6, 1, 12, 0, 0) + timedelta(days=i), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.2})

        data = yield from self.current_cost_service.get_costs(since=datetime(2015, 6, 1, 0, 0))

        self.assertEqual(3, len(data))
        self.assertEqual((datetime(2015, 6, 1), (Decimal(30.0), Decimal(0.0))), data[0])
        self.assertEqual((datetime(2015, 7, 1), (Decimal(31.0), Decimal(0.0))), data[1])
        self.assertEqual((datetime(2015, 8, 1), (Decimal(4.0), Decimal(0.0))), data[2])


class MergeEmptyAndFullHours(TestCase):
    def test_no_empty_hours(self):
        self.assertTupleEqual(((datetime(2015, 5, 28), (1, 0)),), merge_full_and_empty_hours(((datetime(2015, 5, 28), 1),), ()))

    def test_with_empty_hours(self):
        self.assertTupleEqual(((datetime(2015, 5, 28), (1, 2)),), merge_full_and_empty_hours(((datetime(2015, 5, 28), 1), ), ((datetime(2015, 5, 28), 2), )))

    def test_with_empty_hours_on_different_date(self):
        self.assertTupleEqual(((datetime(2015, 5, 28), (1, 0)), (datetime(2015, 5, 29), (0, 2))),
                              merge_full_and_empty_hours(((datetime(2015, 5, 28), 1),), ((datetime(2015, 5, 29), 2),)))
