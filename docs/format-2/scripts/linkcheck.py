import subprocess, sys
D=sys.argv[1]; s=int(float(sys.argv[2])*1e6)//65536*65536
q=lambda k: [l.split("\t") for l in subprocess.run(["tabix",f"{D}/chr22.{k}.bed.gz",f"GRCh38#0#chr22:{s+1}-{s+1}"],capture_output=True,text=True).stdout.splitlines()]
def dec(t):
    o,p=[],0
    for i,v in enumerate(map(int,t.split(","))):
        r=v%2; p=(v-r)//2 if i==0 else p+(v-r)//2; o.append(f"{p}{'-' if r else '+'}")
    return o
flip=lambda e:e[:-1]+('+' if e[-1]=='-' else '-')
canon=lambda a,b:min((a,b),(flip(b),flip(a)))
imp=set()
for r in q("walks"):
    st=dec(r[8]); imp.update(canon(a,b) for a,b in zip(st,st[1:]))
f={canon(r[3],r[4]) for r in q("links")}
print(s, "file",len(f),"implied",len(imp),"file-implied",len(f-imp),"implied-file",len(imp-f))
