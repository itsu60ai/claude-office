# The office: one local page that shows what each Claude Code chat is doing right now,
# and carries what you write to the right chat. Binds 127.0.0.1 only, so nothing leaves this computer.
# Python 3.8+ standard library only. No accounts, no API keys, no model calls, no background jobs.
#
# What it reads: the Claude desktop app's own session files and the chat transcripts in ~/.claude/projects.
# What it writes: only inside this folder (state/ and, when you answer a question, tasks.json).
# It never sends a message: every request comes back as a claude:// link that you open and send yourself.
import base64
import glob
import hashlib
import json
import math
import os
import re
import shutil
import sys
import threading
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
TRANSCRIPTS = os.path.join(HOME, ".claude", "projects")
# Where the Claude desktop app keeps its chat list. Windows (Store and regular install), Mac, Linux.
APP_DIRS = [
    *glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\claude-code-sessions")),
    os.path.expandvars(r"%APPDATA%\Claude\claude-code-sessions"),
    os.path.join(HOME, "Library", "Application Support", "Claude", "claude-code-sessions"),
    os.path.join(HOME, ".config", "Claude", "claude-code-sessions"),
]
CHAT_LINK = "claude://claude.ai/epitaxy/%s"  # opens an existing chat in the desktop app
NEW_CHAT = "claude://code/new?q=%s&folder=%s"  # opens a new chat with the text already typed, not sent

CONFIG = os.path.join(HERE, "office.json")
CONFIG_EXAMPLE = os.path.join(HERE, "office.example.json")
TASKS = os.path.join(HERE, "tasks.json")
STATE = os.path.join(HERE, "state")
QUEUE = os.path.join(STATE, "office-queue.jsonl")  # append-only log of requests, ideas and builds
UPLOADS = os.path.join(STATE, "uploads")           # pictures added to a request, never served to the browser
SNAPSHOTS = os.path.join(STATE, "snapshots")       # a copy before every write, never deleted
NEXT_DIR = os.path.join(HERE, "next")              # where "the next version" is built; the live page is untouched
SERVED = {"/": "index.html", "/index.html": "index.html"}  # the only files the browser can get

TOOL_KIND = {
    "Read": ("read", "read-files"), "Grep": ("read", "search-files"), "Glob": ("read", "find-files"),
    "Edit": ("write", "edit-file"), "Write": ("write", "write-file"), "NotebookEdit": ("write", "edit-file"),
    "Bash": ("run", "run"), "PowerShell": ("run", "run"),
    "WebSearch": ("web", "search-web"), "WebFetch": ("web", "read-web"),
    "Agent": ("help", "helper"), "Workflow": ("help", "helpers"),
}
# Server texts go out with a key ("lineKey" etc.); the page shows the key in its own language.
# The Hebrew here is only what a page shows when it doesn't know the key.
TOOL_TEXT = {"read-files": "קוראת קבצים", "search-files": "מחפשת בקבצים", "find-files": "מחפשת קבצים",
             "edit-file": "כותבת בקובץ", "write-file": "כותבת קובץ", "run": "מריצה פקודה",
             "search-web": "מחפשת ברשת", "read-web": "קוראת דף ברשת", "helper": "שלחה עוזר",
             "helpers": "מפעילה כמה עוזרים", "browser": "עובדת בדפדפן", "tool": "משתמשת בכלי", "working": "עובדת"}
PALETTE = ["#1D9E75", "#7F77DD", "#D85A30", "#378ADD", "#D4537E", "#BA7517", "#639922", "#E24B4A", "#5F5E5A"]
# Text that is never shown even when it sits inside a chat's description of a step.
BLOCK = re.compile(r"password|סיסמ|\.env\b|token|secret|api[_ -]?key|credential|bank|בנק|credit card|כרטיס אשראי", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"(?:\+972[- ]?|\b0)5\d[- ]?\d{3}[- ]?\d{4}\b|\+\d{1,3}[- ]?\(?\d{2,4}\)?[- ]?\d{3,4}[- ]?\d{3,4}\b")
KEY_SHAPE = re.compile(r"sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[abpr]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}"
                       r"|AIza[0-9A-Za-z_-]{30,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
LONG_TOKEN = re.compile(r"[A-Za-z0-9_+/=]{32,}")

LATER_DAYS = (1, 3, 7)
WAIT_MIN = 30          # a chat that finished within this many minutes is "your turn"
STUCK_S = 300          # an open turn with no transcript write for this long is shown as "stopped"
DESK_WINDOW_H = 24     # chats active in the last day get a desk
MAX_DESKS = 9
IMG_MAX = 8 * 1024 * 1024  # bytes per picture
IMG_PER_REQUEST = 4
IMG_KINDS = {"png": b"\x89PNG", "jpg": b"\xff\xd8\xff", "gif": b"GIF8", "webp": b"RIFF"}
DEDUP_S = 600          # the same text to the same place within 10 minutes is one request
SEND_WAIT_S = 1800     # after this, a request nobody sent is shown as "not sent"
ITEM_ID = r"[A-Z]{2,8}-\d{1,5}"

_app_cache = {}        # path -> (mtime, parsed subset)
_tx_path = {}          # cli session -> transcript path
_qlock = threading.Lock()  # one writer for the queue log and tasks.json
_match = {}            # tag -> {"local", "cli"} once a chat with that tag is found
_cfg = {"mt": None, "data": None}


def now():
    return time.time()


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_iso(v):
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError):
        return None


def today():
    return datetime.now().astimezone().date().isoformat()


