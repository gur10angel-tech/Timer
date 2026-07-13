"""טיימר כנסים — לוח בקרה + מסך תצוגה לדוברים.

הפעלה מקומית:   streamlit run app.py
לוח בקרה:       הכתובת הרגילה של האפליקציה
מסך תצוגה:      אותה כתובת עם ‎?view=display‎ (לפתוח על המקרן וללחוץ F11)
"""

import json
import threading
import time

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="טיימר כנסים", page_icon="⏱️", layout="wide")


# ---------- מצב משותף לכל החיבורים (לוח הבקרה + כל מסכי התצוגה) ----------

@st.cache_resource
def shared_state():
    return {
        "lock": threading.Lock(),
        "timers": [],        # [{"id": int, "name": str, "minutes": float}]
        "next_id": 1,
        "active_id": None,
        "started_at": None,  # epoch של ההפעלה האחרונה
        "paused_at": None,   # epoch של ההשהיה, None כשהטיימר רץ
        "pause_total": 0.0,  # סך שניות השהיה שנצברו מאז ההפעלה
        "adjust": 0,         # שניות שנוספו/הופחתו בכפתורי ‎±1 דקה
        "message": "",
        "show_message": False,
    }


S = shared_state()


def _find(tid):
    return next((t for t in S["timers"] if t["id"] == tid), None)


def _active_index():
    ids = [t["id"] for t in S["timers"]]
    return ids.index(S["active_id"]) if S["active_id"] in ids else None


def add_timer(name, minutes):
    with S["lock"]:
        S["timers"].append({"id": S["next_id"], "name": name.strip(), "minutes": float(minutes)})
        S["next_id"] += 1


def update_timer(tid, name, minutes):
    with S["lock"]:
        t = _find(tid)
        if t:
            t["name"], t["minutes"] = name.strip(), float(minutes)


def delete_timer(tid):
    with S["lock"]:
        S["timers"] = [t for t in S["timers"] if t["id"] != tid]
        if S["active_id"] == tid:
            S["active_id"] = None
            S["started_at"] = None
            S["paused_at"] = None


def move_timer(tid, delta):
    with S["lock"]:
        ids = [t["id"] for t in S["timers"]]
        if tid not in ids:
            return
        i = ids.index(tid)
        j = i + delta
        if 0 <= j < len(S["timers"]):
            S["timers"][i], S["timers"][j] = S["timers"][j], S["timers"][i]


def play(tid):
    with S["lock"]:
        if _find(tid) is None:
            return
        S["active_id"] = tid
        S["started_at"] = time.time()
        S["paused_at"] = None
        S["pause_total"] = 0.0
        S["adjust"] = 0


def toggle_pause():
    with S["lock"]:
        if S["active_id"] is None or S["started_at"] is None:
            return
        now = time.time()
        if S["paused_at"] is None:
            S["paused_at"] = now
        else:
            S["pause_total"] += now - S["paused_at"]
            S["paused_at"] = None


def stop():
    with S["lock"]:
        S["active_id"] = None
        S["started_at"] = None
        S["paused_at"] = None


def adjust(seconds):
    with S["lock"]:
        if S["active_id"] is not None:
            S["adjust"] += seconds


def step(delta):
    with S["lock"]:
        if not S["timers"]:
            return
        idx = _active_index()
        if idx is None:
            idx = 0 if delta > 0 else len(S["timers"]) - 1
        else:
            idx = max(0, min(len(S["timers"]) - 1, idx + delta))
        tid = S["timers"][idx]["id"]
    play(tid)


def snapshot():
    """תמונת מצב לרכיב התצוגה — יציבה כל עוד לא בוצעה פעולה בלוח הבקרה,
    כך שה־iframe לא נטען מחדש בכל רענון והספירה חלקה."""
    with S["lock"]:
        t = _find(S["active_id"])
        idx = _active_index()
        next_name = ""
        if idx is not None and idx + 1 < len(S["timers"]):
            next_name = S["timers"][idx + 1]["name"]
        elif t is None and S["timers"]:
            next_name = S["timers"][0]["name"]
        msg = S["message"] if S["show_message"] else ""
        if t is None or S["started_at"] is None:
            return {"status": "idle", "name": "", "total": 0, "zero_epoch": 0,
                    "frozen": 0, "next_name": next_name, "message": msg}
        total = t["minutes"] * 60 + S["adjust"]
        zero = S["started_at"] + total + S["pause_total"]
        if S["paused_at"] is not None:
            return {"status": "paused", "name": t["name"], "total": total,
                    "zero_epoch": zero, "frozen": zero - S["paused_at"],
                    "next_name": next_name, "message": msg}
        return {"status": "running", "name": t["name"], "total": total,
                "zero_epoch": zero, "frozen": 0, "next_name": next_name, "message": msg}


