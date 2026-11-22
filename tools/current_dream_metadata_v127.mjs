import {dreamQiMetadata as prior} from './current_dream_metadata_v122.mjs';
import {dreamBrushLoadFacts} from './current_dream_brush_load_v127.mjs';
export function dreamQiMetadata(root){return [...prior(root),...dreamBrushLoadFacts(root).cards];}
