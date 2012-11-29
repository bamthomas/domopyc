# coding=utf-8
from datetime import datetime
from json import loads
from threading import Thread, Event
from xml.etree.ElementTree import XML, XMLParser
import serial
import redis

CURRENT_COST = 'current_cost'
REDIS = redis.Redis()
__author__ = 'bruno'


class CurrentCostReader(Thread):
    def __init__(self, myredis):
        super(CurrentCostReader, self).__init__(target=self.read_sensor)
        self.serial = serial.Serial('/dev/ttyUSB0', baudrate=57600,
            bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=10)
        self.redis = myredis
        self.stop = Event()

    def read_sensor(self):
        try:
            while not self.stop.is_set():
                line = self.serial.readline()
                if line:
                    xml_data = XML(line, XMLParser())
                    if len(xml_data) >= 7 and xml_data[2].tag == 'time' and xml_data[7].tag == 'ch1':
                        power = int(xml_data[7][0].text)
                        print '%s : %s (%s°C)' % (datetime.now(), power, xml_data[3].text)
                        self.redis.publish(CURRENT_COST,{'timestamp':datetime.now().isoformat(), 'watt':power, 'temperature':xml_data[3].text})
        finally:
            print 'closing'
            self.serial.close()

    def stop(self):
        self.stop.set()
        
class RedisSubscriber(Thread):
    def __init__(self, redis, callback_func):
        super(RedisSubscriber, self).__init__(target=self.wait_messages)
        self.callback_func = callback_func
        self.redis = redis
        self.pubsub = redis.pubsub()
        self.pubsub.subscribe([CURRENT_COST])

    def wait_messages(self):
        for item in self.pubsub.listen():
            if item['type'] == 'message':
                self.callback_func(loads(item['data']))

    def stop(self):
        self.pubsub.unsubscribe()

if __name__ == '__main__':
    current_cost = CurrentCostReader(REDIS)
    current_cost.start()