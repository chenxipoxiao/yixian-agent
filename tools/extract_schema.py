"""Recover selected protobuf schemas from a local managed DLL without executing it.

Usage: python tools/extract_schema.py GAME_DLL OUTPUT_DIRECTORY
Requires dnfile and dncil. Field numbers come from WriteTo's WriteRawTag IL,
not field declaration order. Unsupported patterns are omitted and reported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBytes

DEFAULT_TYPES = [
    "CardConfig", "TalentConfig", "CharacterConfig", "LevelConfig", "SeasonConfig",
    "BuffConfig", "CardCombineConfig", "VersusCardConfig", "FateBranchConfig",
    "SectTalentConfig",
]
WRITERS = {
    "WriteInt32": "int32", "WriteInt64": "int64", "WriteUInt32": "uint32",
    "WriteUInt64": "uint64", "WriteEnum": "enum", "WriteBool": "bool",
    "WriteString": "string", "WriteFloat": "float", "WriteDouble": "double",
    "WriteMessage": "message",
}


def compressed(data: bytes, offset: int) -> tuple[int, int]:
    head = data[offset]
    offset += 1
    if head < 0x80:
        return head, offset
    if head < 0xC0:
        return ((head & 0x3F) << 8) | data[offset], offset + 1
    if head < 0xE0:
        return (((head & 0x1F) << 24) | (data[offset] << 16)
                | (data[offset + 1] << 8) | data[offset + 2]), offset + 3
    raise ValueError("Invalid compressed metadata integer")


def integer_literal(instruction):
    name = instruction.opcode.name
    if name in ("ldc.i4", "ldc.i4.s"):
        return int(instruction.operand)
    if name == "ldc.i4.m1":
        return -1
    if name.startswith("ldc.i4.") and name[-1].isdigit():
        return int(name[-1])
    return None


class Inspector:
    def __init__(self, path: Path):
        self.pe = dnfile.dnPE(str(path))
        if self.pe.net is None:
            raise ValueError("Input has no managed CLR metadata")

    def type_ref(self, coded_index: int) -> str:
        tag, rid = coded_index & 3, coded_index >> 2
        tables = [self.pe.net.mdtables.TypeDef, self.pe.net.mdtables.TypeRef,
                  self.pe.net.mdtables.TypeSpec]
        if tag >= len(tables) or not rid:
            raise ValueError("Invalid TypeDefOrRef signature")
        row = tables[tag].rows[rid - 1]
        if hasattr(row, "TypeName"):
            return ".".join(filter(None, [str(row.TypeNamespace), str(row.TypeName)]))
        return f"TypeSpec#{rid}"

    def declared_type(self, field) -> str:
        data = field.Signature.value

        def parse(offset):
            element = data[offset]
            offset += 1
            scalars = {2: "bool", 3: "char", 4: "int8", 5: "uint8", 6: "int16",
                       7: "uint16", 8: "int32", 9: "uint32", 10: "int64",
                       11: "uint64", 12: "float", 13: "double", 14: "string"}
            if element in scalars:
                return scalars[element], offset
            if element in (0x11, 0x12):
                index, offset = compressed(data, offset)
                return self.type_ref(index), offset
            if element == 0x1D:
                inner, offset = parse(offset)
                return f"array<{inner}>", offset
            if element == 0x15:
                if data[offset] not in (0x11, 0x12):
                    raise ValueError("Unsupported generic signature")
                index, offset = compressed(data, offset + 1)
                count, offset = compressed(data, offset)
                arguments = []
                for _ in range(count):
                    inner, offset = parse(offset)
                    arguments.append(inner)
                return f"{self.type_ref(index)}<{','.join(arguments)}>", offset
            return f"unknown:{element:#x}", offset

        if not data or data[0] != 6:
            raise ValueError("Expected field signature")
        return parse(1)[0]

    def token_name(self, token) -> str:
        if not hasattr(token, "value"):
            return str(token)
        table, rid = token.value >> 24, token.value & 0xFFFFFF
        tables = {4: self.pe.net.mdtables.Field, 6: self.pe.net.mdtables.MethodDef,
                  10: self.pe.net.mdtables.MemberRef}
        if table in tables:
            return str(tables[table].rows[rid - 1].Name)
        return str(token)

    def extract(self, targets: list[str]):
        schemas, warnings = {}, []
        for typedef in self.pe.net.mdtables.TypeDef.rows:
            name = str(typedef.TypeName)
            if str(typedef.TypeNamespace) != "Proto" or name not in targets:
                continue
            methods = [m for m in typedef.MethodList if str(m.row.Name) == "WriteTo"]
            if len(methods) != 1:
                warnings.append(f"{name}: expected exactly one WriteTo")
                continue
            method = methods[0]
            body = CilMethodBody(CilMethodBodyReaderBytes(
                self.pe.get_data(method.row.Rva, 65536)))
            instructions = body.instructions
            field_rows = {f.row_index: f.row for f in typedef.FieldList}
            tags = [i for i, ins in enumerate(instructions)
                    if ins.opcode.name in ("call", "callvirt")
                    and self.token_name(ins.operand) == "WriteRawTag"]
            fields = []
            for position, index in enumerate(tags):
                instruction = instructions[index]
                try:
                    tag_bytes, k = [], index - 1
                    while k >= 0:
                        value = integer_literal(instructions[k])
                        if value is None:
                            break
                        tag_bytes.insert(0, value)
                        k -= 1
                    if (not tag_bytes or any(not 0 <= n <= 255 for n in tag_bytes)
                            or tag_bytes[-1] >= 128
                            or any(n < 128 for n in tag_bytes[:-1])):
                        raise ValueError("tag is not a literal canonical varint")
                    tag = sum((v & 127) << (7 * i) for i, v in enumerate(tag_bytes))
                    number, wire = tag >> 3, tag & 7
                    if not 0 < number < (1 << 29) or wire not in (0, 1, 2, 5):
                        raise ValueError("invalid protobuf tag")
                    end = tags[position + 1] if position + 1 < len(tags) else len(instructions)
                    segment = instructions[index + 1:end]
                    reference = next((ins for ins in segment
                                      if ins.opcode.name == "ldfld"
                                      and (ins.operand.value & 0xFFFFFF) in field_rows), None)
                    if reference is None:
                        raise ValueError("no local field reference after tag")
                    field = field_rows[reference.operand.value & 0xFFFFFF]
                    declared = self.declared_type(field)
                    repeated = "List`1<" in declared or declared.startswith("array<")
                    scalar = declared.split("<", 1)[1][:-1] if repeated else declared
                    value_writers = [self.token_name(ins.operand) for ins in segment
                                     if ins.opcode.name in ("call", "callvirt")
                                     and self.token_name(ins.operand) in WRITERS]
                    if not value_writers:
                        raise ValueError("no recognized value writer after tag")
                    # A packed list first writes its byte length with WriteInt32;
                    # the later loop writes the actual element type.
                    writer = value_writers[-1] if repeated else value_writers[0]
                    kind = WRITERS[writer]
                    if repeated and scalar in ("int32", "bool", "string", "float", "double"):
                        if kind != scalar:
                            raise ValueError("list element signature disagrees with value writer")
                    if any(f["field_number"] == number or f["name"] == str(field.Name)
                           for f in fields):
                        raise ValueError("duplicate number or field mapping")
                    fields.append({
                        "field_number": number, "name": str(field.Name), "field_type": kind,
                        "declared_type": declared, "repeated": repeated,
                        "packed": repeated and wire == 2 and scalar not in ("string", "bytes")
                                  and not scalar.startswith("Proto."),
                        "wire_type": wire,
                        "evidence": {"write_to_method_token": hex(0x06000000 | method.row_index),
                                     "write_to_rva": method.row.Rva,
                                     "tag_il_offset": hex(instruction.offset),
                                     "tag_bytes": tag_bytes, "tag_integer": tag,
                                     "field_il_offset": hex(reference.offset),
                                     "field_token": hex(reference.operand.value),
                                     "writer": writer, "signature_hex": field.Signature.value.hex()},
                    })
                except (ValueError, IndexError) as error:
                    warnings.append(f"{name} IL {instruction.offset:#x}: {error}")
            schemas[name] = {"full_name": f"Proto.{name}", "fields": fields,
                             "declared_field_count": len(typedef.FieldList),
                             "mapped_field_count": len(fields)}
            if len(fields) != len(typedef.FieldList):
                warnings.append(f"{name}: mapped {len(fields)} of {len(typedef.FieldList)} fields")
        return schemas, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dll", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--types", nargs="+", default=DEFAULT_TYPES)
    args = parser.parse_args()
    inspector = Inspector(args.dll)
    schemas, warnings = inspector.extract(args.types)
    report = {"source": {"path": str(args.dll.resolve()),
                          "sha256": hashlib.sha256(args.dll.read_bytes()).hexdigest(),
                          "method": "Static metadata and CIL WriteTo inspection; no assembly execution"},
              "schemas": schemas, "missing_types": sorted(set(args.types) - schemas.keys()),
              "warnings": warnings}
    decode, skipped = {}, {}
    for name, schema in schemas.items():
        decode[name] = {}
        for field in schema["fields"]:
            kind = field["field_type"]
            kind = "int32[]" if field["repeated"] and kind == "int32" else kind
            if ((field["repeated"] and kind != "int32[]")
                    or kind not in ("int32", "enum", "bool", "string", "float", "int32[]")):
                skipped.setdefault(name, []).append({k: field[k] for k in
                    ("field_number", "name", "declared_type", "field_type", "repeated")})
            else:
                decode[name][str(field["field_number"])] = {"name": field["name"], "type": kind}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in [("protobuf-schemas.json", report),
                              ("protobuf-decode-schemas.json", decode),
                              ("protobuf-decode-skipped.json", skipped)]:
        (args.output_dir / filename).write_text(json.dumps(content, ensure_ascii=False, indent=2),
                                               encoding="utf-8")
    print(json.dumps({"schemas": len(schemas), "mapped_fields": sum(len(s["fields"]) for s in schemas.values()),
                      "missing_types": report["missing_types"], "warnings": warnings}, ensure_ascii=False))
    return 1 if warnings or report["missing_types"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
