"""Build one blind judge pack per judge from any two screenshot folders.

usage: build_packs.py <workdir> <nameP> <dirP> <nameQ> <dirQ> [smokeP] [smokeQ]
<workdir>/packs/<judge>/{X,Y}/ gets the PNG+TXT files of one portal each, mapped by a fresh random
draw per judge; the key goes to <workdir>/keys.json, never inside a pack. judge-prompt.md must sit
in <workdir>. Names P/Q are only used in the key, never shown to a judge.
"""
import json, secrets, shutil, sys
from pathlib import Path

work = Path(sys.argv[1]); nameP, dirP, nameQ, dirQ = sys.argv[2], Path(sys.argv[3]), sys.argv[4], Path(sys.argv[5])
smoke = {nameP: Path(sys.argv[6]) if len(sys.argv) > 6 else None, nameQ: Path(sys.argv[7]) if len(sys.argv) > 7 else None}
src = {nameP: dirP, nameQ: dirQ}
keys = {}
for judge in ("claude", "grok", "codex"):
    pack = work / "packs" / judge
    if pack.exists():
        shutil.rmtree(pack)
    flip = secrets.randbelow(2)
    mapping = {"X": (nameP, nameQ)[flip], "Y": (nameP, nameQ)[1 - flip]}
    keys[judge] = mapping
    for label, name in mapping.items():
        out = pack / label; out.mkdir(parents=True)
        files = sorted(p for p in src[name].iterdir() if p.suffix in (".png", ".txt"))
        if smoke[name]:
            files += sorted(smoke[name].glob("save-*.png"))
        for f in files:
            shutil.copy2(f, out / f.name)
        lines = [f"# Portal {label} — files", "", "| File | What it shows |", "|---|---|"]
        for f in files:
            stem = f.stem
            if stem.startswith("save-"):
                what = "after saving: " + stem.split("-", 2)[2].replace("-", " ")
            elif stem.startswith("state-"):
                what = "state: " + stem[6:].replace("-", " ")
            else:
                parts = stem.split("-")
                view = "desktop" if "desktop" in parts else "phone"
                page = "-".join(parts[1:parts.index(view)]) if view in parts else stem
                what = f"{page} page, {view}" + (f", scroll position {parts[-1]}" if f.suffix == ".png" and parts[-1].isdigit() else ", visible text" if f.suffix == ".txt" else "")
            lines.append(f"| `{f.name}` | {what} |")
        (out / "INDEX.md").write_text("\n".join(lines) + "\n")
    shutil.copy2(work / "judge-prompt.md", pack / "PROMPT.md")
(work / "keys.json").write_text(json.dumps(keys, indent=1))
print({j: len(list((work / "packs" / j).rglob("*.png"))) for j in keys})
