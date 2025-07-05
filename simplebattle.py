#!/usr/bin/env python3
# BattleSim Menu Edition – NVDA‑friendly / Arrow‑key UI
import json, socket, threading, random, time, pathlib, sys, os, struct, ctypes, msvcrt

# ── NVDA speech helper ────────────────────────────────────────
def speak(text: str):
    bits = struct.calcsize("P") * 8
    dll  = "nvdaControllerClient64.dll" if bits == 64 else "nvdaControllerClient32.dll"
    path = os.path.join(os.path.dirname(__file__), dll)
    try:
        ctypes.windll.LoadLibrary(path).nvdaController_speakText(text)
    except Exception:
        pass  # NVDA not running or DLL missing

# ── logger & say() ────────────────────────────────────────────
LOG = "battle_log.txt"
def say(*parts):
    line = " ".join(map(str, parts))
    print(line, flush=True)
    pathlib.Path(LOG).open("a", encoding="utf-8").write(line + "\n")
    speak(line)

# ── keyboard helper (arrow keys) ─────────────────────────────
def get_key():
    k = msvcrt.getch()
    if k in b"\x00\xe0":   # special key prefix
        k = msvcrt.getch()
        return {b"H":"UP", b"P":"DOWN", b"K":"LEFT", b"M":"RIGHT"}.get(k, "")
    if k == b"\r": return "ENTER"
    if k == b"\x1b": return "ESC"
    return k.decode(errors="ignore")

def pick_menu(options, speak_each=True):
    idx = 0
    while True:
        for i,txt in enumerate(options):
            mark = "→ " if i==idx else "  "
            print(f"{mark}{txt}")
        if speak_each: speak(options[idx])
        k = get_key()
        print("\x1b[{}A".format(len(options)), end="")  # move cursor up
        if k=="UP":   idx=(idx-1)%len(options)
        if k=="DOWN": idx=(idx+1)%len(options)
        if k=="ENTER":
            print("\x1b[{}B".format(len(options)))      # move back down
            return idx

# ── misc helpers ─────────────────────────────────────────────
PORT, BUF = 5005, 4096
def send(s,o): s.sendall((json.dumps(o)+"\n").encode())
def recv(sock,q):
    buf=b""
    while (c:=sock.recv(BUF)):
        buf+=c
        while b"\n" in buf:
            ln,buf=buf.split(b"\n",1)
            q.append(json.loads(ln.decode()))

def load_team():
    return json.load(open("myteam.json", "r", encoding="utf-8"))

def next_alive(team, idx):
    n=len(team["party"])
    for _ in range(n):
        if team["party"][idx]["hp"]>0: return idx
        idx=(idx+1)%n
    return None

# ── simple damage (strength vs defense) ──────────────────────
def calc_dmg(att, dfn):
    return max(5, (att["strength"]//4) - (dfn["defense"]//10) + random.randint(0,10))

# ── battle loop ──────────────────────────────────────────────
def battle(host):
    me  = load_team()
    size_req = int(input("Battle size 1‑6 (Enter=6): ") or "6")
    size_req = max(1, min(6, size_req))

    # connect
    if host:
        s=socket.socket(); s.bind(("",PORT)); s.listen(1)
        say("Waiting for opponent on port", PORT)
        conn,_=s.accept()
    else:
        ip=input("Host IP (127.0.0.1): ") or "127.0.0.1"
        conn=socket.socket(); conn.connect((ip,PORT))
    q=[]; threading.Thread(target=recv,args=(conn,q),daemon=True).start()
    send(conn, {"team":me,"size":size_req})

    foe=None
    while foe is None:
        if q:
            m=q.pop(0); foe=m["team"]
            size=min(size_req, m["size"], len(me["party"]), len(foe["party"]))

    # ensure basic stats exist
    for t in (me, foe):
        for mon in t["party"]:
            mon.setdefault("strength", random.randint(120,320))
            mon.setdefault("defense",  random.randint( 80,250))
            mon.setdefault("speed",    random.randint(100,300))

    say(f"\nBattle start! {me['name']} vs {foe['name']}  ({size}‑on‑{size})")

    me_idx  = list(range(size))
    foe_idx = list(range(size))
    ptr_me = ptr_foe = 0
    my_turn = host

    while True:
        if not any(me ["party"][i]["hp"]>0 for i in me_idx):
            say("You lose!"); break
        if not any(foe["party"][i]["hp"]>0 for i in foe_idx):
            say("You win!"); break

        if my_turn:
            ai = next_alive(me, me_idx[ptr_me])
            if ai is None: my_turn=False; continue
            mon = me["party"][ai]

            say(f"\n{mon['species']} HP {mon['hp']}")
            action = pick_menu(["Attack","Switch Manamon","View Enemy Info"])
            if action==0:   # Attack
                mv_i = pick_menu(mon["moves"])
                # target selection (only if >1 living foes)
                living = [i for i in foe_idx if foe["party"][i]["hp"]>0]
                if len(living) == 1:
                    tgt = living[0]
                else:
                    labels=[f"{foe['party'][i]['species']} (HP {foe['party'][i]['hp']})" for i in living]
                    tgt = living[pick_menu(labels)]
                foe_mon=foe["party"][tgt]
                damage = calc_dmg(mon, foe_mon)
                foe_mon["hp"]=max(0, foe_mon["hp"]-damage)
                say(f"{mon['species']} used {mon['moves'][mv_i]} → foe {foe_mon['species']} HP {foe_mon['hp']}")
                send(conn, {"cmd":"atk","src":ai,"dst":tgt,
                            "move":mon["moves"][mv_i],"dmg":damage})

            elif action==1: # Switch
                choices=[i for i in range(len(me["party"])) if me["party"][i]["hp"]>0 and i not in me_idx]
                if not choices:
                    say("No healthy substitutes."); continue
                lbl=[f"{me['party'][i]['species']} (HP {me['party'][i]['hp']})" for i in choices]
                sel=pick_menu(lbl)
                me_idx[ptr_me]=choices[sel]
                send(conn, {"cmd":"switch","slot":choices[sel]})
                say(f"Switched to {me['party'][choices[sel]]['species']}")

            else:           # View enemy info
                tgt=next_alive(foe, foe_idx[ptr_foe])
                foe_mon=foe["party"][tgt]
                say(f"Enemy {foe_mon['species']} – HP {foe_mon['hp']} – Level {foe_mon['level']}")
                say("Press H for HP, L for Level, M for Name, or any key to continue.")
                key=get_key().lower()
                if key=="h": say(f"HP {foe_mon['hp']}")
                elif key=="l": say(f"Level {foe_mon['level']}")
                elif key=="m": say(f"Name {foe_mon['species']}")
                continue  # choose action again

            ptr_me  = (ptr_me+1)%size
            my_turn = False

        else:  # waiting for foe
            say("\nWaiting…")
            while not q: time.sleep(0.05)
            m=q.pop(0)
            if m["cmd"]=="switch":
                foe_idx[ptr_foe]=m["slot"]
            else:
                mv,dmg,dst = m["move"], m["dmg"], m["dst"]
                me["party"][dst]["hp"]=max(0, me["party"][dst]["hp"]-dmg)
                say(f"Foe used {mv} → your {me['party'][dst]['species']} HP {me['party'][dst]['hp']}")
            ptr_foe = (ptr_foe+1)%size
            my_turn = True

    say("Press Enter to close."); input()
    conn.close()

# ── main ─────────────────────────────────────────────────────
if __name__ == "__main__":
    battle(input("h=host  j=join : ").lower()=="h")
