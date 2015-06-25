# coding=utf-8
import asyncio
from datetime import datetime
from json import loads
import logging
import binascii
from daq.publishers.redis_publisher import RedisPublisher, create_redis_pool
from iso8601_json import with_iso8601_date
from rfxcom import protocol
from rfxcom.transport import AsyncioTransport
from tzlocal import get_localzone

root = logging.getLogger()
logging.basicConfig()
root.setLevel(logging.INFO)

logger = logging.getLogger('rfxcom')

RFXCOM_KEY = "rfxcom"
RFXCOM_KEY_CMD = "rfxcom_cmd"
dev_name = '/dev/serial/by-id/usb-RFXCOM_RFXtrx433_A1XZI13O-if00-port0'


def now():
    return datetime.now(tz=get_localzone())


@asyncio.coroutine
def create_publisher():
    redis_conn = yield from create_redis_pool(2)
    return RedisPublisher(redis_conn, RFXCOM_KEY)


class RfxTrx433e(object):
    def __init__(self, device, publisher, event_loop=asyncio.get_event_loop()):
        self.publisher = publisher
        asyncio.async(self.subscriber_loop())
        self.rfxcom_transport = self.create_transport(device, event_loop)

    def create_transport(self, device, event_loop):
        return AsyncioTransport(device, event_loop,
                                callbacks={protocol.TempHumidity: self.handle_temp_humidity,
                                           '*': self.default_callback})

    def handle_temp_humidity(self, packet):
        asyncio.async(self.publisher.publish(dict(packet.data, date=now().isoformat())))

    def default_callback(self, packet):
        logger.info('packet <%s> not handled' % packet)

    @asyncio.coroutine
    def subscriber_loop(self):
        subscriber = yield from self.publisher.redis_conn.start_subscribe()
        yield from subscriber.subscribe([RFXCOM_KEY_CMD])
        while True:
            message_to_send = yield from subscriber.next_published()

            message = loads(message_to_send.value)
            yield from self.sendLightning2Message(message['code_device'], message['value'])

    @asyncio.coroutine
    def sendLightning2Message(self, deviceOn7HexChars, onOff):
        # cf http://rfxcmd.eu/?page_id=191
        self.rfxcom_transport.write(binascii.unhexlify('0B1100010%s020%s0F70' % (deviceOn7HexChars, onOff)))

@asyncio.coroutine
def blah():
    rfxcom = RfxTrx433e(dev_name, (yield from create_publisher()))
    return rfxcom


if __name__ == '__main__':
    rfxcom = asyncio.async(blah())
    asyncio.get_event_loop().run_forever()