# ---- settings (office.json, or the example until you make your own) ----

def config():
    """office.json, read again whenever it changes, so edits show up without a restart."""
    path = CONFIG if os.path.exists(CONFIG) else CONFIG_EXAMPLE
    mt = (path, os.path.getmtime(path))
    if _cfg["mt"] != mt:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        projects = []
        for n, p in enumerate(raw.get("projects") or []):
            if not (isinstance(p, dict) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", str(p.get("id", "")))):
                continue
            if p["id"] == "new-project":
                continue
            folder = os.path.normpath(os.path.expanduser(p.get("folder") or "~"))
            projects.append({"id": p["id"], "name": p.get("name") or p["id"], "nameEn": p.get("nameEn") or p.get("name"),
                             "folder": folder, "color": p.get("color") or PALETTE[n % len(PALETTE)],
                             "keywords": p.get("keywords") or ""})
        if not projects:
            projects = [{"id": "main", "name": "העבודה שלי", "nameEn": "My work", "folder": HOME, "color": PALETTE[0],
                         "keywords": ""}]
        names = raw.get("privateNames") or {}
        if isinstance(names, list):
            names = {n: "***" for n in names}
        names = {k: v for k, v in names.items() if isinstance(k, str) and len(k.strip()) >= 2 and isinstance(v, str)}
        on = raw.get("officeName")
        on = on if isinstance(on, dict) else {"he": on or "המשרד", "en": on or "The office"}
        ids = [p["id"] for p in projects]
        _cfg["data"] = {
            "officeName": {"he": on.get("he") or "המשרד", "en": on.get("en") or "The office"},
            "defaultLang": "en" if raw.get("defaultLang") == "en" else "he",
            "defaultProject": raw.get("defaultProject") if raw.get("defaultProject") in ids else ids[0],
            "projects": projects,
            "newProjectsFolder": os.path.normpath(os.path.expanduser(raw.get("newProjectsFolder") or "~")),
            "privateNames": names,
            "example": path == CONFIG_EXAMPLE,
        }
        _cfg["mt"] = mt
    return _cfg["data"]


def projects():
    return {p["id"]: p for p in config()["projects"]}


def hints():
    """The page's project guess: the first pattern that matches wins."""
    out = [["new-project", "new project|פרויקט חדש"]]
    for p in config()["projects"]:
        if p["keywords"]:
            try:
                re.compile(p["keywords"])
                out.append([p["id"], p["keywords"]])
            except re.error:
                continue
    return out


# ---- privacy ----

def secret_shape(v):
    if KEY_SHAPE.search(v):
        return True
    for tok in LONG_TOKEN.findall(v):
        if re.fullmatch(r"[0-9a-fA-F]+", tok) or not (re.search(r"\d", tok) and re.search(r"[A-Za-z]", tok)):
            continue
        c = Counter(tok)
        if -sum(n / len(tok) * math.log2(n / len(tok)) for n in c.values()) >= 3.5:
            return True
    return False


def leak_findings(obj, names):
    found = []

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str):
            if EMAIL.search(v) or PHONE.search(v) or secret_shape(v) or any(n in v for n in names):
                found.append(1)
    walk(obj)
    return found


class Clean:
    """Swaps private names for their alias and drops any string that still looks private."""

    def __init__(self):
        self.names = config()["privateNames"]

    def __call__(self, text, fallback=None, limit=90):
        if not text or not isinstance(text, str):
            return fallback
        t = " ".join(text.split())
        for name in sorted(self.names, key=len, reverse=True):
            t = t.replace(name, self.names[name])
        if BLOCK.search(t) or leak_findings(t, self.names):
            return fallback
        return t if len(t) <= limit else t[:limit - 1].rstrip() + "…"


# ---- chats: the desktop app's list and the transcripts ----

def app_sessions():
    """Recent, non-archived chats from the app's own session files (cached by mtime)."""
    out, cutoff, seen = [], now() - DESK_WINDOW_H * 3600, set()
    for base in APP_DIRS:
        if not os.path.isdir(base):
            continue
        for path in glob.glob(os.path.join(base, "*", "*", "local_*.json")):
            try:
                mt = os.path.getmtime(path)
            except OSError:
                continue
            if mt < cutoff:
                continue
            hit = _app_cache.get(path)
            if not hit or hit[0] != mt:
                try:
                    with open(path, encoding="utf-8") as f:
                        j = json.load(f)
                except (OSError, ValueError):
                    if hit:
                        out.append(hit[1])
                    continue
                hit = (mt, {"local": j.get("sessionId"), "cli": j.get("cliSessionId"), "title": j.get("title"),
                            "cwd": j.get("originCwd") or j.get("cwd") or "", "archived": bool(j.get("isArchived")),
                            "last": (j.get("lastActivityAt") or 0) / 1000.0})
                _app_cache[path] = hit
            if not hit[1]["archived"] and hit[1]["cli"] and hit[1]["cli"] not in seen:
                seen.add(hit[1]["cli"])
                out.append(hit[1])
    return out


def transcript(cli):
    p = _tx_path.get(cli)
    if not p or not os.path.exists(p):
        found = glob.glob(os.path.join(TRANSCRIPTS, "*", cli + ".jsonl"))
        p = found[0] if found else None
        _tx_path[cli] = p
    return p


def tail(path, n):
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - n))
            return f.read().decode("utf-8", "ignore").splitlines()[1:]
    except OSError:
        return []


