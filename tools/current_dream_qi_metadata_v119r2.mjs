import {dreamQiFlowerFacts} from './current_dream_qi_flower_v119.mjs';
import {dreamBasicsFacts} from './current_dream_basics_v93r2.mjs';
export function dreamQiMetadata(root){
 const lower=dreamBasicsFacts(root).cards.filter(c=>c.base_id===1000067);
 return [...lower,...dreamQiFlowerFacts(root).cards];
}
