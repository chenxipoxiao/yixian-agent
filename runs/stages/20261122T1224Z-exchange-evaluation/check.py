import json,sys,hashlib,math
from collections import defaultdict,Counter
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path.cwd()))
from yixian.memory import Memory
from yixian.battle_subset_v185 import split_game
from yixian.combat_calibration import iter_selected_records
d=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def save(p,x):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(x,ensure_ascii=False,indent=2),'utf8');t.replace(p)
l=Path('runs/stages/latest.json');v=read(l);s=read(v['report']);m=Memory('runs/research.sqlite')
archive=Path('runs/analysis/20261117T084200Z-five-elements-44-exchanges').resolve()
sys.path.insert(0,str(archive))
import stats_v4 as recording
import subprocess
import gzip
cohort=Path(s['exchange_new_cohort']).parent
plan=read(cohort/'plan.json')
paths=read(cohort/'report.json')['local_paths']
weights_path=Path(s['exchange_imitation_trial']).with_name('weights-by-fold.json')
assert hashlib.sha256(weights_path.read_bytes()).hexdigest()==plan['weights_sha256']
weights=list(read(weights_path).values())
catalog={c['id']:c for c in read('data/local/2026-11-06/tables/CardConfig.json')}
shared_path=Path('runs/stages/20261116T110900Z-s2-opening-inputs/website-input-audit/longyao-shared.gz')
assert hashlib.sha256(shared_path.read_bytes()).hexdigest()==read(str(shared_path)+'.receipt.json')['sha256']
shared=recording.codec.shared(json.loads(gzip.decompress(shared_path.read_bytes()))[1])
def roster(raw):
 for _,before,after,_ in recording.codec.states(raw):
  for state in (before,after):
   players=state.get('players',{})
   if len(players)==8:return tuple(sorted(players))
 return None
dev=read(s['expanded_exchange_actions_check'])['sources']
seen=set()
for name in subprocess.check_output(['rg','--files','runs/stages','-g','r-*-decoded.json'],encoding='utf8').splitlines():
 path=Path(name);rid=path.name.split('-decoded')[0]
 if rid in dev:
  assert hashlib.sha256(path.read_bytes()).hexdigest()==dev[rid]
  seen.add(roster(read(path)))
results={};roster_flags={}
for item in plan['records']:
 rid=item['recording'];path=Path(paths.get(rid,cohort/item['path']))
 body=path.read_bytes()
 assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==item['git_blob']
 raw=recording.codec.recording(json.loads(gzip.decompress(body)),shared)
 assert raw['id']==rid and rid not in dev
 identity=roster(raw);roster_flags[rid]='unknown' if identity is None else ('duplicate' if identity in seen else 'distinct')
 seen.add(identity)
 if roster_flags[rid]=='duplicate':continue
 uid=raw['targetUid'];names=defaultdict(list);metrics=Counter();prior=None
 for card,entry in raw['catalog']['cards'].items():
  if type(entry.get('upgrade')) is int:names[entry.get('nameChinese'),entry['upgrade']].append(int(card))
 for n,b,a,event in recording.codec.states(raw):
  previous=prior;prior=None
  pub=b.get('players',{}).get(uid,{});bp=b.get('privatePlayer',{});ap=a.get('privatePlayer',{})
  acts=[x for x in event.get('humanActions',[]) if x.get('actorUid')==uid]
  if len(acts)!=1 or acts[0].get('kind')!='exchange':continue
  metrics['observed_single']+=1
  if pub.get('characterId')!=1000003 or b['gameMode']!=3 or b['seasonMechanic']!=10 or bp.get('uid')!=uid or ap.get('uid')!=uid:continue
  if any(x['id']==210 for x in pub['talents']):continue
  hand=bp['hand'];eligible=[c for c in hand if c>0 and c!=19];opts=list(dict.fromkeys(eligible))
  pair=recording.exchange_cards(acts[0],names)
  if not pair or len(opts)<2 or pair[0] not in opts or any(c not in catalog for c in opts):continue
  y,incoming=pair;expected=Counter(hand);expected[y]-=1;expected[incoming]+=1
  if +expected!=Counter(ap['hand']) or bp['deck']!=ap['deck'] or bp['exchangesRemaining']<=0 or bp['exchangesRemaining']-ap['exchangesRemaining']!=1:continue
  adjacent=previous==(n-1,b['round'],hand)
  prior=(n,b['round'],list(ap['hand']))
  def score(c):
   realm=catalog[c]['level']
   features={str(c):1,'realm':realm/5,'hand':hand.count(c)/4,'board':bp['deck'].count(c)/4,'above':int(realm>recording.phase(pub['phase']))}
   return sum(sum(w.get(k,0)*v for k,v in features.items()) for w in weights)/len(weights)
  last=eligible[-1];hybrid=last if adjacent else max(opts,key=score)
  metrics.update(n=1,last=int(last==y),hybrid=int(hybrid==y),wins=int(hybrid==y and last!=y),losses=int(hybrid!=y and last==y),adjacent=int(adjacent))
 results[rid]=metrics
total=sum(results.values(),Counter())
report=dict(metrics=total,by_recording=results,roster_checks=roster_flags,scope='Frozen recording-level comparison. Distinct eight-UID roster when available; no global game ID or repository-wide independent test asserted.')
save(d/'report.json',report)
msg=f"Frozen exchange evaluation {dict(total)} across {len(results)} recordings; rosters {dict(Counter(roster_flags.values()))}."
print(msg)
ev=m.append('finding','training',dict(statement=msg,claim='measured',evidence=[str(d/'report.json')]))
save(d/'conversation-review.json',dict(previous=s['conversation_review'],new_user_decisions=[],visible_boundary='continue scheduled task'))
s.update(prior_stage=v['report'],created_at_utc=datetime.now(timezone.utc).isoformat(),research_event=ev,iteration_status=msg,publication_statement=msg,exchange_new_evaluation=str(d/'report.json'),conversation_review=str(d/'conversation-review.json'),monitor_report=read('runs/monitoring/latest.json')['report'],next_training_hypothesis='Keep evaluation cohort out of further selection. Inspect observable stop/continue decisions and preparation action availability on development recordings.')
save(d/'stage-status.json',s);v.update(report=str(d/'stage-status.json'),run_dir=str(d),research_event=ev);save(l,v)








