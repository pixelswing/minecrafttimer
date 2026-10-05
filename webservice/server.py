#!/usr/bin/env python3
import hmac, json, os, re, sqlite3
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

PORT=int(os.environ.get("MCTIMER_PORT","8787")); TOKEN=os.environ.get("MCTIMER_TOKEN","BITTE-AENDERN")
DEFAULT_LIMIT=max(0,int(os.environ.get("MCTIMER_DEFAULT_MINUTES","60"))); DB_PATH=Path(os.environ.get("MCTIMER_DB","/data/minecraft-timer.db"))
USER_PATTERN=re.compile(r"^[A-Za-z0-9._-]{1,64}$")

INDEX=r'''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Minecraft Timer</title><style>
:root{color-scheme:dark;--bg:#0d1117;--card:#161b22;--line:#30363d;--muted:#8b949e;--green:#3fb950}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#f0f6fc;font:16px system-ui,-apple-system,sans-serif}main{max-width:760px;margin:auto;padding:28px 16px}header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:22px}h1{font-size:24px;margin:0}.sub,.meta,#message{color:var(--muted);font-size:14px}.auth,.add,.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}.auth,.add{display:flex;gap:8px;margin-bottom:14px}input,button{font:inherit;border-radius:8px;padding:10px 12px;border:1px solid var(--line)}input{background:#0d1117;color:#f0f6fc;min-width:0;flex:1}button{background:#21262d;color:#f0f6fc;cursor:pointer}button:hover{border-color:#8b949e}.primary{background:#1f6feb;border-color:#1f6feb}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}.card{padding:18px}.top{display:flex;justify-content:space-between;gap:8px}.user{font-size:20px;font-weight:700}.host{color:var(--muted);font-size:13px;margin-top:3px}.limit{font-size:44px;font-weight:750;margin:18px 0 2px}.unit{color:var(--muted)}.actions{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:16px}.minus{color:#ff7b72}.plus{color:#7ee787}.exact{display:flex;gap:8px;margin-top:8px}.exact input{text-align:center}.empty{text-align:center;color:var(--muted);padding:36px}.hidden{display:none}#message{min-height:22px;margin:10px 2px}.status{color:var(--green);font-size:13px}@media(max-width:520px){header{align-items:flex-start;flex-direction:column}.auth,.add{flex-direction:column}}
</style></head><body><main><header><div><h1>⛏ Minecraft Timer</h1><div class="sub">Tageslimits zentral verwalten</div></div><div id="today" class="meta"></div></header><section class="auth"><input id="token" type="password" placeholder="API-Token"><button class="primary" onclick="loadUsers()">Verbinden</button></section><section id="app" class="hidden"><div class="add"><input id="newUser" placeholder="Benutzer hinzufügen, z. B. oskar"><button onclick="addUser()">Hinzufügen</button></div><div id="cards" class="grid"></div></section><div id="message"></div></main><script>
const token=document.querySelector('#token'),app=document.querySelector('#app'),cards=document.querySelector('#cards'),message=document.querySelector('#message');token.value=localStorage.mct||'';document.querySelector('#today').textContent=new Intl.DateTimeFormat('de-DE',{weekday:'long',day:'2-digit',month:'long'}).format(new Date());function headers(){localStorage.mct=token.value;return {'Authorization':'Bearer '+token.value,'Content-Type':'application/json'}}async function api(path,options={}){let r=await fetch(path,{...options,headers:headers()}),j=await r.json();if(!r.ok)throw Error(j.error||('HTTP '+r.status));return j}function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function card(u){let id=esc(u.username),host=u.host?'Host: '+esc(u.host):'Manuell hinzugefügt';return `<article class="card"><div class="top"><div><div class="user">${id}</div><div class="host">${host}</div></div><div class="status">● bekannt</div></div><div class="limit">${u.used_seconds==null?'–':Math.floor(u.used_seconds/60)+':'+String(Math.floor(u.used_seconds%60)).padStart(2,'0')}</div><div class="unit">Heute gespielt (Min:Sek) · ${u.used_seconds==null?'Mac-Update erforderlich':'zuletzt gemeldeter Stand'}</div><p>Tageslimit: ${u.effective_limit_minutes} Minuten</p><div class="unit">Minuten heute · ${u.delta_minutes>=0?'+':''}${u.delta_minutes} Anpassung</div><div class="actions"><button class="minus" onclick="adjust('${id}',-15)">−15</button><button onclick="resetUser('${id}')">Standard</button><button class="plus" onclick="adjust('${id}',15)">+15</button></div><div class="exact"><input id="value-${id}" type="number" min="0" max="1440" value="${u.effective_limit_minutes}"><button onclick="setLimit('${id}')">Setzen</button></div><p>Tägliches Zeitfenster</p><div class="exact"><input aria-label="Von" id="start-${id}" type="time" value="${u.window_start||'14:00'}"><input aria-label="Bis" id="end-${id}" type="time" value="${u.window_end||'18:00'}"></div><p class="meta">${u.window_start?u.window_start+' – '+u.window_end+' Uhr':'Ganztägig erlaubt'}</p><div class="actions"><button onclick="windowSave('${id}',false)">Speichern</button><button onclick="windowSave('${id}',true)">Ganztägig</button><button class="minus" onclick="removeUser('${id}')">Entfernen</button></div></article>`}async function loadUsers(){try{message.textContent='';let j=await api('/api/v1/users');cards.innerHTML=j.users.length?j.users.map(card).join(''):'<div class="empty">Noch kein Benutzer bekannt.<br>Timer auf dem Mac starten oder Benutzer hinzufügen.</div>';app.classList.remove('hidden')}catch(e){app.classList.add('hidden');message.textContent=e.message}}async function adjust(u,n){try{await api('/api/v1/users/'+encodeURIComponent(u)+'/adjust',{method:'POST',body:JSON.stringify({delta_minutes:n})});await loadUsers()}catch(e){message.textContent=e.message}}async function resetUser(u){try{await api('/api/v1/users/'+encodeURIComponent(u)+'/adjust',{method:'DELETE'});await loadUsers()}catch(e){message.textContent=e.message}}async function setLimit(u){let n=Number(document.getElementById('value-'+u).value);try{await api('/api/v1/users/'+encodeURIComponent(u)+'/limit',{method:'PUT',body:JSON.stringify({limit_minutes:n})});await loadUsers()}catch(e){message.textContent=e.message}}async function addUser(){let el=document.querySelector('#newUser'),u=el.value.trim();if(!u)return;try{await api('/api/v1/users/'+encodeURIComponent(u)+'/limit',{method:'PUT',body:JSON.stringify({limit_minutes:''' + str(60) + r'''})});el.value='';await loadUsers()}catch(e){message.textContent=e.message}}token.addEventListener('keydown',e=>{if(e.key==='Enter')loadUsers()});if(token.value)loadUsers();
async function windowSave(u,clear){try{await api('/api/v1/users/'+encodeURIComponent(u)+'/window',{method:'PUT',body:JSON.stringify({start:clear?null:document.getElementById('start-'+u).value,end:clear?null:document.getElementById('end-'+u).value})});await loadUsers()}catch(e){message.textContent=e.message}}
async function removeUser(u){if(!confirm('Nutzer aus Dashboard entfernen? Timer und Regeln bleiben aktiv.'))return;try{await api('/api/v1/users/'+encodeURIComponent(u),{method:'DELETE'});await loadUsers()}catch(e){message.textContent=e.message}}
setInterval(()=>{if(!app.classList.contains('hidden')&&!document.querySelector('.card input:focus'))loadUsers()},30000);
</script></body></html>'''

