from asyncio import get_event_loop
from rfxcom import protocol

from rfxcom.transport import AsyncioTransport

dev_name = '/dev/serial/by-id/usb-RFXCOM_RFXtrx433_A1XZI13O-if00-port0'
loop = get_event_loop()

# root = logging.getLogger()
# logging.basicConfig()
# root.setLevel(logging.INFO)


def temp_humidity_handler(packet):
    print(packet.data)


def default_callback(packet):
    pass


try:
    rfxcom = AsyncioTransport(dev_name, loop, callbacks={
        protocol.TempHumidity: temp_humidity_handler, '*': default_callback})
    loop.run_forever()
finally:
    loop.close()