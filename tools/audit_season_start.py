"""Create a focused, reproducible static IL audit for seasonal opening effects."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from extract_schema import Inspector, CilMethodBody, CilMethodBodyReaderBytes


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/inspection/initial-fate-il.json'
DLL = ROOT / 'data/local/2026-11-06/raw/DarkSun.HotUpdate.dll'
METHOD = 'XianMoStrategyFunctions+<OnBattleStart>d__5.MoveNext'
RANGES = {
    1003: ('0x30f', '0x3de'), 1006: ('0x6d8', '0x7ac'),
    7036: ('0x17d7', '0x1845'), 7078: ('0x1b24', '0x1ba6'),
    7083: ('0x1be2', '0x1c3b'), 7098: ('0x1499', '0x14f7'),
    7103: ('0x1de0', '0x1e40'), 7123: ('0x2083', '0x2123'),
    15018: ('0x2340', '0x23d1'),
}
FINDINGS = {
    1003: 'Requires ownership and active switch. For each side independently delta=floor(current hp*p[0]/100), then ModifyMaxHp(delta,true), ModifyHp(delta,0,false,false,false). Uses hp, not maxHp.',
    1006: 'Requires ownership and active switch. For each side independently delta=floor(current hp*p[0]/100), then ModifyHp(-delta,0,false,false,false), ModifyMaxHp(-delta,true).',
    7036: 'Ownership required. Active switch controls only buff 13 +=p[0]. ModifyHp(p[1],0,false,false,false) executes even when the switch is off. No maxHp increase.',
    7078: 'Buff 3 +=1. If own lastRoundData.exp >= opponent lastRoundData.exp+p[0], buff 3 +=1 again. Equality satisfies the condition.',
    7083: 'delta=p[0]*GetWuXingCountInDeck(false), then ModifyMaxHp(delta,true), ModifyHp(delta,...). The helper includes additional card, talent, strategy and engraving interactions; counting distinct element names alone is incomplete.',
    7098: 'Buff 240 +=1 on owner. Opponent ModifyHp(-p[0],...), then ModifyMaxHp(-p[0],true).',
    7103: 'delta=current hp / p[0] with integer division (truncates toward zero); positive hp gives floor. ModifyMaxHp(delta,true), then ModifyHp(delta,...).',
    7123: 'Requires lastRoundData.life <= p[0]; bgt skips when greater, so equality applies. delta=current hp*p[1]/100 using integer division. ModifyMaxHp(delta,true), then ModifyHp(delta,...).',
    15018: 'Requires lastRoundData.handCards.Count >0. delta=current hp*p[0]/100 using integer division. ModifyMaxHp(delta,true), then ModifyHp(delta,...).',
}


def main():
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    method = next(row for row in source if row['method'] == METHOD)
    instructions = method['instructions']
    audit = {
        'schema_version':1, 'source_kind':'static_local_client_il',
        'current_server_verified':False,
        'sources':{
            'source_il':{'path':str(SOURCE.resolve()),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest()},
            'dll':{'path':str(DLL.resolve()),'sha256':hashlib.sha256(DLL.read_bytes()).hexdigest()},
        },
        'method':METHOD, 'method_token':method['token'],
        'owner_local_call_order':[int(instructions[i-1]['operand']) for i,ins in enumerate(instructions)
                                 if ins['operand']=='XianMoStrategyFunctions.HasXianMoStrategy'],
        'effects':[], 'supporting_methods':[],
        'limitations':[
            'Owner-local call order is shown; cross-owner and ordinary-talent interleaving is not established here.',
            'ModifyMaxHp and ModifyHp are effectful helpers; direct arithmetic covers only the isolated component without their additional interactions.',
            'Positive ModifyMaxHp deltas are modified by FateStrategy 394, season 7076 and buff 371; negative deltas by opponent buffs 416/667 and own buff 677, among further side effects.',
        ],
    }
    for identifier,(start,end) in RANGES.items():
        audit['effects'].append({'id':identifier,'finding':FINDINGS[identifier],
            'offset_range':[start,end], 'instructions':[ins for ins in instructions
                if int(start,16)<=int(ins['offset'],16)<=int(end,16)]})
    inspector = Inspector(DLL)
    for typedef in inspector.pe.net.mdtables.TypeDef.rows:
        if str(typedef.TypeName) != 'BattleCharacter':
            continue
        for method in typedef.MethodList:
            if str(method.row.Name) not in ('ModifyMaxHp','GetWuXingCountInDeck'):
                continue
            body = CilMethodBody(CilMethodBodyReaderBytes(inspector.pe.get_data(method.row.Rva,65536)))
            audit['supporting_methods'].append({'method':'BattleCharacter.'+str(method.row.Name),
                'token':hex(0x06000000 | method.row_index), 'rva':method.row.Rva,
                'instructions':[{'offset':hex(ins.offset),'op':ins.opcode.name,
                                 'operand':inspector.token_name(ins.operand)} for ins in body.instructions]})
    path = ROOT/'data/inspection/season-start-components-audit.json'
    path.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'path':str(path),'effects':list(RANGES),'supporting_methods':len(audit['supporting_methods'])}))


if __name__ == '__main__':
    main()