def connect():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True); db=sqlite3.connect(DB_PATH)
    db.execute("CREATE TABLE IF NOT EXISTS adjustments (day TEXT NOT NULL, username TEXT NOT NULL, delta_minutes INTEGER NOT NULL, PRIMARY KEY(day,username))")
    db.execute("CREATE TABLE IF NOT EXISTS clients (username TEXT PRIMARY KEY, host TEXT NOT NULL DEFAULT '', last_seen TEXT NOT NULL)"); db.execute("CREATE TABLE IF NOT EXISTS settings (username TEXT PRIMARY KEY, hidden INTEGER DEFAULT 0, start TEXT, end TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS usage (day TEXT, username TEXT, host TEXT, seconds REAL, seen TEXT, PRIMARY KEY(day,username,host))")
    return db

def remember(username,host=""):
    with connect() as db: db.execute("INSERT INTO clients(username,host,last_seen) VALUES(?,?,?) ON CONFLICT(username) DO UPDATE SET host=CASE WHEN excluded.host='' THEN host ELSE excluded.host END,last_seen=excluded.last_seen",(username,host[:128],datetime.now().isoformat(timespec="seconds")))

def get_limit(username):
    with connect() as db:
        row=db.execute("SELECT delta_minutes FROM adjustments WHERE day=? AND username=?",(str(date.today()),username)).fetchone(); client=db.execute("SELECT host,last_seen FROM clients WHERE username=?",(username,)).fetchone()
    with connect() as db:
        setting=db.execute("SELECT start,end FROM settings WHERE username=?",(username,)).fetchone()
        usage=db.execute("SELECT SUM(seconds),MAX(seen) FROM usage WHERE day=? AND username=?",(str(date.today()),username)).fetchone()
    delta=row[0] if row else 0
    return {"used_seconds":usage[0], "usage_updated":usage[1], "window_start":setting[0] if setting else None, "window_end":setting[1] if setting else None, "date":str(date.today()),"username":username,"host":client[0] if client else "","last_seen":client[1] if client else None,"default_limit_minutes":DEFAULT_LIMIT,"delta_minutes":delta,"effective_limit_minutes":max(0,DEFAULT_LIMIT+delta)}