# ---------- רכיב השעון (HTML/JS — מתקתק בצד הלקוח, חלק לגמרי) ----------

TIMER_TEMPLATE = """<!doctype html>
<html>
<head><meta charset="utf-8">
<style>
  html,body{margin:0;height:100%;background:#0b0f14;overflow:hidden;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;color:#fafafa;}
  #stage{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1vh;}
  #name{font-size:min(6vw,8vh);font-weight:600;color:#cbd5e1;text-align:center;padding:0 3vw;}
  #clock{font-weight:800;line-height:1;font-variant-numeric:tabular-nums;letter-spacing:.02em;}
  #badge{font-size:min(3.4vw,4.5vh);color:#94a3b8;min-height:1em;}
  #msg{font-size:min(5vw,6.5vh);font-weight:700;color:#fde047;text-align:center;padding:0 4vw;}
  #next{position:fixed;bottom:4vh;width:100%;text-align:center;font-size:min(3vw,3.8vh);color:#64748b;}
  #bar{position:fixed;bottom:0;left:0;width:100%;height:1.8vh;background:#1e293b;}
  #fill{height:100%;width:100%;background:#22c55e;transition:width .25s linear;}
  .flash{animation:flashbg .5s ease-in-out 4;}
  @keyframes flashbg{50%{background:#7f1d1d;}}
</style></head>
<body>
<div id="stage">
  <div id="name" dir="auto"></div>
  <div id="clock">--:--</div>
  <div id="badge" dir="auto"></div>
  <div id="msg" dir="auto"></div>
</div>
<div id="next" dir="auto"></div>
<div id="bar"><div id="fill"></div></div>
<script>
const D = __DATA__;
const el = id => document.getElementById(id);
el('name').textContent = D.name;
el('msg').textContent = D.message || '';
el('next').textContent = D.next_name ? ('הבא בתור: ' + D.next_name) : '';

function fmt(sec){
  const neg = sec < 0;
  let s = neg ? Math.floor(-sec) : Math.ceil(sec);
  const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), r = s%60;
  const pad = n => String(n).padStart(2,'0');
  return (neg && s > 0 ? '-' : '') + (h>0 ? h+':'+pad(m)+':'+pad(r) : m+':'+pad(r));
}

// תיקון סטיית שעונים: הדף הראשי כותב את שעון השרת לתגית מוסתרת בכל רענון,
// וכאן מחושבת הסטייה מולו (מינימום על חלון דגימות ≈ סטייה אמיתית + זמן רשת),
// כך שהספירה נכונה גם כששעון מחשב המקרן לא מכוון. אם הגישה חסומה — נשארים עם שעון הלקוח.
let skew = 0;
const skewSamples = [];
function sampleSkew(){
  try {
    const el = window.parent.document.getElementById('server-clock');
    if (!el) return;
    const srv = parseFloat(el.getAttribute('data-epoch'));
    if (!isFinite(srv)) return;
    skewSamples.push(Date.now()/1000 - srv);
    if (skewSamples.length > 8) skewSamples.shift();
    skew = Math.min(...skewSamples);
  } catch (e) { /* iframe מבודד — נופלים חזרה לשעון הלקוח */ }
}
sampleSkew();
setInterval(sampleSkew, 500);
const nowS = () => Date.now()/1000 - skew;

let wasOver = D.status === 'running' ? (D.zero_epoch - nowS()) <= 0 : true;

function tick(){
  const c = el('clock');
  if (D.status === 'idle'){
    c.textContent = '--:--';
    c.style.color = '#334155';
    c.style.fontSize = 'min(24vw,55vh)';
    el('badge').textContent = D.next_name ? 'מוכן — לחצו הפעל בלוח הבקרה' : 'הוסיפו טיימרים בלוח הבקרה';
    el('fill').style.width = '0%';
    return;
  }
  const rem = D.status === 'running' ? (D.zero_epoch - nowS()) : D.frozen;
  const warn = 60;  // הדקה האחרונה כולה בכתום
  const over = rem <= 0;
  const txt = fmt(rem);
  c.textContent = txt;
  c.style.color = over ? '#ef4444' : (rem <= warn ? '#f59e0b' : '#fafafa');
  c.style.fontSize = txt.length > 6 ? 'min(18vw,50vh)' : 'min(26vw,56vh)';
  el('badge').textContent = D.status === 'paused' ? '⏸ מושהה' : (over ? 'חריגה מהזמן!' : '');
  const frac = D.total > 0 ? Math.max(0, Math.min(1, rem / D.total)) : 0;
  el('fill').style.width = (frac*100) + '%';
  el('fill').style.background = over ? '#ef4444' : (rem <= warn ? '#f59e0b' : '#22c55e');
  if (over && !wasOver && D.status === 'running'){
    document.body.classList.add('flash');
    setTimeout(() => document.body.classList.remove('flash'), 2200);
  }
  wasOver = over;
}
tick();
setInterval(tick, 100);
</script>
</body></html>"""


