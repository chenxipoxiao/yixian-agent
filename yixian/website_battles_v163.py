"""Six exact dream variants; inherited source ownership and unknown-state gates."""
import hashlib,json
from pathlib import Path
from . import website_battles_v161 as previous
ROOT=Path(__file__).resolve().parents[1]
UnresolvedBattle=previous.UnresolvedBattle
ORIGIN=previous.ORIGIN
PROOF_SHA='e6a1c5b999a580ed70f4e7bdf6f0f4490d6d40117c98a3e77c78bc1bd0667863'
def extension_contract():
 b=(ROOT/'data/inspection/current-dream-formations-v163.json').read_bytes()
 if hashlib.sha256(b).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('dream_formations_v163:evidence_changed')
 f=json.loads(b)
 for p,h in f['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('dream_formations_v163:source_changed:'+p)
 return f
def compiler():
 facts=extension_contract();view=previous.compiler();old_catalogue=view.catalogue
 def catalogue():
  cards,mapping,talents,season=old_catalogue()
  mapping=dict(mapping)
  for c in facts['cards']:
   if c['raw_id'] in mapping or c['runtime_id'] in mapping.values():raise UnresolvedBattle('dream_formations_v163:alias_collision')
   if cards[c['raw_id']]!=c['config']:raise UnresolvedBattle('dream_formations_v163:config_changed')
   mapping[c['raw_id']]=c['runtime_id']
  return cards,mapping,talents,season
 view.catalogue=catalogue
 return view
def compile_case(case,view,tables):
 return previous.compile_case(case,view,tables)
