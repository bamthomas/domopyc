import asyncio
from daq.publishers.redis_publisher import RedisPublisher
from daq.rfxcom_emiter_receiver import RfxTrx433e, RFXCOM_KEY
from subscribers.redis_toolbox import create_redis_pool



def calculate_in_minutes(temperature):
    if temperature < 10.0:
        return 0
    return temperature/2 * 60