def timer_html(snap):
    data = json.dumps(snap, ensure_ascii=False).replace("</", "<\\/")
    return TIMER_TEMPLATE.replace("__DATA__", data)


def server_clock_tag():
    """תגית מוסתרת עם שעון השרת — רכיב השעון קורא אותה כדי לבטל סטיית שעונים
    בין השרת למחשב שמציג את הטיימר."""
    return (f'<span id="server-clock" data-epoch="{time.time():.3f}" '
            f'style="display:none"></span>')


# ---------- עיצוב ----------

RTL_CSS = """<style>
.stApp {direction: rtl;}
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] {text-align: right;}
.stTextInput input, .stTextArea textarea {direction: rtl; text-align: right;}
h1, h2, h3 {text-align: right;}
</style>"""

DISPLAY_CSS = """<style>
header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"] {display: none !important;}
.block-container, [data-testid="stMainBlockContainer"]
  {padding: 0 !important; margin: 0 !important; max-width: 100vw !important;}
[data-testid="stVerticalBlock"] {gap: 0 !important;}
[data-testid="stElementContainer"] {margin: 0 !important;}
.stApp, [data-testid="stAppViewContainer"] {background: #0b0f14 !important; overflow: hidden;}
iframe {display: block; height: 100vh !important; width: 100vw !important; border: 0;}
</style>"""


# ---------- מסך תצוגה (למקרן / למסך של הדובר) ----------

def display_page():
    st.markdown(DISPLAY_CSS, unsafe_allow_html=True)

    @st.fragment(run_every=1.0)
    def live():
        st.markdown(server_clock_tag(), unsafe_allow_html=True)
        components.html(timer_html(snapshot()), height=720)

    live()


# ---------- לוח בקרה ----------

def parse_bulk(text):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        name, _, mins = line.rpartition(",")
        try:
            m = float(mins.strip())
            name = name.strip()
        except ValueError:
            name, m = line, 10.0
        if name:
            rows.append((name, m))
    return rows


