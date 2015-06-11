import asyncio
from daq.publishers.redis_publisher import RedisPublisher
from daq.rfxcom_emiter_receiver import RfxcomReader, RFXCOM_KEY
from subscribers.redis_toolbox import create_redis_pool


dev_name = '/dev/serial/by-id/usb-RFXCOM_RFXtrx433_A1XZI13O-if00-port0'


def calculate_in_minutes(temperature):
    if temperature < 10.0:
        return 0
    return temperature/2 * 60


@asyncio.coroutine
def create_publisher():
    redis_conn = yield from create_redis_pool()
    return RfxcomReader(dev_name, RedisPublisher(redis_conn, RFXCOM_KEY))


if __name__ == '__main__':
    try:
        publisher = asyncio.async(create_publisher())
        asyncio.get_event_loop().run_forever()
    finally:
        asyncio.get_event_loop().close()
