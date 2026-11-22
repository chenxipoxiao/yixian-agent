import unittest
from yixian.protobuf_wire import fields, varint, decode_row, table_rows


class WireTests(unittest.TestCase):
    def test_truncation_rejected(self):
        for data in (b'\x12\x03a', b'\x80', b'\x0d\x01', b'\x08' + b'\xff' * 10):
            with self.assertRaises(ValueError):
                fields(data)

    def test_signed_packed_and_unknown_are_preserved(self):
        schema = {'1': {'name': 'id', 'type': 'int32'}, '2': {'name': 'name', 'type': 'string'},
                  '3': {'name': 'params', 'type': 'int32[]'}, '4': {'name': 'hidden', 'type': 'bool'}}
        data = b'\x08' + b'\xff' * 9 + b'\x01' + b'\x12\x03abc\x1a\x02\x01\x02\x18\x03\x48\x07'
        row = decode_row(data, schema)
        self.assertEqual(row['id'], -1)
        self.assertEqual(row['params'], [1, 2, 3])
        self.assertEqual(row['name'], 'abc')
        self.assertIs(row['hidden'], False)
        self.assertEqual(row['_unknown_fields'][0]['number'], 9)

    def test_envelope_and_schema_mismatch(self):
        self.assertEqual(table_rows(b'\x0a\x01x\x12\x02\x08\x01'), [b'\x08\x01'])
        with self.assertRaises(ValueError):
            decode_row(b'\x0a\x01a', {'1': {'name': 'id', 'type': 'int32'}})


if __name__ == '__main__':
    unittest.main()
