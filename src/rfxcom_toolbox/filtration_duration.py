from asyncio import get_event_loop
from daq.publishers.redis_publisher import RedisPublisher
from daq.rfxcom_emiter_receiver import RfxcomReader
from rfxcom_toolbox.rfxcom_redis import create_redis_pool

dev_name = '/dev/serial/by-id/usb-RFXCOM_RFXtrx433_A1XZI13O-if00-port0'


def calculate_in_minutes(temperature):
    if temperature < 8.0:
        return 0
    return temperature/2 * 60


if __name__ == '__main__':
    try:
        redis_conn = create_redis_pool()
        RfxcomReader(dev_name, RedisPublisher(redis_conn))
        get_event_loop().run_forever()
    finally:
        get_event_loop().close()
