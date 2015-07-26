import asyncio
from domopyc.daq.rfxcom_emiter_receiver import create_rfxtrx433e, RFXCOM_KEY
from domopyc.subscribers.mysql_toolbox import MysqlTemperatureMessageHandler
from domopyc.subscribers.redis_toolbox import AsyncRedisSubscriber, create_redis_pool
from domopyc.web.domopyc_server import init, create_mysql_pool
from domopyc.web.switch_service import KeepAliveService


@asyncio.coroutine
def run_application(mysq_pool):
     # backend
    daq_rfxcom = yield from create_rfxtrx433e()
    pool_temp_recorder = AsyncRedisSubscriber((yield from create_redis_pool()),
                                                  MysqlTemperatureMessageHandler(mysq_pool, 'pool_temperature'),
                                                  RFXCOM_KEY).start()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    pool = loop.run_until_complete(create_mysql_pool())
    keep_alive = KeepAliveService(pool, loop).start()
    asyncio.async(run_application(pool))
    loop.run_until_complete(init(loop, pool))
    loop.run_forever()