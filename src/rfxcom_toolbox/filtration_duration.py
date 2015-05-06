from asyncio import get_event_loop
from rfxcom_toolbox.rfxcom_redis import RfxcomReader, RedisPublisher

dev_name = '/dev/serial/by-id/usb-RFXCOM_RFXtrx433_A1XZI13O-if00-port0'

if __name__ == '__main__':
    try:
        RfxcomReader(dev_name, RedisPublisher())
        get_event_loop().run_forever()
    finally:
        get_event_loop().close()


def calculate_in_minutes(temperature):
    if temperature < 8.0:
        return 0
    return temperature/2 * 60