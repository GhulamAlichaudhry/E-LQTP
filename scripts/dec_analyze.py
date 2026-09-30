#!/usr/bin/env python3
"""Summarize DEC lines (--decisionTrace): why the sink is / is not chosen."""
import sys, math, re, statistics as st
from collections import Counter
def parse(path):
    for line in open(path):
        if not line.startswith("DEC "): continue
        head, *cands = line.rstrip().split(" |")
        kv = dict(re.findall(r"(\w+)=(\S+)", head))
        C = {}
        for c in cands:
            j, vals = c.split(":"); q, R, ce, cd, cn = map(float, vals.split(","))
            C[int(j)] = dict(q=q, R=R, ce=ce, cd=cd, cn=cn)
        yield int(kv["at"]), int(kv["nh"]), C
def cls(x): return "nan" if math.isnan(x) else ("+inf" if x == math.inf else ("-inf" if x == -math.inf else ("<0" if x < 0 else ("0" if x == 0 else ">0"))))
for path in sys.argv[1:]:
    n = 0; sinkin = 0; sinkchosen = 0; reasons = Counter(); qcls_sink = Counter(); qcls_other = Counter()
    ce_sign_other = Counter(); sink_nei = []; other_nei = []; R_sign_other = Counter()
    for at, nh, C in parse(path):
        n += 1
        if 0 not in C: continue
        sinkin += 1; sinkchosen += nh == 0
        qs = C[0]["q"]; others = {j: v for j, v in C.items() if j != 0}
        qcls_sink[cls(qs)] += 1
        for v in others.values():
            qcls_other[cls(v["q"])] += 1; ce_sign_other[cls(v["ce"])] += 1; R_sign_other[cls(v["R"])] += 1; other_nei.append(v["cn"])
        sink_nei.append(C[0]["cn"])
        if not others: reasons["sink only candidate"] += 1; continue
        best = max(others.values(), key=lambda v: (v["q"] if not math.isnan(v["q"]) else -math.inf))["q"]
        if nh == 0:
            if math.isnan(qs) or any(math.isnan(v["q"]) for v in others.values()): reasons["chosen: NaN Q in set -> lowest-id tie-break (sink=0)"] += 1
            elif qs > best: reasons["chosen: sink Q strictly highest"] += 1
            elif qs == best: reasons["chosen: Q tie -> lowest id"] += 1
            else: reasons["chosen: other"] += 1
        else:
            reasons["passed over: relay Q > sink Q"] += 1
    print(f"== {path.split('/')[-1]}: decisions={n} sink_in_set={sinkin} sink_chosen={sinkchosen} ({sinkchosen/max(sinkin,1):.1%})")
    for k, v in reasons.most_common(): print(f"   {k}: {v}")
    print("   sink Q class:", dict(qcls_sink)); print("   relay Q class:", dict(qcls_other))
    print("   relay c_ene sign:", dict(ce_sign_other), " relay R sign:", dict(R_sign_other))
    print(f"   c_nei sink mean={st.mean(sink_nei):.3g}  relay median={st.median(other_nei):.3g} max={max(other_nei):.3g}")

def passed_over_terms(path):
    """For decisions where the sink was a candidate but a relay was chosen:
    ratio of chosen relay's reward terms to the sink's."""
    import statistics as st
    rn, re_, rd, rR, nei_wins, ene_wins, del_wins, n = [], [], [], [], 0, 0, 0, 0
    for at, nh, C in parse(path):
        if 0 not in C or nh in (0, -1) or nh not in C: continue
        s, r = C[0], C[nh]; n += 1
        nei_wins += r["cn"] > s["cn"]; ene_wins += r["ce"] > s["ce"]; del_wins += r["cd"] > s["cd"]
        rn.append(r["cn"] / s["cn"])
        if s["ce"] > 0 and r["ce"] > 0: re_.append(r["ce"] / s["ce"])
        if s["cd"] > 0: rd.append(r["cd"] / s["cd"])
    print(f"   passed-over n={n}: relay beats sink on c_nei {nei_wins/n:.1%}, on c_ene {ene_wins/n:.1%}, on c_del {del_wins/n:.1%}")
    print(f"   median ratio relay/sink: c_nei {st.median(rn):.3g}, c_ene {st.median(re_) if re_ else float('nan'):.3g}, c_del {st.median(rd) if rd else float('nan'):.3g}")
if __name__ == "__main__" and len(sys.argv) > 1:
    for p in sys.argv[1:]:
        print("==", p.split("/")[-1]); passed_over_terms(p)
