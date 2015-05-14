# coding=utf-8
import asyncio
from datetime import datetime
import logging
from serial import FileLike
import xml.etree.cElementTree as ET

CURRENT_COST = 'current_cost'

logging.basicConfig(format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
LOGGER = logging.getLogger('current_cost')

DEVICE = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'
CURRENT_COST_KEY = 'current_cost'


def now():
    return datetime.now()


class AsyncCurrentCostReader(FileLike):

    def __init__(self, drv, publisher, event_loop=asyncio.get_event_loop()):
        super().__init__()
        self.event_loop = event_loop
        self.publisher = publisher
        self.serial_drv = drv
        self.event_loop.add_reader(self.serial_drv.fd, self.read_callback)

    def read_callback(self):
        line = self.readline()
        if line:
            try:
                xml_data = ET.fromstring(line)
                power_element = xml_data.find('ch1/watts')
                if power_element is not None:
                    power = int(power_element.text)
                    asyncio.async(self.publisher.handle({'date': now().isoformat(), 'watt': power,
                                                         'temperature': float(xml_data.find('tmpr').text)}))
            except ET.ParseError as xml_parse_error:
                LOGGER.exception(xml_parse_error)

    def read(self, bytes=1):
        return self.serial_drv.read(bytes)

    def remove_reader(self):
        self.event_loop.remove_reader(self.serial_drv.fd)
