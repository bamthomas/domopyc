import unittest


class RfxcomReader(object):
    def start(self):
        pass


class TestRfxcomReader(unittest.TestCase):
    def __init__(self):
        self.mockrfxrom = None

    def test_read_data(self):
        RfxcomReader().start()
        rfxcom_data = {'packet_length': 10, 'packet_type_name': 'Temperature and humidity sensors', 'sub_type': 1,
                       'packet_type': 82, 'temperature': 22.2, 'humidity_status': 0, 'humidity': 0,
                       'sequence_number': 1,
                       'battery_signal_level': 128, 'signal_strength': 128, 'id': '0xBB02',
                       'sub_type_name': 'THGN122/123, THGN132, THGR122/228/238/268'}

        self.mockrfxrom.receive(rfxcom_data)

        self.assertDictEqual(rfxcom_data, self.mockrfxrom.jkfdq)