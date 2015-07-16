import asyncio
from domopyc.daq.rfxcom_emiter_receiver import create_rfxtrx433e, RFXCOM_KEY
from domopyc.subscribers.mysql_toolbox import MysqlTemperatureMessageHandler
from domopyc.subscribers.redis_toolbox import AsyncRedisSubscriber, create_redis_pool
from domopyc.web import domopyc_server
from domopyc.web.domopyc_server import create_mysql_pool


def run_application():
    loop = asyncio.get_event_loop()
    # backend
    daq_rfxcom = yield from create_rfxtrx433e()
    pool_temp_recorder = AsyncRedisSubscriber((yield from create_redis_pool()),
                                                  MysqlTemperatureMessageHandler((yield from create_mysql_pool()), 'pool_temperature'),
                                                  RFXCOM_KEY).start()
    loop.run_until_complete(domopyc_server.init(loop))
    loop.run_forever()

if __name__ == '__main__':
    run_application()