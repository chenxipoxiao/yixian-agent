// Explicit mirror identity is carried into diagnostics, never a live-player rewrite.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const digest='be042f5b719fdf7bb9e5d7e25eba672c173091894489c7aabf7d28fdd5398cf6';
const check=(ok,why)=>{if(!ok)throw new Error('mirror_context_unresolved:'+why);};
export function validateMirrorContext(root,input){
 const context=input.mirror_context;
 if(context===undefined)return null;
 const bytes=fs.readFileSync(path.join(root,'data/inspection/current-mirror-context-v129r2.json'));
 check(crypto.createHash('sha256').update(bytes).digest('hex')===digest,'evidence_changed');
 check(context!==null&&typeof context==='object'&&!Array.isArray(context)
  &&Object.keys(context).length===1&&Array.isArray(context.is_mirror)
  &&context.is_mirror.length===2&&context.is_mirror.every(v=>typeof v==='boolean')
  &&context.is_mirror.some(Boolean),'explicit_two_markers_required');
 check(input.civet!==null&&typeof input.civet==='object'
  &&Array.isArray(input.civet.is_mirror)&&input.civet.is_mirror.length===2
  &&context.is_mirror.every((v,i)=>input.civet.is_mirror[i]===v),'civet_marker_mismatch');
 return {evidence_sha256:digest,is_mirror:[...context.is_mirror],
  authoritative_mirror_balance_inferred:false,match_continuation_allowed:false,
  training_label_allowed:false};
}
