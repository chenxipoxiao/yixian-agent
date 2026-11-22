"""Copy the runtime dependency closure into a unique, hash-checked release."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import argparse,hashlib,json,re,shutil,sys,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def closure():
    pending=[(ROOT/'tools/battle_subset_worker_v185r3.mjs',True)]
    pending += [(p,True) for p in list((ROOT/'external/yisim').glob('*.js'))+list((ROOT/'external/yisim').glob('*.json'))]
    observed=read(ROOT/'runs/tactical-data/verified-subset-v185/runtime-read-files.json')
    assert observed['baselines']==615
    pending += [(Path(p),False) for p in observed['files']]
    seen={};parsed=set()
    while pending:
        p,parse=pending.pop();p=p.resolve()
        if p in seen and (not parse or p in parsed):continue
        assert p.is_relative_to(ROOT) and p.is_file(),p
        if p.suffix.lower() in {'.dll','.exe','.zst','.pt'}:
            # This one assembly is read solely for the existing provenance hash
            # guards. It is not executed or accompanied by a game installation.
            allowed=ROOT/'data/local/2026-11-06/raw/DarkSun.HotUpdate.dll'
            if p!=allowed or sha(p)!='0d4a4a876963f2cc35a41d46109bf8c6fb01d90e6ca9c0d67780e462221499d6':
                raise ValueError('Unexpected runtime dependency '+str(p))
        seen[p]=sha(p)
        if not parse:continue
        parsed.add(p)
        if p.suffix in {'.js','.mjs'}:
            text=p.read_text('utf8')
            for rel in re.findall(r"(?:from\s*|import\s*\()['\"](\.[^'\"]+)['\"]",text):
                q=(p.parent/rel).resolve()
                if q.is_file():pending.append((q,True))
            # Non-code reads come from the traced full calibrated input pool.
            # A new lazy dependency remains a hard error, never an absent=zero
            # fallback. The server rejects that entire counterfactual state.
    return seen

def main(out,inspect):
    paths=closure()
    if inspect:
        print(json.dumps({'files':len(paths),'bytes':sum(p.stat().st_size for p in paths),
            'largest':[(str(p.relative_to(ROOT)),p.stat().st_size) for p in sorted(paths,key=lambda p:p.stat().st_size,reverse=True)[:15]],
            'extensions':dict(Counter(p.suffix for p in paths))},ensure_ascii=False));return
    out.mkdir(parents=True,exist_ok=False)
    py=['yixian/__init__.py','yixian/battle_subset_v185.py','tools/run_battle_subset_v185.py','tools/train_battle_subset_v185.py',
        'yixian/research.py','yixian/memory.py']
    v3=read(ROOT/'runs/pretraining/20261112T020700Z-tactical-v3-pilot/contract.json')
    for name,h in v3['source_sha256'].items():
        if sha(ROOT/name)!=h:raise ValueError('Warm-start code changed '+name)
        py.append(name)
    for name in py:paths[ROOT/name]=sha(ROOT/name)
    weight='runs/pretraining/20261112T020700Z-tactical-v3-pilot/selected-policy.pt'
    paths[ROOT/weight]=sha(ROOT/weight)
    for p in (ROOT/'external/yisim/node_modules').rglob('*'):
        if p.is_file():paths[p]=sha(p)
    for p,h in paths.items():
        target=out/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
        assert sha(target)==h
    target=out/'data/starts.json';target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'runs/tactical-data/verified-subset-v185/starts.json',target)
    shutil.copyfile(ROOT/'runs/tactical-data/verified-subset-v185/manifest.json',out/'data/source-manifest.json')
    config={'scope':'longyao_verified_subset_battle_order_v185','seed':2026111804,'bootstrap_seed':2026111805,
        'segment_seconds':6600,'workers':4,'max_updates':1200,'validation_interval':200,'patience':4,
        'batch_size':64,'eval_batch_size':192,'learning_rate':0.00005,
        'warm_start':weight,'warm_start_sha256':sha(ROOT/weight),
        'card_table':'data/local/2026-11-06/tables/CardConfig.json',
        'card_table_sha256':sha(ROOT/'data/local/2026-11-06/tables/CardConfig.json'),
        'project_root':'/home/ubuntu/yixian-agent','user_authorization':'2026-11-18: train confirmed battles remotely while completing local mechanisms',
        'S2_gate_exception':'restricted simple-schema calibrated subset only; no overall S2 promotion',
        'reward':'new frozen-engine winner +/-1 plus 0.1*tanh(signed terminal HP difference/50)',
        'opponent':'3 predeclared numeric scripts conditioned on earlier public learner board; original table and same learner career',
        'policy':'v3 warm start; own-card-only order proposal distilled from shared-panel counterfactual search',
        'not_exact_resume_from_v3':True,'full_match_training':False,'independent_acceptance':False}
    write(out/'run-config.json',config)
    manifest={'schema':'isolated-battle-training-release-v185','created_utc':datetime.now(timezone.utc).isoformat(),
        'sha256':{p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
        'full_game_client_or_raw_replay_archives_included':False,'source_runtime':'v183r2',
        'hash_only_source_assembly_included':True,'source_assembly_executed':False,
        'old_sources_or_checkpoints_overwritten':False}
    write(out/'package-manifest.json',manifest)
    archive=out.with_suffix('.tar.gz')
    with tarfile.open(archive,'w:gz') as tar:
        for p in sorted(out.rglob('*')):
            if p.is_file():tar.add(p,arcname=p.relative_to(out).as_posix())
    write(out.with_suffix('.receipt.json'),{'files':len(manifest['sha256']),'unpacked_bytes':sum(p.stat().st_size for p in out.rglob('*') if p.is_file()),
        'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'manifest_sha256':sha(out/'package-manifest.json')})
    print(out.with_suffix('.receipt.json').read_text('utf8'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--inspect',action='store_true');a=p.parse_args();main(a.out,a.inspect)
