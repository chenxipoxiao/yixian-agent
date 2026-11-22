"""Extract local battle IL containing the seasonal runtime IDs or buff IDs."""
import hashlib
import json
from pathlib import Path

from extract_schema import Inspector, CilMethodBody, CilMethodBodyReaderBytes, integer_literal


def main():
    root=Path(__file__).resolve().parents[1]
    dll=root/'data/local/2026-11-06/raw/DarkSun.HotUpdate.dll'
    p=Inspector(dll)
    parents={r.NestedClass.row_index:r.EnclosingClass.row_index for r in p.pe.net.mdtables.NestedClass.rows}
    def name(rid):
        t=p.pe.net.mdtables.TypeDef.rows[rid-1]
        return name(parents[rid])+'+'+str(t.TypeName) if rid in parents else str(t.TypeName)
    targets={1005,1007,1008,1009,1010,3004,3011,3012,561,281,214,543,784}
    rows=[]
    for rid,t in enumerate(p.pe.net.mdtables.TypeDef.rows,1):
        n=name(rid)
        if n.split('+')[0] not in {'BattleCharacter','BattleExecuter','XianMoStrategyFunctions','BuffFunctions','BattleCard','CardFunctions','CardActionBase','CardItem','CardItemBase','ConfigExtension'}:
            continue
        for m in t.MethodList:
            if not m.row.Rva:continue
            body=CilMethodBody(CilMethodBodyReaderBytes(p.pe.get_data(m.row.Rva,131072)))
            found=sorted({integer_literal(i) for i in body.instructions}&targets)
            if found or (n=='ConfigExtension' and str(m.row.Name)=='CanUpgrade'):
                rows.append({'method':n+'.'+str(m.row.Name),'token':hex(0x06000000|m.row_index),
                    'found_literals':found,'instructions':[{'offset':hex(i.offset),'op':i.opcode.name,'operand':p.token_name(i.operand)} for i in body.instructions]})
    result={'source':str(dll),'sha256':hashlib.sha256(dll.read_bytes()).hexdigest(),
            'source_kind':'static_local_client_il','current_server_verified':False,'methods':rows}
    dest=root/'data/inspection/season-runtime-il.json'
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([{'method':r['method'],'literals':r['found_literals']} for r in rows]))


if __name__=='__main__':main()