def recent_actions(lines, n=3):
    """Last tool uses from the end of a transcript: (time, tool name, description)."""
    acts = []
    for line in reversed(lines):
        if '"tool_use"' not in line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        for c in reversed((e.get("message") or {}).get("content") or []):
            if isinstance(c, dict) and c.get("type") == "tool_use":
                inp = c.get("input") or {}
                acts.append((parse_iso(e.get("timestamp")), c.get("name") or "", inp.get("description")))
        if len(acts) >= n:
            break
    return acts[:n]


def turn_open(lines):
    """True while a chat's turn is still running: its last entry isn't a finished reply."""
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        k = e.get("type")
        if k == "system":
            if e.get("subtype") in ("stop_hook_summary", "turn_duration"):
                return False
            continue
        if k == "assistant":
            return (e.get("message") or {}).get("stop_reason") not in ("end_turn", "stop_sequence")
        if k == "user":
            return True
    return False


def action_text(name, desc, clean):
    """(kind, text, key). The key is None when the text is the chat's own description of the step."""
    kind, key = TOOL_KIND.get(name, ("other", "working"))
    if name.startswith("mcp__Claude_Browser") or name.startswith("mcp__claude-in-chrome"):
        kind, key = "web", "browser"
    elif name.startswith("mcp__"):
        kind, key = "other", "tool"
    own = clean(desc, None, 80) if name in ("Bash", "PowerShell", "Agent") else None
    return (kind, own, None) if own else (kind, TOOL_TEXT[key], "tool." + key)


def project_of(chat):
    """The project whose folder holds the chat's folder (the deepest one wins)."""
    cwd = os.path.normcase(os.path.normpath(chat["cwd"])) if chat["cwd"] else ""
    best, depth = None, -1
    for p in config()["projects"]:
        f = os.path.normcase(p["folder"])
        if cwd and (cwd == f or cwd.startswith(f.rstrip("\\/") + os.sep)) and len(f) > depth:
            best, depth = p["id"], len(f)
    return best


