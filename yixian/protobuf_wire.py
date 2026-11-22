"""Small strict protobuf wire reader for the game's exported configuration tables.

Field names/types must come from a verified schema; unknown fields remain raw.
This module never imports or executes the game assembly.
"""
from __future__ import annotations
import base64
import struct


def varint(data: bytes, offset: int = 0) -> tuple[int, int]:
    value = 0
    for shift in range(0, 70, 7):
        if offset >= len(data):
            raise ValueError("Truncated protobuf varint")
        byte = data[offset]
        offset += 1
        if shift == 63 and byte > 1:
            raise ValueError("Protobuf varint exceeds 64 bits")
        value |= (byte & 127) << shift
        if byte < 128:
            return value, offset
    raise ValueError("Invalid protobuf varint")


def fields(data: bytes) -> list[tuple[int, int, int | bytes]]:
    result = []
    offset = 0
    while offset < len(data):
        tag, offset = varint(data, offset)
        number, wire = tag >> 3, tag & 7
        if not 0 < number < (1 << 29):
            raise ValueError("Invalid protobuf field number")
        if wire == 0:
            value, offset = varint(data, offset)
        else:
            if wire == 2:
                length, offset = varint(data, offset)
            elif wire in (1, 5):
                length = 8 if wire == 1 else 4
            else:
                raise ValueError(f"Unsupported protobuf wire type {wire}")
            if offset + length > len(data):
                raise ValueError("Truncated protobuf payload")
            value = data[offset:offset + length]
            offset += length
        result.append((number, wire, value))
    return result


def signed32(value: int) -> int:
    value &= 0xffffffff
    return value - (1 << 32) if value >= (1 << 31) else value


def packed_int32(data: bytes) -> list[int]:
    offset, values = 0, []
    while offset < len(data):
        value, offset = varint(data, offset)
        values.append(signed32(value))
    return values


def raw_json(items):
    return [{"number": n, "wire": w, "value": base64.b64encode(v).decode("ascii") if isinstance(v, bytes) else v,
             "encoding": "base64" if isinstance(v, bytes) else "uint64"} for n, w, v in items]


def table_rows(data: bytes) -> list[bytes]:
    """The exported table envelope stores its repeated row messages in field 2."""
    return [value for number, wire, value in fields(data) if number == 2 and wire == 2]


def decode_row(data: bytes, schema: dict[str, dict]) -> dict:
    values, unknown = {}, []
    for number, wire, value in fields(data):
        spec = schema.get(str(number))
        if spec is None:
            unknown.append((number, wire, value))
            continue
        name, kind = spec["name"], spec["type"]
        if kind == "string" and wire == 2:
            decoded = value.decode("utf-8")
        elif kind in ("int32", "enum", "bool") and wire == 0:
            decoded = bool(value) if kind == "bool" else signed32(value)
        elif kind == "float" and wire == 5:
            decoded = struct.unpack("<f", value)[0]
        elif kind == "int32[]" and wire in (0, 2):
            decoded = packed_int32(value) if wire == 2 else [signed32(value)]
            values.setdefault(name, []).extend(decoded)
            continue
        else:
            raise ValueError(f"Schema mismatch for {name}: {kind}, wire {wire}")
        values[name] = decoded
    # Protobuf omits zero/empty values; apply only schema-declared defaults.
    for spec in schema.values():
        default = {"string": "", "int32": 0, "enum": 0, "bool": False, "float": 0.0, "int32[]": []}[spec["type"]]
        values.setdefault(spec["name"], default)
    if unknown:
        values["_unknown_fields"] = raw_json(unknown)
    return values
