"""Monitor-visible entry point and append-only experiment lifecycle."""
from pathlib import Path
import argparse,json,sys,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.run_battle_subset_v185 import main,read
from yixian.memory import Memory
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--resume',action='store_true');p.add_argument('--experiment-id',required=True)
    a=p.parse_args();cfg=read(ROOT/'run-config.json');memory=Memory(Path(cfg['project_root'])/'runs/research.sqlite')
    if not a.resume:memory.record_experiment(a.experiment_id,'running',{'run_dir':str(a.out)},role='training')
    try:
        main(a);status=read(a.out/'status.json')
        if status['status']=='completed':memory.record_experiment(a.experiment_id,'completed',status,role='training')
        else:memory.append('finding','training',{'statement':'Frozen subset training saved a resumable segment','claim':'measured','evidence':[str(a.out/'status.json')],'experiment_id':a.experiment_id})
    except BaseException:
        memory.record_experiment(a.experiment_id,'failed',{'traceback':traceback.format_exc(),'run_dir':str(a.out)},role='training');raise
