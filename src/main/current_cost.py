# coding=utf-8
from datetime import datetime
from json import loads, dumps
import logging
import threading
from xml.etree.ElementTree import XML, XMLParser, ParseError
import serial
import redis

CURRENT_COST = 'current_cost'
REDIS = redis.Redis()
__author__ = 'bruno'

logging.basicConfig(format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
LOGGER = logging.getLogger('current_cost')

class CurrentCostReader(threading.Thread):
    def __init__(self, serial_drv, publish_func):
        super(CurrentCostReader, self).__init__(target=self.read_sensor)
        self.serial_drv = serial_drv
        self.publish = publish_func
        self.stop_asked = threading.Event()

    def read_sensor(self):
        try:
            while not self.stop_asked.is_set():
                line = self.serial_drv.readline()
                if line:
                    try:
                        xml_data = XML(line, XMLParser())

                        if len(xml_data) >= 7 and xml_data[2].tag == 'time' and xml_data[7].tag == 'ch1':
                            power = int(xml_data[7][0].text)
                            self.publish(CURRENT_COST,{'date':now().isoformat(), 'watt':power, 'temperature':xml_data[3].text})
                    except ParseError as xml_parse_error:
                        LOGGER.exception(xml_parse_error)
        finally:
            self.serial_drv.close()

    def stop(self):
        self.stop_asked.set()

class RedisSubscriber(threading.Thread):
    def __init__(self, redis, callback_func):
        super(RedisSubscriber, self).__init__(target=self.wait_messages)
        self.callback_func = callback_func
        self.pubsub = redis.pubsub()
        self.pubsub.subscribe([CURRENT_COST])

    def wait_messages(self):
        for item in self.pubsub.listen():
            if item['type'] == 'message':
                self.callback_func(item['data'])

    def stop(self):
        self.pubsub.unsubscribe([CURRENT_COST])

def now(): return datetime.now()

def redis_publish(channel, event_dict):
    REDIS.publish(channel, dumps(event_dict))

def redis_save_event(json_event):
    key = 'current_cost_' + now().strftime('%Y-%m-%d')
    REDIS.lpush(key, json_event)
    REDIS.expire(key, 5 * 24 * 3600)

if __name__ == '__main__':
    serial_drv = serial.Serial('/dev/ttyUSB0', baudrate=57600,
            bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=10)
    current_cost = CurrentCostReader(serial_drv, redis_publish)
    current_cost.start()

    redis_save_consumer = RedisSubscriber(REDIS, redis_save_event)
    redis_save_consumer.start()

    current_cost.join()