def controller_page():
    st.markdown(RTL_CSS, unsafe_allow_html=True)
    st.title("⏱️ טיימר כנסים")
    st.markdown(
        '<a href="?view=display" target="_blank" style="font-size:1.1em;font-weight:600;">'
        '🖥️ פתיחת מסך התצוגה לדובר</a>'
        '<span style="color:#94a3b8;"> — לפתוח על המחשב שמחובר למקרן וללחוץ F11 למסך מלא</span>',
        unsafe_allow_html=True)

    sched_col, live_col = st.columns([5, 4], gap="large")

    # --- לו"ז ---
    with sched_col:
        st.subheader("לו״ז הכנס")
        with st.form("add_timer", clear_on_submit=True, border=True):
            c1, c2 = st.columns([3, 1])
            name = c1.text_input("שם הדובר / נושא", placeholder="דברי פתיחה")
            minutes = c2.number_input("דקות", min_value=0.5, max_value=600.0, value=10.0, step=1.0)
            if st.form_submit_button("➕ הוספה ללו״ז", use_container_width=True) and name.strip():
                add_timer(name, minutes)
                st.rerun()

        if not S["timers"]:
            st.info("אין עדיין טיימרים — הוסיפו את הדובר הראשון למעלה.")

        for i, t in enumerate(list(S["timers"])):
            is_active = t["id"] == S["active_id"]
            with st.container(border=True):
                c_play, c_txt, c_edit, c_up, c_dn, c_del = st.columns(
                    [1.3, 5, 1, 1, 1, 1], vertical_alignment="center")
                if c_play.button("🔁" if is_active else "▶️", key=f"pl{t['id']}",
                                 help="הפעלה מחדש מההתחלה" if is_active else "הפעלה",
                                 use_container_width=True):
                    play(t["id"])
                    st.rerun()
                status = " · 🟢 משודר כעת" if is_active else ""
                c_txt.markdown(f"**{i + 1}. {t['name']}**  \n{t['minutes']:g} דקות{status}")
                with c_edit.popover("✏️"):
                    en = st.text_input("שם", value=t["name"], key=f"en{t['id']}")
                    em = st.number_input("דקות", min_value=0.5, max_value=600.0,
                                         value=float(t["minutes"]), step=1.0, key=f"em{t['id']}")
                    if st.button("שמירה", key=f"es{t['id']}"):
                        update_timer(t["id"], en, em)
                        st.rerun()
                if c_up.button("⬆️", key=f"up{t['id']}", disabled=(i == 0)):
                    move_timer(t["id"], -1)
                    st.rerun()
                if c_dn.button("⬇️", key=f"dn{t['id']}", disabled=(i == len(S["timers"]) - 1)):
                    move_timer(t["id"], 1)
                    st.rerun()
                if c_del.button("🗑️", key=f"del{t['id']}"):
                    delete_timer(t["id"])
                    st.rerun()

        with st.expander("📋 ייבוא לו״ז מלא בהדבקה"):
            bulk = st.text_area("שורה לכל דובר בפורמט: שם, דקות",
                                placeholder="דברי פתיחה, 10\nהרצאה מרכזית, 45\nהפסקת קפה, 15",
                                height=140, key="bulk_text")
            replace = st.checkbox("החלפת הלו״ז הקיים (במקום הוספה בסופו)", key="bulk_replace")
            if st.button("ייבוא", use_container_width=True):
                rows = parse_bulk(bulk)
                if rows:
                    if replace:
                        with S["lock"]:
                            S["timers"] = []
                            S["active_id"] = None
                            S["started_at"] = None
                            S["paused_at"] = None
                    for nm, m in rows:
                        add_timer(nm, m)
                    st.rerun()

        with st.expander("💾 גיבוי ושחזור הלו״ז"):
            st.caption("הלו״ז נשמר בזיכרון השרת — אם האפליקציה נרדמת (בתוכנית החינמית) הוא יימחק. "
                       "מומלץ להוריד גיבוי אחרי שמזינים את הלו״ז.")
            st.download_button("⬇️ הורדת הלו״ז (JSON)",
                               data=json.dumps(S["timers"], ensure_ascii=False, indent=2),
                               file_name="conference-schedule.json", mime="application/json",
                               use_container_width=True)
            up = st.file_uploader("שחזור מקובץ גיבוי", type=["json"], key="restore")
            if up is not None and st.button("החלפת הלו״ז בקובץ שהועלה", use_container_width=True):
                try:
                    data = json.load(up)
                    with S["lock"]:
                        S["timers"] = []
                        S["active_id"] = None
                        S["started_at"] = None
                        S["paused_at"] = None
                        for d in data:
                            S["timers"].append({"id": S["next_id"],
                                                "name": str(d.get("name", "ללא שם")),
                                                "minutes": float(d.get("minutes", 10))})
                            S["next_id"] += 1
                    st.rerun()
                except (ValueError, TypeError, AttributeError):
                    st.error("קובץ לא תקין")

    # --- שידור חי ---
    with live_col:
        st.subheader("שידור חי")

        @st.fragment(run_every=1.0)
        def live_preview():
            st.markdown(server_clock_tag(), unsafe_allow_html=True)
            components.html(timer_html(snapshot()), height=250)

        live_preview()

        running = S["active_id"] is not None and S["started_at"] is not None and S["paused_at"] is None
        has_active = S["active_id"] is not None
        b = st.columns(6)
        if b[0].button("⏮️", help="הדובר הקודם", use_container_width=True):
            step(-1)
            st.rerun()
        if b[1].button("⏸️" if running else "▶️", help="הפעלה / השהיה", use_container_width=True):
            if not has_active:
                if S["timers"]:
                    play(S["timers"][0]["id"])
            else:
                toggle_pause()
            st.rerun()
        if b[2].button("⏭️", help="הדובר הבא", use_container_width=True):
            step(1)
            st.rerun()
        if b[3].button("‎+1ד׳", help="הוספת דקה", use_container_width=True, disabled=not has_active):
            adjust(60)
            st.rerun()
        if b[4].button("‎-1ד׳", help="הפחתת דקה", use_container_width=True, disabled=not has_active):
            adjust(-60)
            st.rerun()
        if b[5].button("⏹️", help="עצירה", use_container_width=True, disabled=not has_active):
            stop()
            st.rerun()

        st.text_input("הודעה לדובר", key="msg_text", placeholder="לדוגמה: נשארו 5 דקות, נא לסכם")
        m1, m2 = st.columns(2)
        if m1.button("📢 הצגת ההודעה על המסך", use_container_width=True):
            with S["lock"]:
                S["message"] = st.session_state.msg_text
                S["show_message"] = True
            st.rerun()
        if m2.button("🧹 הסתרת ההודעה", use_container_width=True):
            with S["lock"]:
                S["show_message"] = False
            st.rerun()


# ---------- ניתוב ----------

if st.query_params.get("view") == "display":
    display_page()
else:
    controller_page()
