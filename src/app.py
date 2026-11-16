"""DataAI Explorer - local AI data workspace (Streamlit).

Save as src/app.py and run:  python -m streamlit run src/app.py
"""
import html
import inspect
import json
import os
import re
import tempfile
import urllib.request

import pandas as pd
import streamlit as st

from src.db import (
    get_table_names,
    get_table_schema,
    import_csv_to_table,
    run_select,
)
from src.nl2sql import generate_sql

try:
    from src.db import DB_PATH
except Exception:
    DB_PATH = os.path.join("data", "ecommerce.db")

OLLAMA_URL = "http://localhost:11434"
PAGES = ["Home", "Upload Data", "Browse Data", "Ask AI", "Settings"]

st.set_page_config(page_title="DataAI Explorer", page_icon="✦", layout="wide")

# --------------------------------------------------------------------------
# Styling  (pastel palette, framed app shell, top navbar)
# --------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800&display=swap');

:root{
  --ink:#272c4f; --muted:#6b7194; --line:#e4e8f5; --tint:#f5f7ff; --frame:#ffffff;
  --primary:#5b6bda; --primary-d:#4654c2; --primary-soft:#e2e7ff;
  --mint:#d9f3e8; --mint-ink:#1f7a58;
  --sky:#dcebfc;  --sky-ink:#2a5fa8;
  --lilac:#e8e1fa; --lilac-ink:#5b3fb0;
  --peach:#fde7da; --peach-ink:#a4551f;
  --rose:#fde3e3; --rose-ink:#b03a3a;
}
html, body, [class*="css"], .stApp { font-family:'Figtree', system-ui, sans-serif; color:var(--ink); }
.stApp { background:linear-gradient(160deg,#e6ecfb 0%,#eee8fa 55%,#e3f1f6 100%); background-attachment:fixed; }
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { display:none !important; }
header[data-testid="stHeader"] { background:transparent; height:0; }

/* ---------- the frame ---------- */
[data-testid="stMainBlockContainer"], .block-container{
  max-width:1180px; width:calc(100% - 2rem); margin:1.6rem auto 2rem; padding:0 2.4rem 1.4rem !important;
  background:var(--frame); border:1px solid var(--line); border-radius:24px;
  box-shadow:0 28px 60px -34px rgba(70,80,160,.45);
}

/* ---------- top navbar (first row that contains .brand) ---------- */
div[data-testid="stHorizontalBlock"]:has(.brand){
  width:calc(100% + 4.8rem); max-width:none; margin:0 0 1.4rem -2.4rem; padding:.85rem 2.4rem;
  background:var(--tint); border-bottom:1px solid var(--line); border-radius:24px 24px 0 0;
  align-items:center; gap:1rem;
}
.brand{ display:flex; align-items:center; gap:.7rem; }
.mark{ width:38px; height:38px; border-radius:12px; display:grid; place-items:center; color:#fff; font-size:19px;
       background:linear-gradient(135deg,#7686ee,#8f7be0); }
.brand b{ font-size:1.12rem; letter-spacing:-.01em; display:block; line-height:1.15; }
.brand span{ font-size:.78rem; color:var(--muted); }
.statuswrap{ display:flex; justify-content:flex-end; }
.status{ display:inline-flex; align-items:center; gap:.45rem; font-size:.82rem; font-weight:700; padding:.4rem .85rem; border-radius:999px; }
.status .dot{ width:8px; height:8px; border-radius:50%; }
.status.on{ background:var(--mint); color:var(--mint-ink); } .status.on .dot{ background:#2fb585; }
.status.off{ background:var(--rose); color:var(--rose-ink); } .status.off .dot{ background:#e05a5a; }

/* nav links = radio restyled */
div[data-testid="stRadio"] > div[role="radiogroup"]{ gap:.2rem; justify-content:center; flex-wrap:wrap; }
div[data-testid="stRadio"] label[data-baseweb="radio"]{
  margin:0; padding:.48rem 1.05rem; border-radius:10px; cursor:pointer; transition:background .15s; }
div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child{ display:none; }
div[data-testid="stRadio"] label[data-baseweb="radio"] p{ font-weight:600; font-size:.93rem; color:var(--muted); margin:0; }
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover{ background:#fff; }
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked){ background:var(--primary-soft); }
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p{ color:var(--primary-d); }

/* ---------- content ---------- */
.ph h2{ font-size:1.7rem; font-weight:800; letter-spacing:-.02em; margin:.2rem 0 .15rem; padding:0; }
.ph p{ color:var(--muted); margin:0 0 .4rem; font-size:.98rem; }
.sec{ font-size:1.25rem; font-weight:800; margin:1.6rem 0 .7rem; letter-spacing:-.015em; }

.hero{ padding:2.4rem 2.6rem; border-radius:20px; border:1px solid #dfe5fa;
  background:
    radial-gradient(circle at 92% 15%, rgba(255,255,255,.85), transparent 38%),
    linear-gradient(120deg,#dde7ff 0%,#e7dffb 55%,#d6f0e7 100%); }
.hero h1{ font-size:2.45rem; font-weight:800; letter-spacing:-.025em; margin:0 0 .6rem; padding:0; line-height:1.12; color:var(--ink); }
.hero p{ color:#4a5078; max-width:600px; font-size:1.02rem; line-height:1.6; margin:0 0 1.1rem; }
.pill{ display:inline-block; margin:0 .4rem .3rem 0; padding:.3rem .8rem; border-radius:999px; background:rgba(255,255,255,.75);
  border:1px solid rgba(91,107,218,.18); color:var(--primary-d); font-size:.8rem; font-weight:700; }

.num{ width:34px; height:34px; border-radius:11px; display:grid; place-items:center; font-weight:800; margin-bottom:.6rem; }
.n1{ background:var(--mint); color:var(--mint-ink); } .n2{ background:var(--sky); color:var(--sky-ink); } .n3{ background:var(--lilac); color:var(--lilac-ink); }
.ctitle{ font-size:1.1rem; font-weight:800; margin:0 0 .2rem; }
.cdesc{ color:var(--muted); font-size:.9rem; margin:0 0 .5rem; min-height:2.7em; }
.chip{ display:inline-block; margin:.15rem .25rem .15rem 0; padding:.22rem .65rem; border-radius:999px;
  background:var(--lilac); color:var(--lilac-ink); font-size:.8rem; font-weight:700; }
.chip.sky{ background:var(--sky); color:var(--sky-ink); }
.kv{ display:flex; justify-content:space-between; gap:1rem; padding:.5rem 0; border-bottom:1px solid var(--line); font-size:.92rem; }
.kv:last-child{ border-bottom:none; } .kv span{ color:var(--muted); }
.kv b{ font-weight:600; text-align:right; word-break:break-all; }
.qline{ color:var(--muted); font-size:.88rem; margin:.2rem 0 .5rem; }

div[data-testid="stVerticalBlockBorderWrapper"]{ background:#fcfcff; border-color:var(--line) !important; border-radius:16px; }

/* buttons */
.stButton > button, .stDownloadButton > button{
  border-radius:11px; border:1px solid var(--line); background:#fff; color:var(--ink); font-weight:600; padding:.55rem 1rem; transition:all .15s; }
.stButton > button:hover, .stDownloadButton > button:hover{ border-color:var(--primary); color:var(--primary-d); background:var(--tint); }
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"]{ background:var(--primary); color:#fff; border-color:var(--primary); }
.stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover{ background:var(--primary-d); color:#fff; border-color:var(--primary-d); }
.stButton > button:focus-visible{ outline:2px solid var(--primary); outline-offset:2px; }

/* inputs */
textarea, input{ border-radius:10px !important; }
[data-testid="stFileUploaderDropzone"]{ background:var(--tint); border:1.5px dashed #b9c2f2; border-radius:14px; }
[data-testid="stDataFrame"]{ border:1px solid var(--line); border-radius:12px; overflow:hidden; }
[data-testid="stExpander"]{ border-radius:12px; border-color:var(--line); }
.foot{ text-align:center; color:var(--muted); font-size:.82rem; margin-top:2.2rem; padding-top:1rem; border-top:1px solid var(--line); }
</style>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|truncate)\b", re.I
)


def clean_generated_sql(text) -> str:
    """Strip Markdown fences / chatter and keep a single SQL statement."""
    if isinstance(text, dict):
        text = text.get("sql") or text.get("query") or ""
    if isinstance(text, (tuple, list)):
        text = text[0] if text else ""
    text = str(text or "")
    text = re.sub(r"```(?:sql)?", "", text, flags=re.I).replace("```", "").strip()
    m = re.search(r"\b(select|with)\b", text, flags=re.I)
    if m:
        text = text[m.start():]
    text = text.split(";")[0].strip()
    return text + ";" if text else ""


def is_read_only(sql: str):
    """Front-end guard. run_select() in db.py remains the real enforcement."""
    body = sql.strip().rstrip(";").strip()
    if not body:
        return False, "The query is empty."
    if not re.match(r"^(select|with)\b", body, flags=re.I):
        return False, "Only SELECT queries are allowed."
    if ";" in body:
        return False, "Only one statement can be run at a time."
    bad = FORBIDDEN.search(body)
    if bad:
        return False, f"Blocked: “{bad.group(0).upper()}” is not allowed (read-only mode)."
    return True, ""


def as_dataframe(res) -> pd.DataFrame:
    if isinstance(res, pd.DataFrame):
        return res
    if isinstance(res, dict) and "rows" in res:
        return pd.DataFrame(res["rows"], columns=res.get("columns"))
    if (
        isinstance(res, (tuple, list)) and len(res) == 2
        and isinstance(res[0], (tuple, list)) and all(isinstance(c, str) for c in res[0])
        and isinstance(res[1], list)
        and (not res[1] or not isinstance(res[1][0], (str, bytes, int, float)))
    ):
        return pd.DataFrame([list(r) for r in res[1]], columns=list(res[0]))
    if isinstance(res, list) and res and isinstance(res[0], dict):
        return pd.DataFrame(res)
    return pd.DataFrame(res)


def run_query(sql: str) -> pd.DataFrame:
    ok, why = is_read_only(sql)
    if not ok:
        raise ValueError(why)
    try:
        res = run_select(sql)
    except TypeError:
        res = run_select(DB_PATH, sql)
    return as_dataframe(res)


def list_tables():
    try:
        names = get_table_names()
    except Exception:
        return []
    out = [n[0] if isinstance(n, (tuple, list)) else n for n in names]
    return [n for n in out if not str(n).startswith("sqlite_")]


def safe_table_preview(table: str, limit: int = 10) -> pd.DataFrame:
    return run_query(f'SELECT * FROM "{table}" LIMIT {int(limit)};')


def count_rows(table: str) -> int:
    try:
        return int(run_query(f'SELECT COUNT(*) AS n FROM "{table}";').iloc[0, 0])
    except Exception:
        return 0


def column_names(table: str):
    try:
        return list(safe_table_preview(table, 1).columns)
    except Exception:
        return []


def schema_frame(table: str):
    """Return the schema as a DataFrame if possible, else the raw value."""
    sch = get_table_schema(table)
    if isinstance(sch, pd.DataFrame):
        return sch
    if isinstance(sch, (list, tuple)) and sch:
        first = sch[0]
        if isinstance(first, dict):
            return pd.DataFrame(sch)
        if isinstance(first, (list, tuple)) and len(first) == 6:
            return pd.DataFrame(sch, columns=["cid", "name", "type", "notnull", "default", "primary_key"])
        if isinstance(first, (list, tuple)):
            return pd.DataFrame(sch)
    return sch


def sanitize_table_name(name: str) -> str:
    name = re.sub(r"\W+", "_", name.strip()).strip("_").lower()
    if not name:
        return ""
    return f"t_{name}" if name[0].isdigit() else name


def do_import(uploaded, table: str):
    """Save the upload to a temp file and call import_csv_to_table()."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(uploaded.getvalue())
        path = tmp.name
    try:
        params = [p.lower() for p in inspect.signature(import_csv_to_table).parameters]
        first = params[0] if params else ""
        if len(params) >= 3 and ("db" in first or "conn" in first):
            args = (DB_PATH, path, table)
        elif "table" in first or first == "name":
            args = (table, path)
        elif first in ("df", "dataframe", "data"):
            uploaded.seek(0)
            args = (pd.read_csv(uploaded), table)
        else:
            args = (path, table)
        return import_csv_to_table(*args)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


@st.cache_data(ttl=10)
def ollama_status():
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=1.5) as r:
            data = json.load(r)
        return True, [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        return False, []


def go_to(page: str, **state):
    """Callback: switch page (and optionally preselect a table)."""
    st.session_state["page"] = page
    for k, v in state.items():
        st.session_state[k] = v


def set_question(text: str):
    st.session_state["question"] = text


def reuse_question(question: str, table: str):
    st.session_state["question"] = question
    if table in list_tables():
        st.session_state["ask_table"] = table


def page_header(title: str, subtitle: str):
    st.markdown(f'<div class="ph"><h2>{html.escape(title)}</h2><p>{html.escape(subtitle)}</p></div>',
                unsafe_allow_html=True)


def chips(items, cls=""):
    return "".join(f'<span class="chip {cls}">{html.escape(str(i))}</span>' for i in items)


def kv(rows):
    return "".join(f'<div class="kv"><span>{html.escape(k)}</span><b>{html.escape(str(v))}</b></div>' for k, v in rows)


# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------
st.session_state.setdefault("page", "Home")
st.session_state.setdefault("last", None)
st.session_state.setdefault("question", "")
st.session_state.setdefault("history", [])

online, models = ollama_status()
tables = list_tables()

# --------------------------------------------------------------------------
# Top navbar
# --------------------------------------------------------------------------
nav_brand, nav_links, nav_status = st.columns([2.3, 5.2, 2.0])
with nav_brand:
    st.markdown(
        '<div class="brand"><div class="mark">✦</div>'
        '<div><b>DataAI Explorer</b><span>Local AI data workspace</span></div></div>',
        unsafe_allow_html=True,
    )
with nav_links:
    st.radio("Navigation", PAGES, key="page", horizontal=True, label_visibility="collapsed")
with nav_status:
    st.markdown(
        f'<div class="statuswrap"><div class="status {"on" if online else "off"}"><div class="dot"></div>'
        f'{"Local AI ready" if online else "Local AI offline"}</div></div>',
        unsafe_allow_html=True,
    )
page = st.session_state["page"]


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
def page_home():
    st.markdown(
        """
<div class="hero">
  <h1>Explore your data with AI.</h1>
  <p>Upload datasets, browse your tables and ask questions in everyday language.
  DataAI Explorer turns them into SQL with your local model and runs them on your SQLite database.</p>
  <span class="pill">Runs locally</span><span class="pill">Your data stays on this computer</span><span class="pill">Read-only queries</span>
</div>
<div class="sec">Get started</div>
""",
        unsafe_allow_html=True,
    )
    cards = [
        ("n1", "1", "Upload your data", "Import a CSV file into your local database.", "Upload Data", "Upload data"),
        ("n2", "2", "Browse tables", "Check table structures, columns and records.", "Browse Data", "Browse data"),
        ("n3", "3", "Ask AI", "Turn a question into SQL and see the answer.", "Ask AI", "Start asking"),
    ]
    for col, (cls, n, title, desc, target, label) in zip(st.columns(3), cards):
        with col.container(border=True):
            st.markdown(
                f'<div class="num {cls}">{n}</div><div class="ctitle">{title}</div><div class="cdesc">{desc}</div>',
                unsafe_allow_html=True,
            )
            st.button(label, key=f"home_{target}", on_click=go_to, args=(target,),
                      type="primary" if target == "Ask AI" else "secondary", use_container_width=True)

    st.markdown('<div class="sec">Your tables</div>', unsafe_allow_html=True)
    if not tables:
        st.info("No tables yet. Upload a CSV file to create your first table.")
        return
    overview = [{"Table": t, "Rows": count_rows(t), "Columns": len(column_names(t))} for t in tables]
    st.dataframe(pd.DataFrame(overview), use_container_width=True, hide_index=True)


def page_upload():
    page_header("Upload data", "Add a CSV file as a new table in your local database.")
    left, right = st.columns([1.7, 1])
    with left:
        with st.container(border=True):
            up = st.file_uploader("Choose a CSV file", type=["csv"])
            default = sanitize_table_name(os.path.splitext(up.name)[0]) if up else ""
            raw_name = st.text_input("Table name", value=default, key=f"tname_{up.name if up else 'none'}",
                                     help="Letters, numbers and underscores only.")
            name = sanitize_table_name(raw_name)
            if raw_name and name != raw_name:
                st.caption(f"Will be saved as **{name}**")
            if name and name in tables:
                st.warning(f"A table named “{name}” already exists. Importing may replace its data.")
            if up:
                try:
                    up.seek(0)
                    st.caption("Preview of the first 5 rows")
                    st.dataframe(pd.read_csv(up, nrows=5), use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"This file could not be read as a CSV: {e}")
            if st.button("Import dataset", type="primary", disabled=not (up and name)):
                try:
                    with st.spinner("Importing…"):
                        do_import(up, name)
                    st.success(f"Imported into table “{name}” ({count_rows(name)} rows).")
                    c1, c2 = st.columns(2)
                    c1.button("Browse this table", on_click=go_to, args=("Browse Data",),
                              kwargs={"browse_table": name}, use_container_width=True)
                    c2.button("Ask questions about it", on_click=go_to, args=("Ask AI",),
                              kwargs={"ask_table": name}, use_container_width=True)
                except Exception as e:
                    st.error(f"Import failed: {e}")
    with right:
        with st.container(border=True):
            st.markdown("**Available tables**")
            fresh = list_tables()
            if fresh:
                for t in fresh:
                    st.markdown(f'<div class="kv"><span>{html.escape(t)}</span><b>{count_rows(t)} rows</b></div>',
                                unsafe_allow_html=True)
            else:
                st.caption("No tables yet.")
        with st.container(border=True):
            st.markdown("**Tips**")
            st.caption("Use a CSV with a header row. Column names become the fields the AI can query, "
                       "so clear names such as “marks” or “order_date” give better answers.")


def page_browse():
    page_header("Browse data", "Look at a table before you ask questions about it.")
    if not tables:
        st.info("No tables yet. Upload a CSV file first.")
        st.button("Go to Upload Data", on_click=go_to, args=("Upload Data",))
        return
    if st.session_state.get("browse_table") not in tables:
        st.session_state["browse_table"] = tables[0]
    with st.container(border=True):
        c0, c1, c2 = st.columns([1.4, 1, 1.6])
        table = c0.selectbox("Table", tables, key="browse_table")
        c1.metric("Total rows", count_rows(table))
        limit = c2.slider("Rows to preview", 5, 200, 10, step=5)
        cols = column_names(table)
        if cols:
            st.markdown(chips(cols, "sky"), unsafe_allow_html=True)
        try:
            st.dataframe(safe_table_preview(table, limit), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Could not load records: {e}")
        with st.expander("Table structure"):
            try:
                sch = schema_frame(table)
                if isinstance(sch, pd.DataFrame):
                    st.dataframe(sch, use_container_width=True, hide_index=True)
                else:
                    st.code(str(sch), language="sql")
            except Exception as e:
                st.error(f"Could not read the structure: {e}")
    st.button("Ask questions about this table", type="primary", on_click=go_to,
              args=("Ask AI",), kwargs={"ask_table": table})


def page_ask():
    page_header("Ask AI", "Ask in plain English. The model writes read-only SQL and the result appears below.")
    if not tables:
        st.info("No tables yet. Upload a CSV file first.")
        st.button("Go to Upload Data", on_click=go_to, args=("Upload Data",))
        return
    if st.session_state.get("ask_table") not in tables:
        st.session_state["ask_table"] = tables[0]
    if not online:
        st.warning("Local AI is offline. Start Ollama (run `ollama serve`) and make sure `llama3` is installed.")

    left, right = st.columns([2.4, 1])
    with left:
        with st.container(border=True):
            table = st.selectbox("Table", tables, key="ask_table")
            st.text_area("Your question", key="question", height=100,
                         placeholder="e.g. Which students scored more than 80 marks?")
            st.caption("Try an example")
            examples = ["Show the first 10 rows", "How many records are there?", "Show rows with the highest values"]
            for i, (col, ex) in enumerate(zip(st.columns(len(examples)), examples)):
                col.button(ex, key=f"ex_{i}", on_click=set_question, args=(ex,), use_container_width=True)
            run = st.button("Generate SQL and run", type="primary")

        if run:
            q = st.session_state["question"].strip()
            if not q:
                st.warning("Type a question first.")
            else:
                result = {"question": q, "table": table, "sql": "", "df": None, "error": None}
                try:
                    with st.spinner("Thinking…"):
                        result["sql"] = clean_generated_sql(generate_sql(q, table))
                    if result["sql"]:
                        result["df"] = run_query(result["sql"])
                    else:
                        result["error"] = "The model did not return a SQL query. Try rephrasing the question."
                except Exception as e:
                    result["error"] = str(e)
                st.session_state["last"] = result
                if not result["error"]:
                    hist = [h for h in st.session_state["history"] if (h["question"], h["table"]) != (q, table)]
                    st.session_state["history"] = ([{"question": q, "table": table}] + hist)[:6]

        last = st.session_state["last"]
        if last:
            st.markdown('<div class="sec">Result</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="qline">{html.escape(last["question"])} &nbsp;·&nbsp; table: '
                        f'<b>{html.escape(last["table"])}</b></div>', unsafe_allow_html=True)
            if last["sql"]:
                st.markdown("**Generated SQL**")
                st.code(last["sql"], language="sql")
            if last["error"]:
                st.error(last["error"])
            else:
                df = last["df"]
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption(f"{len(df)} row(s) returned")
                st.download_button("Download results as CSV", df.to_csv(index=False).encode("utf-8"),
                                   file_name="query_results.csv", mime="text/csv")
                with st.expander("Edit the SQL and run it again"):
                    edited = st.text_area("SQL", value=last["sql"], height=120, key="edited_sql")
                    if st.button("Run edited SQL"):
                        try:
                            sql = clean_generated_sql(edited)
                            st.session_state["last"] = {**last, "sql": sql, "df": run_query(sql), "error": None}
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

    with right:
        with st.container(border=True):
            st.markdown("**Columns in this table**")
            cols = column_names(table)
            if cols:
                st.markdown(chips(cols, "sky"), unsafe_allow_html=True)
                st.caption("Use these names in your question for more accurate SQL.")
            else:
                st.caption("No columns found.")
        with st.container(border=True):
            st.markdown("**Recent questions**")
            if not st.session_state["history"]:
                st.caption("Your questions will appear here.")
            for i, h in enumerate(st.session_state["history"]):
                label = h["question"] if len(h["question"]) <= 34 else h["question"][:33] + "…"
                st.button(label, key=f"hist_{i}", help=f'{h["question"]}  (table: {h["table"]})',
                          on_click=reuse_question, args=(h["question"], h["table"]), use_container_width=True)


def page_settings():
    page_header("Settings", "Information about this workspace.")
    size = f"{os.path.getsize(DB_PATH) / 1024:.1f} KB" if os.path.exists(DB_PATH) else "not found"
    a, b = st.columns(2)
    with a.container(border=True):
        st.markdown("**Application**")
        st.markdown(kv([("Name", "DataAI Explorer"), ("Interface", "Streamlit"),
                        ("Mode", "Local, read-only queries")]), unsafe_allow_html=True)
    with b.container(border=True):
        st.markdown("**Database**")
        st.markdown(kv([("Engine", "SQLite"), ("File", DB_PATH), ("Size", size), ("Tables", len(tables))]),
                    unsafe_allow_html=True)
    c, d = st.columns(2)
    with c.container(border=True):
        st.markdown("**Local AI (Ollama)**")
        st.markdown(kv([("Status", "Running" if online else "Not reachable"), ("Address", OLLAMA_URL),
                        ("Models", ", ".join(models) if models else "none found")]), unsafe_allow_html=True)
        if st.button("Check again"):
            ollama_status.clear()
            st.rerun()
    with d.container(border=True):
        st.markdown("**Database safety**")
        st.write("Only SELECT and WITH … SELECT queries run. INSERT, UPDATE, DELETE, DROP and ALTER "
                 "are rejected by this app and by the database layer.")
    st.markdown('<div class="sec">Tables</div>', unsafe_allow_html=True)
    if tables:
        st.dataframe(pd.DataFrame({"Table": tables, "Rows": [count_rows(t) for t in tables]}),
                     use_container_width=True, hide_index=True)
    else:
        st.caption("No tables yet.")


{
    "Home": page_home,
    "Upload Data": page_upload,
    "Browse Data": page_browse,
    "Ask AI": page_ask,
    "Settings": page_settings,
}[page]()

st.markdown('<div class="foot">DataAI Explorer · Runs locally with Ollama and Llama 3 · Read-only SQL on SQLite</div>',
            unsafe_allow_html=True)
