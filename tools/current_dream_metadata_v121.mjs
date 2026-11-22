import {dreamQiMetadata as prior} from './current_dream_qi_metadata_v119r2.mjs';
import {dreamRejuvenationFacts} from './current_dream_rejuvenation_v121.mjs';
export function dreamQiMetadata(root){return [...prior(root),...dreamRejuvenationFacts(root).cards];}
