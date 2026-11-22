import {dreamQiMetadata as prior} from './current_dream_metadata_v121.mjs';
import {dreamExerciseFacts} from './current_dream_exercise_v122.mjs';
export function dreamQiMetadata(root){return [...prior(root),...dreamExerciseFacts(root).cards];}
