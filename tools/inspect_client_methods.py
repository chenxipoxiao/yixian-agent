"""Read-only targeted IL extraction for versioned combat compatibility audits."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.extract_schema import Inspector,CilMethodBody,CilMethodBodyReaderBytes

def extract(owners,method_names,tokens,output,constant_reads=()):
    dll=ROOT/'data/local/2026-11-06/raw/DarkSun.HotUpdate.dll'
    i=Inspector(dll);types=i.pe.net.mdtables.TypeDef.rows
    nested={n.NestedClass.row_index:n.EnclosingClass.row_index for n in i.pe.net.mdtables.NestedClass.rows}
    def type_name(rid):
        t=types[rid-1];name='.'.join(filter(None,[str(t.TypeNamespace),str(t.TypeName)]))
        return type_name(nested[rid])+'+'+name if rid in nested else name
    mo,fo={},{}
    for rid,t in enumerate(types,1):
        for m in t.MethodList:mo[m.row_index]=type_name(rid)
        for f in t.FieldList:fo[f.row_index]=type_name(rid)
    def operand(o):
        if not hasattr(o,'value'):return o if isinstance(o,(int,str,list)) or o is None else str(o)
        table,rid=o.value>>24,o.value&0xffffff
        if table==0x70:return str(i.pe.net.user_strings.get(rid))
        name=i.token_name(o)
        if table==6:name=mo[rid]+'.'+name
        if table==4:name=fo[rid]+'.'+name
        return name
    methods=[];reads=[]
    for rid,m in enumerate(i.pe.net.mdtables.MethodDef.rows,1):
        if not m.Rva:continue
        owner,name=mo[rid],str(m.Name)
        wanted=any(owner==o or owner.startswith(o+'+') for o in owners) or name in method_names or 0x06000000|rid in tokens
        if not wanted and not constant_reads:continue
        try:body=CilMethodBody(CilMethodBodyReaderBytes(i.pe.get_data(m.Rva,1_000_000)))
        except Exception as e:
            if wanted:raise
            continue
        instructions=[{'offset':hex(s.offset),'op':s.opcode.name,'operand':operand(s.operand)} for s in body.instructions]
        if wanted:methods.append({'owner':owner,'method':name,'token':hex(0x06000000|rid),'rva':m.Rva,'instructions':instructions})
        for n,s in enumerate(instructions):
            if s['op'] in ('ldc.i4','ldc.i4.s') and s['operand'] in constant_reads:
                reads.append({'owner':owner,'method':name,'token':hex(0x06000000|rid),'constant':s['operand'],
                    'window':instructions[max(0,n-5):min(len(instructions),n+12)]})
    constants=[]
    for c in i.pe.net.mdtables.Constant.rows:
        raw=c.Value.value
        if len(raw)==4 and hasattr(c.Parent.row,'Name'):
            constants.append({'owner':fo.get(c.Parent.row_index,''),'name':str(c.Parent.row.Name),'value':int.from_bytes(raw,'little',signed=True)})
    result={'dll_sha256':hashlib.sha256(dll.read_bytes()).hexdigest(),'methods':methods,'constant_reads':reads,'enum_constants':constants}
    with output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    return {'output':str(output),'methods':len(methods),'reads':len(reads)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--owners',nargs='*',default=[])
    p.add_argument('--methods',nargs='*',default=[]);p.add_argument('--tokens',nargs='*',default=[])
    p.add_argument('--constants',nargs='*',type=int,default=[]);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(extract(a.owners,a.methods,[int(t,0) for t in a.tokens],a.out,a.constants)))
