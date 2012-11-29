# coding=utf-8
from datetime import datetime
from xml.etree.ElementTree import XML, XMLParser
import serial

__author__ = 'bruno'

ser = serial.Serial('/dev/ttyUSB0', baudrate=57600,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=10)
try:
    while True:
        line = ser.readline()
        if line:
            xml_data = XML(line, XMLParser())
            if len(xml_data) >= 7 and xml_data[2].tag == 'time' and xml_data[7].tag == 'ch1':
                power = int(xml_data[7][0].text)
                print '%s : %s (%s°C)' % (datetime.now(), power, xml_data[3].text)

finally:
    print 'closing'
    ser.close()