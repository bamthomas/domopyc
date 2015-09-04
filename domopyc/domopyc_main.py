import asyncio
import configparser
import ssl
from domopyc.daq.current_cost_sensor import create_current_cost, CURRENT_COST_KEY
import os
from domopyc.daq.rfxcom_emiter_receiver import create_rfxtrx433e, RFXCOM_KEY
from domopyc.subscribers.mysql_toolbox import MysqlTemperatureMessageHandler, MysqlCurrentCostMessageHandler
from domopyc.subscribers.redis_toolbox import AsyncRedisSubscriber, create_redis_pool
from domopyc.web.domopyc_server import init, create_mysql_pool
from domopyc.web.keep_alive_service import KeepAliveService


@asyncio.coroutine
def run_application(mysq_pool, config):
     # backend
    redis_pool_ = yield from create_redis_pool()
    daq_rfxcom = yield from create_rfxtrx433e(config)
    current_cost = create_current_cost(redis_pool_, config)
    current_cost_recorder = AsyncRedisSubscriber(redis_pool_,
                                                 MysqlCurrentCostMessageHandler(mysq_pool, average_period_minutes=10),
                                                 CURRENT_COST_KEY).start()
    pool_temp_recorder = AsyncRedisSubscriber(redis_pool_,
                                                  MysqlTemperatureMessageHandler(mysq_pool, 'pool_temperature', average_period_minutes=10),
                                                  RFXCOM_KEY).start()


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read(os.path.dirname(__file__) + '/web/static/domopyc.conf')

    sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    sslcontext.load_cert_chain('/home/pi/domopyc.crt', '/home/pi/domopyc.key')

    loop = asyncio.get_event_loop()
    pool = loop.run_until_complete(create_mysql_pool())
    keep_alive = KeepAliveService(pool, loop).start()
    loop.run_until_complete(init(loop, pool, config=config, sslcontext=sslcontext))
    asyncio.async(run_application(pool, config))
    loop.run_forever()
