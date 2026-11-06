import json,sys
from collections import Counter
for fn in sys.argv[1:]:
    c=Counter(); wins=Counter(); ex={}
    for line in open(fn):
        w=json.loads(line)
        if "error" in w: continue
        ds,de=w["start"]-w["context"], w["end"]+w["context"]
        seen=set()
        for d in w["departures"]:
            if not d["fromSteps"]: continue
            a,b=min(d["leavePos"],d["rejoinPos"]),max(d["leavePos"],d["rejoinPos"])
            dist = max(ds-1-b, a-(de+1), 0)
            if dist==0: continue
            k = "<=1kb" if dist<=1000 else "<=64kb" if dist<=65536 else "<=1Mb" if dist<=1e6 else ">1Mb"
            c[k]+=1; seen.add(k); ex.setdefault(k,(w["start"],w["end"],d["name"],d["leavePos"],d["rejoinPos"]))
        for k in seen: wins[k]+=1
    print(fn, dict(c), "windows", dict(wins)); print("   ", ex)