def turn(cli, clean):
    """Where one chat's turn stands, from its transcript: work / stuck / closed."""
    tx = transcript(cli)
    tx_mt = os.path.getmtime(tx) if tx and os.path.exists(tx) else 0
    lines = tail(tx, 160000) if tx else []
    acts = recent_actions(lines)
    quiet = now() - tx_mt if tx_mt else 1e9
    is_open = turn_open(lines) if lines else False
    kind, doing, dkey = action_text(acts[0][1], acts[0][2], clean) if acts else ("other", None, None)
    arg = None
    if is_open and quiet < STUCK_S:
        state, line, key = "work", doing or "עובדת", dkey if doing else "tool.working"
    elif is_open:
        arg = int(quiet // 60)
        state, line, key = "stuck", "עצרה לפני %d דק'. אולי מחכה לאישור שלך" % arg, "stuck"
    else:
        state, line, key = "closed", None, None
    return {"state": state, "line": line, "lineKey": key, "lineArg": arg, "kind": kind, "tx": tx, "tx_mt": tx_mt,
            "acts": acts}


def desks(clean):
    t, rows, feed, projs = now(), [], [], projects()
    for ch in sorted(app_sessions(), key=lambda c: -c["last"])[:MAX_DESKS]:
        tu = turn(ch["cli"], clean)
        last, acts, state, line, key = max(ch["last"], tu["tx_mt"]), tu["acts"], tu["state"], tu["line"], tu["lineKey"]
        if state == "closed":
            state, line = ("done", "סיימה. התור שלך") if t - last < WAIT_MIN * 60 else ("idle", "בהפסקה")
            key = state
        p = project_of(ch)
        title = clean(ch["title"], None, 40)
        tkey = None if title else "untitled"
        title = title or "שיחה בלי שם"
        rows.append({"id": hashlib.sha256(ch["cli"].encode()).hexdigest()[:8], "title": title, "titleKey": tkey,
                     "project": projs[p]["name"] if p else "כללי", "pid": p or "other", "state": state,
                     "kind": tu["kind"], "line": line, "lineKey": key, "lineArg": tu["lineArg"], "since": iso(last),
                     "local": ch["local"], "link": CHAT_LINK % ch["local"] if ch["local"] else None})
        for at, name, desc in acts:
            if at:
                _, what, wkey = action_text(name, desc, clean)
                feed.append({"at": iso(at), "ts": at, "who": title, "whoKey": tkey, "what": what, "whatKey": wkey})
    return rows, feed


# ---- questions waiting for you (tasks.json, optional) ----

def read_tasks():
    """(raw bytes, parsed). No tasks.json means no questions: the card stays hidden."""
    try:
        with open(TASKS, "rb") as f:
            raw = f.read()
        d = json.loads(raw.decode("utf-8"))
        return raw, d if isinstance(d, dict) and isinstance(d.get("items"), list) else {"items": []}
    except (OSError, ValueError):
        return None, {"items": []}


def is_waiting(it):
    return (isinstance(it, dict) and isinstance(it.get("id"), str) and re.fullmatch(ITEM_ID, it["id"])
            and it.get("status", "waiting") == "waiting" and str(it.get("later_until") or "") <= today())


def two(clean, v, limit, fallback=None):
    """A question's text is one string, or {"he": ..., "en": ...} so the page can show it in its own language."""
    if isinstance(v, dict):
        he, en = clean(v.get("he"), None, limit), clean(v.get("en"), None, limit)
        return {"he": he or en, "en": en or he} if he or en else fallback
    return clean(v, fallback, limit)


def plain(v):
    return (v.get("en") or v.get("he")) if isinstance(v, dict) else (v or "")


def waiting(clean):
    rows, projs = [], projects()
    for it in read_tasks()[1]["items"]:
        if not is_waiting(it):
            continue
        p = it.get("project") if it.get("project") in projs else config()["defaultProject"]
        name = two(clean, it.get("name"), 70, {"he": "שאלה", "en": "Question"})
        nxt = two(clean, it.get("next"), 160)
        quick = bool(it.get("quick"))
        auto = not it.get("why")  # the page writes the general "why" lines in its own language
        why = ([nxt] if nxt else []) if auto else [w for w in it["why"] if isinstance(w, (str, dict))]
        q = "I want to move forward on %s (%s) from tasks.json in the office folder. Tell me briefly where it stands." % (
            it["id"], plain(name))
        chat = it.get("chat") if isinstance(it.get("chat"), str) and re.fullmatch(r"local_[0-9a-f-]{36}", it["chat"]) else None
        rows.append({"id": it["id"], "name": name, "next": nxt, "project": projs[p]["name"], "pid": p,
                     "main": bool(it.get("main")), "money": bool(it.get("money")),
                     "quick": quick, "ask": two(clean, it.get("ask"), 120),
                     "why": [two(clean, w, 160, "") for w in why[:2]], "whyAuto": auto,
                     "pick": it.get("pick") if quick and it.get("pick") in ("yes", "no") else None,
                     "pickWhy": two(clean, it.get("pickWhy"), 160),
                     "chat": CHAT_LINK % chat if chat else None,
                     "newChat": NEW_CHAT % (quote(q, safe=""), quote(projs[p]["folder"], safe=""))})
    rows.sort(key=lambda r: not r["quick"])  # quick taps first; otherwise the file's order
    return rows


def snapshot(path, raw):
    """Copy the file before a write and check the copy matches byte for byte."""
    sha = hashlib.sha256(raw).hexdigest()
    os.makedirs(SNAPSHOTS, exist_ok=True)
    snap = os.path.join(SNAPSHOTS, "%s-%s-%s" % (os.path.basename(path), datetime.now().strftime("%Y%m%dT%H%M%S"),
                                                 sha[:12]))
    shutil.copyfile(path, snap)
    with open(snap, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest() == sha


def answer(body):
    """Your Yes / No / Later on one question in tasks.json. It only records the answer; nothing is sent."""
    iid, value, nonce = body.get("id"), body.get("answer"), body.get("nonce")
    if not (isinstance(iid, str) and re.fullmatch(ITEM_ID, iid)):
        return 400, {"error": "bad-id"}
    if value not in ("yes", "no", "later") or not good_nonce(nonce):
        return 400, {"error": "bad-answer"}
    with _qlock:
        raw, d = read_tasks()
        it = next((x for x in d["items"] if isinstance(x, dict) and x.get("id") == iid), None)
        if raw is None or not it or not is_waiting(it):
            return 409, {"error": "not-waiting"}
        if value != "later" and not it.get("quick"):
            return 409, {"error": "needs-chat"}
        at = datetime.now().astimezone().isoformat(timespec="seconds")
        until = None
        if value == "later":
            days = body.get("days")
            if days not in LATER_DAYS:
                return 400, {"error": "bad-days"}
            until = (datetime.now().astimezone().date() + timedelta(days=days)).isoformat()
            it["later_until"] = until
        else:
            it.update(status="answered", answer={"value": value, "at": at, "via": "office-page"})
        if not snapshot(TASKS, raw):
            return 500, {"error": "snapshot-mismatch"}
        with open(TASKS, "rb") as f:  # nobody changed it between our read and our write
            if f.read() != raw:
                return 409, {"error": "changed"}
        tmp = TASKS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, TASKS)
    return 200, {"recorded": iid, "answer": value, "until": until}


# ---- requests, ideas and the next version (one append-only log, one writer) ----

def good_nonce(n):
    return isinstance(n, str) and re.fullmatch(r"[a-f0-9]{8,32}", n) is not None


def qread():
    out = []
    try:
        with open(QUEUE, encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def qappend(rec):
    """Append one record. Daily snapshot first, then a hash check that the old bytes are untouched."""
    os.makedirs(STATE, exist_ok=True)
    old = b""
    if os.path.exists(QUEUE):
        with open(QUEUE, "rb") as f:
            old = f.read()
        os.makedirs(SNAPSHOTS, exist_ok=True)
        snap = os.path.join(SNAPSHOTS, "office-queue-%s.jsonl" % datetime.now().strftime("%Y%m%d"))
        if not os.path.exists(snap):
            shutil.copyfile(QUEUE, snap)
    sha = hashlib.sha256(old).hexdigest()
    line = (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8")
    with open(QUEUE, "ab") as f:
        f.write(line)
    with open(QUEUE, "rb") as f:
        after = f.read()
    if hashlib.sha256(after[:len(old)]).hexdigest() != sha or not after.endswith(line):
        raise IOError("queue-check-failed")


def qstate():
    """Fold the log: requests, ideas (queued / included / building) and builds."""
    reqs, ideas, builds = {}, {}, {}
    for r in qread():
        k, rid = r.get("kind"), r.get("id")
        if k == "request":
            reqs[rid] = r
        elif k == "idea":
            ideas[rid] = dict(r, state="queued")
        elif k == "idea-include" and rid in ideas and ideas[rid]["state"] in ("queued", "included"):
            ideas[rid]["state"] = "included" if r.get("include") else "queued"
        elif k == "build":
            builds[rid] = dict(r, cancelled=False)
            for i in r.get("ideas") or []:
                if i in ideas:
                    ideas[i].update(state="building", build=rid)
        elif k == "build-cancel" and rid in builds:
            builds[rid]["cancelled"] = True
            for i in builds[rid].get("ideas") or []:
                if i in ideas and ideas[i].get("build") == rid:
                    ideas[i]["state"] = "included"
    return reqs, ideas, builds


def new_id(prefix, nonce):
    return prefix + hashlib.sha256(("%s%f" % (nonce, now())).encode()).hexdigest()[:6]


def stamp():
    return {"at": datetime.now().astimezone().isoformat(timespec="seconds"), "ts": now()}


def typed(buf, tag):
    """True when the tag sits in a message you sent, not in a tool's output or in Claude's own text."""
    for line in buf.split(b"\n"):
        if tag not in line or b'"user"' not in line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        c = (e.get("message") or {}).get("content") if e.get("type") == "user" else None
        if isinstance(c, str):
            parts = [c]
        else:
            parts = [x.get("text", "") for x in c or [] if isinstance(x, dict) and x.get("type") == "text"]
        if any(tag.decode() in p for p in parts):
            return True
    return False


def find_tag(tag, since, chat=None):
    """The chat whose transcript holds this ASCII tag: a known chat (tail only) or one opened after `since` (head only)."""
    if tag in _match:
        return _match[tag]
    b = tag.encode()
    for ch in app_sessions():
        if chat and ch["local"] != chat:
            continue
        tx = transcript(ch["cli"])
        if not tx or (not chat and ch["last"] < since - 60):
            continue
        try:
            size = os.path.getsize(tx)
            if os.path.getmtime(tx) < since - 60 or (not chat and size > 3000000):
                continue
            with open(tx, "rb") as f:
                if chat:
                    f.seek(max(0, size - 400000))
                if not typed(f.read(400000), b):
                    continue
        except OSError:
            continue
        _match[tag] = {"local": ch["local"], "cli": ch["cli"]}
        return _match[tag]
    return None


def last_reply(tx, since):
    """The last assistant text written after `since` (reads the tail only)."""
    for line in reversed(tail(tx, 300000)):
        if '"assistant"' not in line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") != "assistant":
            continue
        if (parse_iso(e.get("timestamp")) or 0) < since:
            return None
        for c in (e.get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "text" and (c.get("text") or "").strip():
                return re.sub(r"[*#`>|_]+", "", c["text"])
    return None


def lang_of(body):
    return "en" if body.get("lang") == "en" else "he"


CHAT_WORDS = {
    "he": {"item": "התשובה שלי לשאלה %s (בקובץ tasks.json בתיקיית המשרד):\n%s",
           "new": "בקשה לפרויקט חדש:\n%s\n\nלפני שפותחים משהו: תבדוק בתיקייה %s אם כבר יש פרויקט שמתאים. "
                  "תת-תיקייה רגילה היא לא פרויקט. אם באמת צריך פרויקט חדש, תציע לי שם, ורק אחרי שאני מאשר "
                  "תפתח את התיקייה ותוסיף אותה ל-office.json בתיקיית המשרד (%s).",
           "pic": "\nתמונה מצורפת (תפתח אותה עם Read): %s"},
    "en": {"item": "My answer to question %s (in tasks.json in the office folder):\n%s",
           "new": "A request for a new project:\n%s\n\nBefore creating anything: check %s for a project that already "
                  "fits. A plain subfolder is not a project. If it really needs a new one, suggest a name, and only "
                  "after I approve create the folder and add it to office.json in the office folder (%s).",
           "pic": "\nAttached picture (open it with Read): %s"},
}


def chat_text(r):
    """What goes into the chat: your words, any routing note, and the ASCII tag the office tracks."""
    w = CHAT_WORDS[r.get("lang") or "he"]
    t = r["text"]
    if r.get("item"):
        t = w["item"] % (r["item"], t)
    elif r.get("project") == "new-project":
        t = w["new"] % (t, config()["newProjectsFolder"], HERE)
    for name in r.get("images") or []:
        t += w["pic"] % os.path.normpath(os.path.join(UPLOADS, name))
    return t + "\n\n(office request %s)" % r["id"]


def upload(body):
    """A picture for a request. Checked by its first bytes, saved under a name made from its content."""
    data = body.get("data")
    if not isinstance(data, str) or len(data) > IMG_MAX * 4 // 3 + 8:
        return 400, {"error": "too-big"}
    try:
        raw = base64.b64decode(data, validate=True)
    except ValueError:
        return 400, {"error": "bad-image"}
    ext = next((k for k, magic in IMG_KINDS.items() if raw.startswith(magic)), None)
    if ext == "webp" and raw[8:12] != b"WEBP":
        ext = None
    if not ext or len(raw) > IMG_MAX:
        return 400, {"error": "bad-image" if not ext else "too-big"}
    name = "IMG-%s.%s" % (hashlib.sha256(raw).hexdigest()[:16], ext)
    os.makedirs(UPLOADS, exist_ok=True)
    path = os.path.normpath(os.path.join(UPLOADS, name))
    if not os.path.exists(path):
        with open(path + ".tmp", "wb") as f:
            f.write(raw)
        os.replace(path + ".tmp", path)
    return 200, {"image": name, "size": len(raw)}


def good_images(v):
    if v is None:
        return []
    if not (isinstance(v, list) and len(v) <= IMG_PER_REQUEST):
        return None
    for n in v:
        if not (isinstance(n, str) and re.fullmatch(r"IMG-[0-9a-f]{16}\.(png|jpg|gif|webp)", n)
                and os.path.isfile(os.path.join(UPLOADS, n))):
            return None
    return list(dict.fromkeys(v))


def request_link(r):
    q = chat_text(r)
    if r.get("chat"):
        return {"id": r["id"], "mode": "continue", "link": CHAT_LINK % r["chat"], "copy": q}
    return {"id": r["id"], "mode": "new", "copy": q, "link": NEW_CHAT % (quote(q, safe=""), quote(r["folder"], safe=""))}


def make_request(body):
    """You wrote something in the office. Record it once and hand back the link that carries it to a chat."""
    text, pid, target, nonce = body.get("text"), body.get("project"), body.get("target") or "new", body.get("nonce")
    if not (isinstance(text, str) and 0 < len(text.strip()) <= 2000):
        return 400, {"error": "bad-text"}
    if not good_nonce(nonce) or not isinstance(target, str):
        return 400, {"error": "bad-nonce"}
    images = good_images(body.get("images"))
    if images is None:
        return 400, {"error": "bad-images"}
    text = text.strip()
    projs = projects()
    rec = {"kind": "request", "text": text, "target_in": target, "nonce": nonce, "chat": None, "lang": lang_of(body)}
    if images:
        rec["images"] = images
    if target == "new":
        if pid == "new-project":
            rec.update(project=pid, folder=config()["newProjectsFolder"])
        elif pid in projs:
            rec.update(project=pid, folder=projs[pid]["folder"])
        else:
            return 400, {"error": "bad-project"}
    elif re.fullmatch(r"local_[0-9a-f-]{36}", target):
        rec.update(project=pid if pid in projs else None, chat=target)
    elif re.fullmatch(r"item:" + ITEM_ID, target):
        it = next((x for x in read_tasks()[1]["items"] if isinstance(x, dict) and x.get("id") == target[5:]), None)
        if not it:
            return 409, {"error": "no-item"}
        p = it.get("project") if it.get("project") in projs else config()["defaultProject"]
        chat = it.get("chat") if isinstance(it.get("chat"), str) and re.fullmatch(r"local_[0-9a-f-]{36}", it["chat"]) else None
        rec.update(item=it["id"], project=p, folder=projs[p]["folder"], chat=chat)
    else:
        return 400, {"error": "bad-target"}
    norm = " ".join(text.split())
    with _qlock:
        reqs, _, _ = qstate()
        for r in reqs.values():
            if r.get("nonce") == nonce or (" ".join(r["text"].split()) == norm and r.get("target_in") == target
                                           and r.get("project") == rec["project"] and now() - r["ts"] < DEDUP_S
                                           and (r.get("images") or []) == images):
                return 200, dict(request_link(r), duplicate=True)
        rec.update(stamp(), id=new_id("R-", nonce))
        qappend(rec)
    return 200, request_link(rec)


def reopen(body):
    rid = body.get("id")
    r = qstate()[0].get(rid) if isinstance(rid, str) and re.fullmatch(r"R-[0-9a-f]{6}", rid) else None
    return (200, request_link(r)) if r else (404, {"error": "no-request"})


def add_idea(body):
    """Only records an idea for the next version. It never starts a build."""
    text, nonce = body.get("text"), body.get("nonce")
    if not (isinstance(text, str) and 0 < len(text.strip()) <= 500) or not good_nonce(nonce):
        return 400, {"error": "bad-idea"}
    text = " ".join(text.split())
    with _qlock:
        for i in qstate()[1].values():
            if i.get("nonce") == nonce or (i["text"] == text and i["state"] in ("queued", "included")):
                return 200, {"idea": i["id"], "duplicate": True}
        rec = dict(stamp(), kind="idea", id=new_id("I-", nonce), text=text, nonce=nonce)
        qappend(rec)
    return 200, {"idea": rec["id"]}


def include_idea(body):
    iid, inc = body.get("id"), body.get("include")
    if not (isinstance(iid, str) and re.fullmatch(r"I-[0-9a-f]{6}", iid)) or not isinstance(inc, bool):
        return 400, {"error": "bad-idea"}
    with _qlock:
        i = qstate()[1].get(iid)
        if not i or i["state"] not in ("queued", "included"):
            return 409, {"error": "not-editable"}
        qappend(dict(stamp(), kind="idea-include", id=iid, include=inc))
    return 200, {"idea": iid, "include": inc}


BUILD_WORDS = {
    "he": ("תבנה את הגרסה הבאה של דף המשרד (התיקייה %s).\n\nהרעיונות שבחרתי:\n%s\n\n"
           "איך עובדים:\n"
           "- רק על עותק: תעתיק את index.html ואת server.py לתיקייה next (אם היא כבר קיימת, תמשיך ממנה) ותבנה שם. "
           "אל תיגע ב-index.html או ב-server.py החיים.\n"
           "- לא מוחקים כלום, לא שולחים, לא מפרסמים ולא מוציאים כסף.\n"
           "- תבדוק את העותק בדפדפן: python next/server.py 8799, ואז http://127.0.0.1:8799.\n"
           "- כשסיימת ובדקת, תכתוב next/BUILD-%s.md: מה נבנה, מה בדקת, ואיך מחליפים לגרסה החדשה. "
           "ההחלפה עצמה רק אחרי שאני מאשר.\n\n(office build %s)"),
    "en": ("Build the next version of the office page (the folder %s).\n\nThe ideas I picked:\n%s\n\n"
           "How to work:\n"
           "- Only on a copy: copy index.html and server.py into the next folder (if it exists, continue there) and "
           "build there. Don't touch the live index.html or server.py.\n"
           "- Delete nothing, send nothing, publish nothing, spend nothing.\n"
           "- Check the copy in a browser: python next/server.py 8799, then http://127.0.0.1:8799.\n"
           "- When it's done and checked, write next/BUILD-%s.md: what was built, what you checked, and how to "
           "switch to it. The switch itself only after I approve.\n\n(office build %s)"),
}


def build_text(b, ideas):
    lines = ["%d. %s" % (n + 1, ideas[i]["text"]) for n, i in enumerate(b["ideas"]) if i in ideas]
    return BUILD_WORDS[b.get("lang") or "he"] % (HERE, "\n".join(lines), b["id"], b["id"])


def build_link(b, ideas):
    return NEW_CHAT % (quote(build_text(b, ideas), safe=""), quote(HERE, safe=""))


def build_status(b, clean):
    """send -> building -> ready, or needs-you when the chat stopped without the BUILD file. Real, from files."""
    if b.get("cancelled"):
        return "cancelled", "בוטלה. הדף החי לא השתנה", "build-cancelled", None
    ready = ("ready", "מוכנה בעותק נפרד. מחכה לאישור שלך להחלפה", "build-ready", None)
    marker = os.path.exists(os.path.join(NEXT_DIR, "BUILD-%s.md" % b["id"]))
    m = find_tag("(office build %s)" % b["id"], b["ts"])
    if not m:
        return ready if marker else ("send", "מחכה ללחיצה על שלח בשיחה שנפתחה", "build-send", None)
    tu = turn(m["cli"], clean)
    if tu["state"] == "work":
        return "building", tu["line"], tu["lineKey"], tu["lineArg"]
    if marker:
        return ready
    if tu["state"] == "stuck":
        return "needs-you", tu["line"], tu["lineKey"], tu["lineArg"]
    return "needs-you", "השיחה עצרה בלי לסיים. כדאי לפתוח ולבדוק", "build-check", None


def start_build(body):
    """One build at a time. It opens nothing itself: it returns the link you open and send."""
    if not good_nonce(body.get("nonce")):
        return 400, {"error": "bad-nonce"}
    clean = Clean()
    with _qlock:
        _, ideas, builds = qstate()
        for b in builds.values():
            if b.get("nonce") == body["nonce"]:
                return 200, {"build": b["id"], "link": build_link(b, ideas), "duplicate": True}
            if build_status(b, clean)[0] not in ("ready", "cancelled"):
                return 409, {"error": "build-open", "build": b["id"], "link": build_link(b, ideas)}
        inc = [i["id"] for i in sorted(ideas.values(), key=lambda x: x["ts"]) if i["state"] == "included"]
        if not inc:
            return 400, {"error": "no-ideas"}
        rec = dict(stamp(), kind="build", id=new_id("B-", body["nonce"]), ideas=inc, nonce=body["nonce"],
                   lang=lang_of(body))
        qappend(rec)
    return 200, {"build": rec["id"], "link": build_link(rec, ideas)}


def cancel_build(body):
    """Drop an open build that is not running right now. The live page never changed, so nothing to undo."""
    bid = body.get("id")
    if not (isinstance(bid, str) and re.fullmatch(r"B-[0-9a-f]{6}", bid)):
        return 400, {"error": "bad-build"}
    clean = Clean()
    with _qlock:
        b = qstate()[2].get(bid)
        if not b or b["cancelled"]:
            return 409, {"error": "not-open"}
        if build_status(b, clean)[0] == "building":
            return 409, {"error": "running"}
        qappend(dict(stamp(), kind="build-cancel", id=bid))
    return 200, {"cancelled": bid}


def office_view(clean):
    """Requests with their real state, the idea list and the current build, for /api/live."""
    reqs, ideas, builds = qstate()
    t, rows = now(), []
    projs = config()["projects"]
    names = {p["id"]: clean(p["name"], p["id"], 40) for p in projs}
    names["new-project"] = "פרויקט חדש"
    for r in sorted(reqs.values(), key=lambda x: -x["ts"])[:8]:
        if t - r["ts"] > 3 * 86400:
            break
        m = find_tag("(office request %s)" % r["id"], r["ts"], r.get("chat"))
        reply, rkey, arg = None, None, None
        if not m:
            state, line, key = ("send", "מחכה ללחיצה על שלח בשיחה", "req-send") if t - r["ts"] < SEND_WAIT_S else \
                ("unsent", "לא נשלחה. אפשר לפתוח שוב", "req-unsent")
        else:
            tu = turn(m["cli"], clean)
            if tu["state"] in ("work", "stuck"):
                state = "working" if tu["state"] == "work" else "needs-you"
                line, key, arg = tu["line"], tu["lineKey"], tu["lineArg"]
            else:
                rep = last_reply(tu["tx"], r["ts"]) if tu["tx"] else None
                if rep and rep.rstrip().rstrip("‏‎").endswith("?"):
                    state, line, key = "needs-you", "בשיחה מחכה לך שאלה", "req-question"
                else:
                    state, line, key = "result", "יש תשובה", "req-result"
                reply = clean(rep, None, 240) if rep else None
                if rep and not reply:
                    reply, rkey = "התשובה מחכה בשיחה", "in-chat"
        text, proj = clean(r["text"], None, 120), names.get(r.get("project"))
        rows.append({"id": r["id"], "at": r["at"], "text": text or "(הטקסט מוסתר כאן, הוא שמור)",
                     "textKey": None if text else "hidden", "pid": r.get("project"),
                     "project": proj or "שיחה קיימת", "projectKey": None if proj else "existing", "item": r.get("item"),
                     "mode": "continue" if r.get("chat") else "new", "state": state, "line": line, "lineKey": key,
                     "lineArg": arg, "reply": reply, "replyKey": rkey,
                     "local": m["local"] if m else r.get("chat"),
                     "chat": CHAT_LINK % m["local"] if m else None})
    cur = None
    for b in sorted(builds.values(), key=lambda x: -x["ts"])[:1]:
        state, line, key, arg = build_status(b, clean)
        cur = {"id": b["id"], "at": b["at"], "state": state, "line": line, "lineKey": key, "lineArg": arg,
               "count": len(b["ideas"])}
        if state == "ready":
            for i in b["ideas"]:
                if i in ideas and ideas[i].get("build") == b["id"]:
                    ideas[i]["state"] = "ready"
    il = []
    for i in sorted(ideas.values(), key=lambda x: -x["ts"])[:20]:
        txt = clean(i["text"], None, 140)
        il.append({"id": i["id"], "text": txt or "(רעיון שמור)", "textKey": None if txt else "idea-hidden",
                   "state": i["state"]})
    picks = [{"id": p["id"], "name": names[p["id"]], "nameEn": clean(p["nameEn"], None, 40), "color": p["color"]}
             for p in projs]
    picks.append({"id": "new-project", "name": "פרויקט חדש", "nameEn": "New project", "color": "#888780"})
    return rows, il, cur, picks


def version():
    try:
        with open(os.path.join(HERE, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()[:20]
    except OSError:
        return ""


def live():
    clean = Clean()
    d, feed = desks(clean)
    feed = sorted(feed, key=lambda x: -(x["ts"] or 0))[:6]
    for x in feed:
        x.pop("ts", None)
    reqs, ideas, build, picks = office_view(clean)
    data = {"now": iso(now()), "desks": d, "waiting": waiting(clean), "feed": feed,
            "requests": reqs, "ideas": ideas, "build": build, "projects": picks}
    if leak_findings(data, clean.names):  # last line of defence: never serve a page with a private string
        data = {"now": iso(now()), "error": "privacy", "desks": [], "waiting": [], "feed": [],
                "requests": [], "ideas": [], "build": None, "projects": []}
    c = config()
    data.update(officeName=c["officeName"], defaultLang=c["defaultLang"], defaultProject=c["defaultProject"],
                hints=hints(), version=version())
    return data


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=HERE, **k)

    def okhost(self):
        port = self.server.server_address[1]
        return {"127.0.0.1:%d" % port, "localhost:%d" % port}

    def do_GET(self):
        # a rebound hostname (DNS rebinding) still reaches 127.0.0.1, but its Host header gives it away
        if self.headers.get("Host") not in self.okhost():
            self.send_error(403)
            return
        p = unquote(self.path.split("?")[0])
        if p == "/api/live":
            try:
                body = json.dumps(live(), ensure_ascii=False).encode("utf-8")
                code = 200
            except Exception as e:  # report the type only, never content
                body = json.dumps({"error": type(e).__name__}).encode("utf-8")
                code = 500
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if p not in SERVED:  # settings, tasks, pictures and code are never served
            self.send_error(404)
            return
        self.path = "/" + SERVED[p]
        super().do_GET()

    def do_HEAD(self):
        self.send_error(405)

    def do_POST(self):
        # same-origin JSON only: a page on another site can't send this header without a preflight we never answer
        okhost = self.okhost()
        origin = self.headers.get("Origin", "")
        fn = POSTS.get(self.path)
        if (not fn or self.headers.get("Host") not in okhost
                or origin.split("//", 1)[-1] not in okhost
                or self.headers.get("X-Office") != "1"
                or not self.headers.get("Content-Type", "").startswith("application/json")):
            self.send_error(403)
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            cap = IMG_MAX * 4 // 3 + 1000 if fn is upload else 8000  # only a picture may be large
            if n > cap:  # don't read it; drop the connection after answering
                self.close_connection = True
                code, out = 413, {"error": "too-big"}
            else:
                body = json.loads(self.rfile.read(n).decode("utf-8")) if n > 0 else {}
                code, out = fn(body if isinstance(body, dict) else {})
        except Exception as e:  # report the type only, never content
            code, out = 500, {"error": type(e).__name__}
        data = json.dumps(out, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass


POSTS = {"/api/answer": answer, "/api/request": make_request, "/api/reopen": reopen, "/api/idea": add_idea,
         "/api/idea-include": include_idea, "/api/build": start_build, "/api/build-cancel": cancel_build,
         "/api/upload": upload}


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    for stream in (sys.stdout, sys.stderr):  # a console that can't show Hebrew must not stop the office
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    config()  # a broken office.json stops here, with the reason, instead of on the first page load
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("The office is open: http://127.0.0.1:%d" % port)
    print("המשרד פתוח: http://127.0.0.1:%d" % port)
    if config()["example"]:
        print("Using office.example.json. Ask Claude to set up office.json (see README.md).")
    print("Close this window to stop. / כדי לסגור, סוגרים את החלון הזה.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
