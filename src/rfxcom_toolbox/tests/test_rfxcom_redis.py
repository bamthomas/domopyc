from datetime import datetime, timezone
from json import dumps
import asyncio
from daq import rfxcom_emiter_receiver

from rfxcom_toolbox import rfxcom_redis
from rfxcom_toolbox.rfxcom_redis import RedisTimeCappedSubscriber
from test_utils.ut_async import async_coro
from test_utils.ut_redis import WithRedis


class TestPoolSubscriber(WithRedis):

    @async_coro
    def setUp(self):
        yield from super().setUp()

    @async_coro
    def test_average_no_data(self):
        pool_temp = RedisTimeCappedSubscriber(self.connection, 'pool_temperature').start()

        value = yield from pool_temp.get_average()
        self.assertEqual(0.0, value)

    @async_coro
    def test_average_one_data(self):
        pool_temp = RedisTimeCappedSubscriber(self.connection, 'pool_temperature').start(1)

        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime.now().isoformat(), 'temperature': 3.0}))
        yield from asyncio.wait_for(pool_temp.message_loop_task, timeout=1)

        value = yield from pool_temp.get_average()
        self.assertEqual(3.0, value)

    @async_coro
    def test_average_two_data(self):
        pool_temp = RedisTimeCappedSubscriber(self.connection, 'pool_temperature').start(2)

        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 0).isoformat(), 'temperature': 3.0}))
        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 1).isoformat(), 'temperature': 4.0}))
        yield from asyncio.wait_for(pool_temp.message_loop_task, timeout=1)

        value = yield from pool_temp.get_average()
        self.assertEqual(3.5, value)

    @async_coro
    def test_capped_collection(self):
        pool_temp = RedisTimeCappedSubscriber(self.connection, 'pool_temperature', 10).start(3)
        rfxcom_redis.now = lambda: datetime(2015, 2, 14, 15, 0, 10, tzinfo=timezone.utc)

        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 0).isoformat(), 'temperature': 2.0}))
        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 1).isoformat(), 'temperature': 4.0}))
        yield from self.connection.publish(rfxcom_emiter_receiver.RFXCOM_KEY, dumps({'date': datetime(2015, 2, 14, 15, 0, 2).isoformat(), 'temperature': 6.0}))
        yield from asyncio.wait_for(pool_temp.message_loop_task, timeout=1)

        value = yield from pool_temp.get_average()
        self.assertEqual(5.0, value)


