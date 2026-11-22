from pathlib import Path
from collections import Counter,defaultdict
from statistics import mean
import json,hashlib,fcntl,torch,time
d=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def tensor(v):return torch.tensor(v,dtype=torch.float64,device="cuda")
def run():
    start=time.monotonic()
    p=read(d/"plan.json")
    assert sha(d/"train.py")==p["script"] and sha(d/"rows.json")==p["rows"]
    rows=read(d/"rows.json");pairs=[];counts=Counter();val=[]
    for r in rows:
        x,b,w,u=map(tensor,(r["x"],r["base"],r["wins"],r["utility"]))
        if r["split"]=="validation":
            val.append((r["game"],x,b,w,u));continue
        assert r["split"]=="train"
        i,j=torch.triu_indices(len(x),len(x),offset=1,device="cuda")
        mask=w[i]!=w[j];i,j=i[mask],j[mask]
        if len(i):
            sign=(w[i]-w[j]).sign()
            pairs.append((r["game"],(x[i]-x[j])*sign[:,None],(b[i]-b[j])*sign))
            counts[r["game"]]+=1
    assert not set(counts)&{v[0] for v in val}
    x=torch.cat([x for g,x,b in pairs]);offset=torch.cat([b for g,x,b in pairs])
    wt=torch.cat([torch.full_like(b,1/(len(counts)*counts[g]*len(b))) for g,x,b in pairs])
    coef=torch.zeros(x.shape[1],device="cuda",dtype=x.dtype,requires_grad=True)
    opt=torch.optim.Adam([coef],lr=p["lr"])
    for _ in range(p["steps"]):
        loss=(wt*torch.nn.functional.softplus(-(offset+x@coef))).sum()+p["penalty"]*coef.square().sum()
        opt.zero_grad();loss.backward();opt.step()
    groups=defaultdict(list);changed=0
    for g,x,b,w,u in val:
        a=int(b.argmax());z=int((b+x@coef).argmax())
        changed+=int(a!=z)
        groups[g].append([w[a].item()/3,w[z].item()/3,u[a].item(),u[z].item()])
    games={g:list(map(mean,zip(*vs))) for g,vs in groups.items()}
    means=list(map(mean,zip(*games.values())))
    (d/"weights.json").write_text(json.dumps(coef.tolist()))
    result=dict(means=means,games=games,changed=changed,informative_games=len(counts),informative_views=len(pairs),pairs=sum(len(b) for g,xx,b in pairs),selected="win_pairs" if (means[1],means[3])>(means[0],means[2]) else "v3",elapsed_s=time.monotonic()-start,weight_hash=sha(d/"weights.json"))
    (d/"report.json").write_text(json.dumps(result));print(means,changed)
with Path("/home/ubuntu/yixian-agent/runs/tactical-gpu.lock").open("a") as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run()

