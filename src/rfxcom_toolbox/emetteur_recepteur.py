from asyncio import get_event_loop
import logging
import asyncio
from json import dumps
import asyncio_redis
from rfxcom import protocol

from rfxcom.transport import AsyncioTransport

dev_name = '/dev/serial/by-id/usb-RFXCOM_RFXtrx433_A1XZI13O-if00-port0'

root = logging.getLogger()
logging.basicConfig()
root.setLevel(logging.INFO)

logger = logging.getLogger('rfxcom')


class RedisPublisher(object):
    RFXCOM_KEY = "rfxcom"

    def __init__(self, host='localhost', port=6379):
        self.port = port
        self.host = host
        self.connection = None

    @asyncio.coroutine
    def redis_connect(self):
        self.connection = yield from asyncio_redis.Connection.create(self.host, self.port)

    @asyncio.coroutine
    def publish(self, event):
        if self.connection is None:
            yield from asyncio.wait_for(self.redis_connect(), timeout=5.0)
        yield from self.connection.publish(self.RFXCOM_KEY, dumps(event))


class RfxcomReader(object):
    def __init__(self, device, publisher, event_loop=asyncio.get_event_loop()):
        self.publisher = publisher
        self.rfxcom_transport = self.create_transport(device, event_loop)

    def create_transport(self, device, event_loop):
        return AsyncioTransport(device, event_loop,
                                callbacks={protocol.TempHumidity: self.handle_temp_humidity,
                                           '*': self.default_callback})

    def handle_temp_humidity(self, packet):
        asyncio.async(self.publisher.publish(packet.data))

    def default_callback(self, packet):
        logger.info('packet <%s> not handled' % packet)

if __name__ == '__main__':
    try:
        RfxcomReader(dev_name, RedisPublisher())
        get_event_loop().run_forever()
    finally:
        get_event_loop().close()