# coding=utf-8
import asyncio
from datetime import datetime
import logging
from rfxcom import protocol
from rfxcom.transport import AsyncioTransport
from tzlocal import get_localzone

root = logging.getLogger()
logging.basicConfig()
root.setLevel(logging.INFO)

logger = logging.getLogger('rfxcom')

RFXCOM_KEY = "rfxcom"


def now():
    return datetime.now(tz=get_localzone())


class RfxcomReader(object):
    def __init__(self, device, publisher, event_loop=asyncio.get_event_loop()):
        self.publisher = publisher
        self.rfxcom_transport = self.create_transport(device, event_loop)

    def create_transport(self, device, event_loop):
        return AsyncioTransport(device, event_loop,
                                callbacks={protocol.TempHumidity: self.handle_temp_humidity,
                                           '*': self.default_callback})

    def handle_temp_humidity(self, packet):
        asyncio.async(self.publisher.publish(dict(packet.data, date=now().isoformat())))

    def default_callback(self, packet):
        logger.info('packet <%s> not handled' % packet)