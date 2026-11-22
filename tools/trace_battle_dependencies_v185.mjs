// Observe bytes actually read by this frozen engine, preserving every guard.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const read=fs.readFileSync.bind(fs),seen=new Set();
fs.readFileSync=function(p,...args){
  if(typeof p==='string'||p instanceof URL)seen.add(path.resolve(p instanceof URL?fileURLToPath(p):p));
  return read(p,...args);
};
const rows=JSON.parse(read(path.join(root,'runs/tactical-data/verified-subset-v185/starts.json'),'utf8'));
const {execute}=await import('./full_battle_bridge_web_v183r2.mjs');
let count=0;
for(const row of rows){const input=structuredClone(row.battle);input.include_trace=false;execute(input);count++;}
fs.writeFileSync(path.join(root,'runs/tactical-data/verified-subset-v185/runtime-read-files.json'),JSON.stringify({baselines:count,files:[...seen].sort()},null,2));
console.log(JSON.stringify({baselines:count,read_files:seen.size,client_binary_reads:[...seen].filter(p=>/\.(dll|exe)$/i.test(p))}));
