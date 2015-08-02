import asyncio
import configparser
import ssl
import os
from domopyc.daq.rfxcom_emiter_receiver import create_rfxtrx433e, RFXCOM_KEY
from domopyc.subscribers.mysql_toolbox import MysqlTemperatureMessageHandler
from domopyc.subscribers.redis_toolbox import AsyncRedisSubscriber, create_redis_pool
from domopyc.web.domopyc_server import init, create_mysql_pool
from domopyc.web.keep_alive_service import KeepAliveService


@asyncio.coroutine
def run_application(mysq_pool):
     # backend
    daq_rfxcom = yield from create_rfxtrx433e()
    pool_temp_recorder = AsyncRedisSubscriber((yield from create_redis_pool()),
                                                  MysqlTemperatureMessageHandler(mysq_pool, 'pool_temperature'),
                                                  RFXCOM_KEY).start()


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read(os.path.dirname(__file__) +'/web/users.conf')

    sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    sslcontext.load_cert_chain(os.path.dirname(__file__) + '/web/domopyc.crt', os.path.dirname(__file__) +'/web/domopyc.key')

    loop = asyncio.get_event_loop()
    pool = loop.run_until_complete(create_mysql_pool())
    keep_alive = KeepAliveService(pool, loop).start()
    loop.run_until_complete(init(loop, pool, config=config, sslcontext=sslcontext))
    asyncio.async(run_application(pool))
    loop.run_forever()