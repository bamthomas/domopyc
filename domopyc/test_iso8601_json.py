from datetime import datetime, timezone
from json import dumps, loads
from unittest import TestCase
from decimal import Decimal

from domopyc.iso8601_json import Iso8601DateEncoder, with_iso8601_date


class TestIso8601(TestCase):
    def test_encoder(self):
        self.assertEqual('{"date": "2015-12-11T12:13:14"}',
                         dumps({'date': datetime(2015, 12, 11, 12, 13, 14)}, cls=Iso8601DateEncoder))

    def test_decoder(self):
        self.assertEqual({'date': datetime(2015, 12, 11, 12, 13, 14, tzinfo=timezone.utc)},
                         loads('{"date": "2015-12-11T12:13:14"}', object_hook=with_iso8601_date))

    def test_encoder_bigdecimal_also(self):
        self.assertEqual('{"watt": 123.0}',
                         dumps({'watt': Decimal(123)}, cls=Iso8601DateEncoder))