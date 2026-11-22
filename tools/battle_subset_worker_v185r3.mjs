// Versioned Windows-evidence-path adapter; source bytes and SHA checks unchanged.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import readline from 'node:readline';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const originalRead=fs.readFileSync.bind(fs);
fs.readFileSync=function(p,...args){
  if(typeof p==='string' && p.startsWith(root+path.sep))p=p.replaceAll('\\','/');
  return originalRead(p,...args);
};
const {execute}=await import('./full_battle_bridge_web_v183r2.mjs');
for await (const line of readline.createInterface({input:process.stdin,crlfDelay:Infinity})) {
  try {
    const inputs=JSON.parse(line);
    if(!Array.isArray(inputs)||inputs.length>128)throw new Error('Bounded batch required');
    const out=inputs.map(input=>{
      try {
        const r=execute(input);
        return Object.fromEntries(['terminated','truncated','winner','hp_delta','turns','used_randomness','termination_reason'].map(k=>[k,r[k]]));
      } catch(e) {return {unresolved:true,reason:e.message,error_type:e.name};}
    });
    process.stdout.write(JSON.stringify(out)+'\n');
  } catch(e) {process.stdout.write(JSON.stringify({worker_error:e.message})+'\n');}
}
