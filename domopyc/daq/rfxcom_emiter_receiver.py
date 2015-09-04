# coding=utf-8
import asyncio
from datetime import datetime
import logging
import binascii

from domopyc.daq.publishers.redis_publisher import RedisPublisher, create_redis_pool
from rfxcom import protocol
from rfxcom.transport import AsyncioTransport
from domopyc.subscribers.redis_toolbox import AsyncRedisSubscriber
from tzlocal import get_localzone

root = logging.getLogger()
logging.basicConfig()
root.setLevel(logging.INFO)

logger = logging.getLogger('rfxcom')

RFXCOM_KEY = "rfxcom"
RFXCOM_KEY_CMD = "rfxcom_cmd"


def now():
    return datetime.now(tz=get_localzone())


@asyncio.coroutine
def create_publisher():
    redis_conn = yield from create_redis_pool(2)
    return RedisPublisher(redis_conn, RFXCOM_KEY)

@asyncio.coroutine
def create_subscriber():
    redis_conn = yield from create_redis_pool(2)
    return AsyncRedisSubscriber(redis_conn, RfxTrx433eMessageHandler(), RFXCOM_KEY_CMD)


class RfxTrx433eMessageHandler(object):
    def __init__(self):
        self.rfxcom_transport = None

    def set_rfxcom_transport(self, transport):
        self.rfxcom_transport = transport

    @asyncio.coroutine
    def handle(self, json_message):
        if self.rfxcom_transport is not None:
            # cf http://rfxcmd.eu/?page_id=191
            self.rfxcom_transport.write(
                binascii.unhexlify('0B1100010%s020%s0F70' % (json_message['code_device'], json_message['value'])))
        else:
            logger.info('cannot send RFXCOM command : rfxcom_transport is not set')


class RfxTrx433e(object):
    def __init__(self, device, publisher, subscriber, event_loop=asyncio.get_event_loop()):
        self.publisher = publisher
        self.rfxcom_transport = self.create_transport(device, event_loop)
        subscriber.message_handler.set_rfxcom_transport(self.rfxcom_transport)
        self.subscriber = subscriber

    def create_transport(self, device, event_loop):
        return AsyncioTransport(device, event_loop,
                                callbacks={protocol.TempHumidity: self.handle_temp_humidity,
                                           '*': self.default_callback})

    def handle_temp_humidity(self, packet):
        asyncio.async(self.publisher.publish(dict(packet.data, date=now().isoformat())))

    def default_callback(self, packet):
        logger.info('packet %s not handled' % packet)


@asyncio.coroutine
def create_rfxtrx433e(config):
    publisher = yield from create_publisher()
    subscriber = yield from create_subscriber()
    return RfxTrx433e(config['rfxcom']['device'], publisher, subscriber.start())

