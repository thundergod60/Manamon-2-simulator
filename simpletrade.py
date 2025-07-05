#!/usr/bin/env python3
import json, socket, threading

PORT=5006; BUF=4096
def load(): return json.load(open("myteam.json","r",encoding="utf-8"))
def save(t): json.dump(t,open("myteam.json","w",encoding="utf-8"),indent=2)
def send(s,o): s.sendall((json.dumps(o)+"\n").encode())
def recv(s,q):
    buf=b""
    while (c:=s.recv(BUF)):
        buf+=c
        while b"\n" in buf:
            line,buf=buf.split(b"\n",1); q.append(json.loads(line.decode()))

def pick(team):
    for i,m in enumerate(team["party"],1):
        print(f" {i}. {m['species']}  L{m['level']}")
    return int(input("Slot #: ") or "1")-1

def trade(host):
    me=load()
    if host:
        s=socket.socket(); s.bind(("",PORT)); s.listen(1)
        print("Waiting on",PORT); c,_=s.accept()
    else:
        ip=input("Host IP (127.0.0.1): ") or "127.0.0.1"
        c=socket.socket(); c.connect((ip,PORT))
    q=[]; threading.Thread(target=recv,args=(c,q),daemon=True).start()

    while True:
        my_slot=pick(me); send(c,{"slot":my_slot})
        while not q: pass
        other_slot=q.pop(0)["slot"]

        send(c,{"mon":me["party"][my_slot]})
        while not q: pass
        other_mon=q.pop(0)["mon"]

        me["party"][my_slot]=other_mon; save(me)
        print("Got",other_mon["species"])
        if input("Trade again? (Y/N) ").lower().startswith("y"):
            continue
        send(c,{"cmd":"bye"}); break
    c.close()

if __name__=="__main__":
    trade(input("h=host  j=join : ").lower()=="h")
