import asyncio
from domopyc.daq.rfxcom_emiter_receiver import create_rfxtrx433e, RFXCOM_KEY
from domopyc.subscribers.mysql_toolbox import MysqlTemperatureMessageHandler
from domopyc.subscribers.redis_toolbox import AsyncRedisSubscriber, create_redis_pool
from domopyc.web.domopyc_server import init, create_mysql_pool


@asyncio.coroutine
def run_application():
     # backend
    daq_rfxcom = yield from create_rfxtrx433e()
    pool_temp_recorder = AsyncRedisSubscriber((yield from create_redis_pool()),
                                                  MysqlTemperatureMessageHandler((yield from create_mysql_pool()), 'pool_temperature'),
                                                  RFXCOM_KEY).start()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    asyncio.async(run_application())
    loop.run_until_complete(init(loop))
    loop.run_forever()