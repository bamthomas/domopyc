import asyncio
from daq.current_cost_sensor import AsyncCurrentCostReader, CURRENT_COST_KEY, LOGGER
from daq.publishers.redis_publisher import RedisPublisher, create_redis_connection
import serial


if __name__ == '__main__':
    serial_drv = serial.Serial('/dev/ttyUSB0', baudrate=57600,
                               bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                               timeout=10)

    LOGGER.info("create redis connection")
    redis_conn = asyncio.wait(asyncio.async(create_redis_connection()))

    loop = asyncio.get_event_loop()
    LOGGER.info("create reader")
    reader = AsyncCurrentCostReader(serial_drv, RedisPublisher(redis_conn, CURRENT_COST_KEY), loop)

    LOGGER.info("launch main loop")
    loop.run_forever()