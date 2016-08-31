# coding=utf-8
import asyncio
import logging
import xml.etree.cElementTree as ET
from datetime import datetime
from functools import partial
from logging.handlers import SysLogHandler

import serial
from domopyc.daq.publishers.redis_publisher import RedisPublisher
from tzlocal import get_localzone

CURRENT_COST = 'current_cost'

logging.basicConfig(format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
LOGGER = logging.getLogger('current_cost')
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(SysLogHandler())


CURRENT_COST_KEY = 'current_cost'


def now():
    return datetime.now(tz=get_localzone())


def create_current_cost(redis_connection, config):
    LOGGER.info("create reader")
    return AsyncCurrentCostReader(create_serial_factory(config), RedisPublisher(redis_connection, CURRENT_COST_KEY))


def create_serial_factory(config):
    return partial(serial.Serial, config['device'], baudrate=57600,
                         bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                         timeout=10)


class AsyncCurrentCostReader(object):
    RECONNECT_TIMEOUT_SECONDS = 500

    def __init__(self, drv_factory, publisher, event_loop=asyncio.get_event_loop(), connection_delay_seconds=1):
        self.connection_delay_seconds = connection_delay_seconds
        self.event_loop = event_loop
        self.publisher = publisher
        self._serial_drv = None
        self.serial_drv_factory = drv_factory
        self._open_serial()

    def read_callback(self):
        try:
            line = self._serial_drv.readline().decode().strip()
        except serial.SerialException as serial_exc:
            LOGGER.exception(serial_exc)
            self.close()
            asyncio.async(self.try_to_connect(), loop=self.event_loop)
            return

        LOGGER.debug('line : %s' % line)
        if line:
            try:
                xml_data = ET.fromstring(line)
                power_element = xml_data.find('ch1/watts')
                if power_element is not None:
                    power = int(power_element.text)
                    asyncio.async(self.publisher.publish({'date': now().isoformat(), 'watt': power,
                                                         'temperature': float(xml_data.find('tmpr').text)}))
            except ET.ParseError as xml_parse_error:
                LOGGER.exception(xml_parse_error)

    def read(self, bytes=1):
        return self._serial_drv.read(bytes)

    def close(self):
        self.event_loop.remove_reader(self._serial_drv.fd)
        self._serial_drv.close()

    @asyncio.coroutine
    def try_to_connect(self):
        while not self._serial_drv.isOpen():
            LOGGER.info('trying to connect current_cost serial port...')
            try:
                self._open_serial()
                LOGGER.info('connected to current_cost')
            except serial.SerialException as e:
                LOGGER.exception(e)
                yield from asyncio.sleep(self.connection_delay_seconds)

    def _open_serial(self):
        self._serial_drv = self.serial_drv_factory()
        self.event_loop.add_reader(self._serial_drv.fd, self.read_callback)