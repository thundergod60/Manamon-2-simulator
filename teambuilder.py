#!/usr/bin/env python3
import json, difflib, re, pathlib

MOVE_FILE = "manamon move list.txt"
OUT_JSON  = "myteam.json"

def norm(s): return re.sub(r"[^a-z]", "", s.lower())

# load move list
lines = pathlib.Path(MOVE_FILE).read_text(encoding="utf-8").splitlines()
MOVES = [re.split(r"\.\s+", ln, 1)[1].replace("_", " ").strip() for ln in lines if ". " in ln]
LOOK = {norm(m): m for m in MOVES}

def ask_move(n):
    while True:
        raw = input(f"    Move {n}: ").strip()
        k = norm(raw)
        if k in LOOK:
            return LOOK[k]
        # 10 best fuzzy matches
        cand = difflib.get_close_matches(k, LOOK.keys(), n=10, cutoff=0.5)
        if cand:
            print("    Not found. Close matches:")
            for c in cand: print("      ", LOOK[c])
        else:
            print("    Move not recognised. Try again.")

print("=== Team Builder (auto‑suggest moves) ===")
name = input("Trainer name: ").title().strip() or "Trainer"
party=[]

for slot in range(1,7):
    sp = input(f"\nSpecies for slot {slot} (Enter to finish): ").title().strip()
    if not sp: break
    lvl=int(input("  Level (default 25): ") or "25")
    base_hp=60+lvl*4
    hp_in=input(f"  Max HP (Enter = {base_hp}): ").strip()
    hp=int(hp_in) if hp_in else base_hp
    moves=[ask_move(i+1) for i in range(4)]
    party.append({"species":sp,"level":lvl,"hp":hp,"moves":moves})

json.dump({"name":name,"party":party}, open(OUT_JSON,"w",encoding="utf-8"), indent=2)
print("\nSaved team to", OUT_JSON)
