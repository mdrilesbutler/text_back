"""Read a judging workdir and print each judge's scores per real portal name.

usage: scores.py <workdir>   (expects <workdir>/keys.json and <workdir>/judges/{claude,grok,codex}.md)
Prints one row per (judge, portal) with the ten criteria, the total and the verdict, unblinded with keys.json.
"""
import json, re, sys
from pathlib import Path

W = Path(sys.argv[1]); keys = json.loads((W / "keys.json").read_text())
CRIT = ["a1", "a2", "b1", "b2", "c1", "c2", "d1", "d2", "e1", "e2"]
out = {}
for judge, mapping in keys.items():
    f = W / "judges" / f"{judge}.md"
    text = f.read_text() if f.exists() else ""
    verdict = re.findall(r"VERDICT:\s*WINNER\s*([XY])", text)
    for label in ("X", "Y"):
        m = re.search(rf"^\|\s*\**{label}\**\s*\|((?:\s*\d\s*\|){{10}})\s*\**(\d+)\**\s*\|", text, re.M)
        row = [int(x) for x in re.findall(r"\d", m.group(1))] if m else None
        out.setdefault(judge, {})[mapping[label]] = {"scores": dict(zip(CRIT, row)) if row else None,
                                                     "total": int(m.group(2)) if m else None}
    out[judge]["winner"] = mapping[verdict[-1]] if verdict else None
print(f"{'judge':7} {'portal':7} " + " ".join(f"{c:>2}" for c in CRIT) + "  total  winner")
for judge, d in out.items():
    for name, v in d.items():
        if name == "winner": continue
        s = v["scores"] or {}
        print(f"{judge:7} {name:7} " + " ".join(f"{s.get(c, '-'):>2}" for c in CRIT) + f"  {v['total'] or '-':>5}  {d['winner'] if d['winner']==name else ''}")
(W / "scores.json").write_text(json.dumps(out, indent=1))