class Handler(BaseHTTPRequestHandler):
    def send_json(self,status,payload):
        data=json.dumps(payload).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
    def authorized(self): return hmac.compare_digest(self.headers.get("Authorization",""),f"Bearer {TOKEN}")
    def require_auth(self):
        if self.authorized(): return True
        self.send_json(401,{"error":"Token ist nicht korrekt"}); return False
    def username(self,pattern):
        match=re.fullmatch(pattern,urlparse(self.path).path)
        if not match:return None
        username=unquote(match.group(1)); return username if USER_PATTERN.fullmatch(username) else None
    def body(self): return json.loads(self.rfile.read(min(int(self.headers.get("Content-Length","0")),1024)))
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path=="/":
            data=INDEX.encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data); return
        if parsed.path=="/api/v1/users":
            if not self.require_auth():return
            with connect() as db:names={r[0] for r in db.execute("SELECT username FROM clients")}|{r[0] for r in db.execute("SELECT username FROM adjustments WHERE day=?",(str(date.today()),))}
            with connect() as db:hidden={r[0] for r in db.execute("SELECT username FROM settings WHERE hidden=1")}
            self.send_json(200,{"date":str(date.today()),"users":[get_limit(n) for n in sorted(names-hidden)]});return
        username=self.username(r"/api/v1/limits/([^/]+)")
        if username:
            if not self.require_auth():return
            remember(username,parse_qs(parsed.query).get("host",[""])[0]);self.send_json(200,get_limit(username));return
        self.send_json(404,{"error":"Nicht gefunden"})
    def do_POST(self):
        user=self.username(r"/api/v1/users/([^/]+)/usage")
        if user:
            if not self.require_auth():return
            try:
                b=self.body()
                seconds=b["used_seconds"]
                if not isinstance(seconds,(int,float)) or not 0<=seconds<=172800:raise ValueError()
                if b["date"]!=str(date.today()):raise ValueError()
                host=b["host"]
                if not isinstance(host,str) or not 0<len(host)<=128:raise ValueError()
            except (ValueError,KeyError,TypeError):self.send_json(400,{"error":"Ungültiger Verbrauch oder abweichendes Datum"});return
            remember(user,host)
            with connect() as db:db.execute("INSERT INTO usage VALUES(?,?,?,?,?) ON CONFLICT(day,username,host) DO UPDATE SET seconds=MAX(seconds,excluded.seconds),seen=excluded.seen",(b["date"],user,host,seconds,datetime.now().isoformat(timespec="seconds")))
            self.send_json(200,{"ok":True});return

        username=self.username(r"/api/v1/users/([^/]+)/adjust")
        if not username:self.send_json(404,{"error":"Nicht gefunden"});return
        if not self.require_auth():return
        try:
            delta=int(self.body()["delta_minutes"])
            if not -1440<=delta<=1440:raise ValueError()
        except (ValueError,KeyError,json.JSONDecodeError):self.send_json(400,{"error":"Ungültige Minuten"});return
        remember(username)
        with connect() as db:db.execute("INSERT INTO adjustments(day,username,delta_minutes) VALUES(?,?,?) ON CONFLICT(day,username) DO UPDATE SET delta_minutes=delta_minutes+excluded.delta_minutes",(str(date.today()),username,delta))
        self.send_json(200,get_limit(username))
    def do_PUT(self):
        user=self.username(r"/api/v1/users/([^/]+)/window")
        if user:
            if not self.require_auth():return
            try:
                b=self.body();start=b["start"];end=b["end"]
                if not (start is None and end is None):
                    if not all(isinstance(v,str) and re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]",v) for v in (start,end)) or start>=end:raise ValueError()
            except (ValueError,KeyError,TypeError):self.send_json(400,{"error":"Start muss vor Ende liegen (gleicher Tag)"});return
            with connect() as db:db.execute("INSERT INTO settings(username,start,end) VALUES(?,?,?) ON CONFLICT(username) DO UPDATE SET start=excluded.start,end=excluded.end",(user,start,end))
            self.send_json(200,get_limit(user));return

        username=self.username(r"/api/v1/users/([^/]+)/limit")
        if not username:self.send_json(404,{"error":"Nicht gefunden"});return
        if not self.require_auth():return
        try:
            limit=int(self.body()["limit_minutes"])
            if not 0<=limit<=1440:raise ValueError()
        except (ValueError,KeyError,json.JSONDecodeError):self.send_json(400,{"error":"Limit muss zwischen 0 und 1440 liegen"});return
        remember(username)
        with connect() as db:db.execute("UPDATE settings SET hidden=0 WHERE username=?",(username,))
        with connect() as db:db.execute("INSERT INTO adjustments(day,username,delta_minutes) VALUES(?,?,?) ON CONFLICT(day,username) DO UPDATE SET delta_minutes=excluded.delta_minutes",(str(date.today()),username,limit-DEFAULT_LIMIT))
        self.send_json(200,get_limit(username))
    def do_DELETE(self):
        user=self.username(r"/api/v1/users/([^/]+)")
        if user:
            if not self.require_auth():return
            with connect() as db:db.execute("INSERT INTO settings(username,hidden) VALUES(?,1) ON CONFLICT(username) DO UPDATE SET hidden=1",(user,))
            self.send_json(200,{"ok":True});return

        username=self.username(r"/api/v1/users/([^/]+)/adjust")
        if not username:self.send_json(404,{"error":"Nicht gefunden"});return
        if not self.require_auth():return
        with connect() as db:db.execute("DELETE FROM adjustments WHERE day=? AND username=?",(str(date.today()),username))
        self.send_json(200,get_limit(username))
    def log_message(self,fmt,*args):print(f"{self.address_string()} {fmt % args}",flush=True)

if __name__=="__main__":
    if TOKEN=="BITTE-AENDERN":print("WARNUNG: MCTIMER_TOKEN ist noch nicht geändert",flush=True)
    with connect():pass
    print(f"Minecraft Timer Webservice auf Port {PORT}",flush=True);ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
