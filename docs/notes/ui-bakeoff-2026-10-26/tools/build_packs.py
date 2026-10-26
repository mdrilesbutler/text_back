"""Build one blind judge pack per judge: X/ and Y/ mapped to A/B by a fresh random draw each.

The key goes to keys.json beside this script, never inside a pack.
"""
import json, secrets, shutil
from pathlib import Path

S = Path(__file__).resolve().parent
PAGES = {"01": "sign-in", "02": "enter-code"}
keys = {}
for judge in ("claude", "grok", "codex"):
    pack = S / "packs" / judge
    if pack.exists():
        shutil.rmtree(pack)
    flip = secrets.randbelow(2)
    mapping = {"X": "AB"[flip], "Y": "AB"[1 - flip]}
    keys[judge] = mapping
    for label, src in mapping.items():
        out = pack / label; out.mkdir(parents=True)
        files = sorted(p for p in (S / "view" / src).iterdir() if p.suffix in (".png", ".txt"))
        files += sorted((S / "smoke" / src).glob("save-*.png"))
        for f in files:
            shutil.copy2(f, out / f.name)
        lines = [f"# Portal {label} — files", "", "| File | What it shows |", "|---|---|"]
        for f in files:
            stem = f.stem
            if stem.startswith("save-"):
                what = "after saving: " + stem.split("-", 2)[2].replace("-", " ")
            else:
                parts = stem.split("-")
                view = "desktop" if "desktop" in parts else "phone"
                page = "-".join(parts[1:parts.index(view)])
                what = f"{page} page, {view}" + (f", scroll position {parts[-1]}" if f.suffix == ".png" else ", visible text")
            lines.append(f"| `{f.name}` | {what} |")
        (out / "INDEX.md").write_text("\n".join(lines) + "\n")
    shutil.copy2(S / "judge-prompt.md", pack / "PROMPT.md")
(S / "keys.json").write_text(json.dumps(keys, indent=1))
print({j: len(list((S / "packs" / j).rglob("*.png"))) for j in keys})
