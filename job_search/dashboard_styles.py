"""Streamlit dashboard layout styles (job cards, explorer search, pagination)."""
from __future__ import annotations

import html

# sessionStorage key for main-pane vertical scroll (browser tab scoped).
_SCROLL_STORAGE_KEY = "job_search_dashboard_scrollY"

# Single window manager object (listeners + APIs); survives Streamlit reruns.
_SCROLL_MGR_OBJ = "__jobSearchScrollMgr"

# API exposed for tests and legacy callers.
_SCROLL_TO_LIST_FN = "__jobSearchScrollToJobList"

# Anchor id on Job explorer results header (scroll target after page change).
_JOB_LIST_ANCHOR_ID = "job-explorer-list-start"

# Limitations (see inject_scroll_manager): Streamlit may still reflow after our
# restore window; pagination scroll-to-list wins over F5 restore on the same load.


def _scroll_manager_js(*, scroll_to_list: bool, force_restore: bool = False) -> str:
    """One boot script: install manager once, then restore and/or scroll-to-list."""
    if scroll_to_list:
        action = "toList"
    elif force_restore:
        action = "forceRestore"
    else:
        action = "boot"
    return f"""
<script>
(function () {{
  /* Unified scroll manager — install listeners once per browser tab; each Streamlit
     rerun emits a small boot tail (restore and/or pagination scroll). Inject at the
     *end* of main() so the Job explorer anchor exists before scroll-to-list. */
  function resolveWin() {{
    var win = window;
    try {{
      if (win.parent && win.parent !== win) {{
        void win.parent.document;
        win = win.parent;
      }}
    }} catch (e) {{}}
    return win;
  }}

  var win = resolveWin();
  if (!win) return;
  var doc = win.document;
  var KEY = "{_SCROLL_STORAGE_KEY}";
  var MGR_KEY = "{_SCROLL_MGR_OBJ}";
  var TO_LIST_FN = "{_SCROLL_TO_LIST_FN}";
  var ANCHOR_ID = "{_JOB_LIST_ANCHOR_ID}";
  var ACTION = "{action}";

  function ensureMgr() {{
    if (win[MGR_KEY]) return win[MGR_KEY];
    var mgr = {{
      userMoved: false,
      restoring: false,
      restoreScheduled: false,
      toListScheduled: false,
      saveTimer: null,
      suppressSaveUntil: 0,
      bound: [],
      obs: null
    }};

    function markUserMoved() {{
      mgr.userMoved = true;
      if (mgr.obs) {{
        try {{ mgr.obs.disconnect(); }} catch (e) {{}}
        mgr.obs = null;
      }}
    }}

    function scrollCandidates() {{
      return [
        doc.querySelector('[data-testid="stMain"]'),
        doc.querySelector('[data-testid="stMainBlockContainer"]'),
        doc.querySelector("section.main"),
        doc.querySelector(".stMain"),
        doc.querySelector('[data-testid="stAppViewContainer"]'),
        doc.scrollingElement,
        doc.documentElement,
        doc.body
      ].filter(Boolean);
    }}

    function pickScrollEl() {{
      var best = null;
      var bestDelta = -1;
      var list = scrollCandidates();
      for (var i = 0; i < list.length; i++) {{
        var el = list[i];
        var delta = (el.scrollHeight || 0) - (el.clientHeight || 0);
        if (delta > bestDelta) {{
          bestDelta = delta;
          best = el;
        }}
      }}
      return best || doc.documentElement;
    }}

    function isRootScroll(el) {{
      return (
        el === doc.documentElement ||
        el === doc.body ||
        el === doc.scrollingElement
      );
    }}

    function getY() {{
      var el = pickScrollEl();
      if (isRootScroll(el)) {{
        return win.scrollY || doc.documentElement.scrollTop || 0;
      }}
      return el.scrollTop || 0;
    }}

    function setY(y) {{
      var el = pickScrollEl();
      if (isRootScroll(el)) {{
        win.scrollTo(0, y);
      }} else {{
        el.scrollTop = y;
      }}
    }}

    function shouldPersistScroll() {{
      return !!findJobListAnchor();
    }}

    function saveY() {{
      if (Date.now() < mgr.suppressSaveUntil) return;
      if (!shouldPersistScroll()) return;
      try {{
        win.sessionStorage.setItem(KEY, String(Math.round(getY())));
      }} catch (e) {{}}
    }}

    function forceSaveY() {{
      try {{
        win.sessionStorage.setItem(KEY, String(Math.round(getY())));
      }} catch (e) {{}}
    }}

    function findJobListAnchor() {{
      return (
        doc.getElementById(ANCHOR_ID) ||
        doc.querySelector(".explorer-results-header") ||
        doc.querySelector(".job-card-list") ||
        doc.querySelector(".job-card-marker")
      );
    }}

    function scrollToJobListOnce() {{
      bindScrollTargets();
      var anchor = findJobListAnchor();
      if (!anchor) return false;
      var scroller = pickScrollEl();
      var pad = 8;
      var nextY;
      if (isRootScroll(scroller)) {{
        var rect = anchor.getBoundingClientRect();
        nextY = (win.scrollY || doc.documentElement.scrollTop || 0) + rect.top - pad;
      }} else {{
        var sRect = scroller.getBoundingClientRect();
        var aRect = anchor.getBoundingClientRect();
        nextY = (scroller.scrollTop || 0) + (aRect.top - sRect.top) - pad;
      }}
      if (nextY < 0) nextY = 0;
      mgr.userMoved = true;
      mgr.restoring = true;
      setY(nextY);
      mgr.restoring = false;
      forceSaveY();
      return true;
    }}

    mgr.scrollToJobListOnce = scrollToJobListOnce;
    win[TO_LIST_FN] = scrollToJobListOnce;

    mgr.scrollToJobListWithRetries = function () {{
      if (mgr.toListScheduled) return;
      mgr.toListScheduled = true;
      var delays = [0, 50, 150, 350, 700, 1200, 2000, 3200];
      for (var i = 0; i < delays.length; i++) {{
        (function (ms) {{
          win.setTimeout(function () {{
            scrollToJobListOnce();
          }}, ms);
        }})(delays[i]);
      }}
    }};

    function onScroll() {{
      if (mgr.restoring) return;
      if (mgr.saveTimer) win.clearTimeout(mgr.saveTimer);
      mgr.saveTimer = win.setTimeout(saveY, 120);
    }}

    function bindScrollTargets() {{
      var cands = scrollCandidates();
      for (var j = 0; j < cands.length; j++) {{
        var node = cands[j];
        if (mgr.bound.indexOf(node) !== -1) continue;
        mgr.bound.push(node);
        node.addEventListener("scroll", onScroll, {{ passive: true }});
      }}
    }}

    function savedTargetY() {{
      var saved = null;
      try {{
        saved = win.sessionStorage.getItem(KEY);
      }} catch (e) {{}}
      var targetY = saved !== null ? parseInt(saved, 10) : 0;
      return !isNaN(targetY) && targetY > 0 ? targetY : 0;
    }}

    function applyRestoreY(targetY) {{
      if (mgr.userMoved) return;
      bindScrollTargets();
      mgr.restoring = true;
      setY(targetY);
      mgr.restoring = false;
    }}

    mgr.scheduleRestore = function () {{
      if (mgr.restoreScheduled || mgr.userMoved) return;
      mgr.restoreScheduled = true;
      var targetY = savedTargetY();
      if (targetY <= 0) return;
      mgr.suppressSaveUntil = Date.now() + 4500;
      var delays = [0, 50, 150, 350, 700, 1200, 2000, 3000, 4000, 5000];
      for (var d = 0; d < delays.length; d++) {{
        (function (ms, y) {{
          win.setTimeout(function () {{
            applyRestoreY(y);
          }}, ms);
        }})(delays[d], targetY);
      }}
      var main = doc.querySelector('[data-testid="stMain"]');
      if (main && typeof MutationObserver !== "undefined") {{
        mgr.obs = new MutationObserver(function () {{
          applyRestoreY(targetY);
        }});
        mgr.obs.observe(main, {{ childList: true, subtree: true }});
        win.setTimeout(function () {{
          if (mgr.obs) {{
            try {{ mgr.obs.disconnect(); }} catch (e) {{}}
            mgr.obs = null;
          }}
        }}, 5000);
      }}
    }};

    win.addEventListener("wheel", markUserMoved, {{ passive: true }});
    win.addEventListener("touchmove", markUserMoved, {{ passive: true }});
    doc.addEventListener("keydown", function (e) {{
      var k = e.key;
      if (
        k === "PageDown" ||
        k === "PageUp" ||
        k === "Home" ||
        k === "End" ||
        k === "ArrowDown" ||
        k === "ArrowUp"
      ) {{
        markUserMoved();
      }}
    }});
    win.addEventListener("scroll", onScroll, {{ passive: true }});
    win.addEventListener("pagehide", saveY);
    win.addEventListener("beforeunload", saveY);
    win.addEventListener("pageshow", function (ev) {{
      if (ev && ev.persisted) {{
        mgr.restoreScheduled = false;
        mgr.userMoved = false;
        mgr.scheduleRestore();
      }}
    }});
    bindScrollTargets();
    win.setTimeout(bindScrollTargets, 400);
    win.setTimeout(bindScrollTargets, 1200);

    win[MGR_KEY] = mgr;
    return mgr;
  }}

  var mgr = ensureMgr();

  if (ACTION === "toList") {{
    mgr.restoreScheduled = true;
    mgr.userMoved = true;
    mgr.scrollToJobListWithRetries();
  }} else if (ACTION === "forceRestore") {{
    mgr.userMoved = false;
    mgr.restoreScheduled = false;
    mgr.toListScheduled = false;
    if (savedTargetY() > 0) {{
      mgr.scheduleRestore();
    }}
  }} else if (!mgr.restoreScheduled) {{
    mgr.scheduleRestore();
  }}
}})();
</script>
"""


# Exported for unit tests (boot action; pagination uses scroll_to_list=True).
_SCROLL_RESTORE_JS = _scroll_manager_js(scroll_to_list=False)
_SCROLL_TO_JOB_LIST_JS = _scroll_manager_js(scroll_to_list=True)
_SCROLL_FORCE_RESTORE_JS = _scroll_manager_js(scroll_to_list=False, force_restore=True)


def inject_scroll_manager(*, scroll_to_list: bool = False, force_restore: bool = False) -> None:
    """Install scroll manager and optionally scroll Job explorer to results header.

    Call once at the end of ``main()`` (``scroll_to_list`` when pagination changed).
    Pass ``force_restore`` after closing the Apply/Modify dialog so a prior minimal
    fast-path rerun does not block ``scheduleRestore`` on the full page.
    Limitations: very late Streamlit layout shifts can still move scroll slightly;
    intentional pagination scroll aborts F5 restore on the same page load.
    """
    import streamlit as st

    snippet = _scroll_manager_js(scroll_to_list=scroll_to_list, force_restore=force_restore)
    st.html(snippet, unsafe_allow_javascript=True)


def inject_scroll_restoration() -> None:
    """Backward-compatible alias — prefer ``inject_scroll_manager`` at end of main()."""
    inject_scroll_manager(scroll_to_list=False)


def inject_scroll_to_job_list() -> None:
    """Backward-compatible alias — prefer ``inject_scroll_manager(scroll_to_list=True)``."""
    inject_scroll_manager(scroll_to_list=True)


METRIC_CSS = """
div[data-testid="stMetric"] { padding: 0.2rem 0; }
div[data-testid="stMetricLabel"] { font-size: 0.8rem; }
div[data-testid="stMetricValue"] { font-size: 1.35rem; }
div[data-testid="stExpander"] details {
    border: 1px solid rgba(49, 51, 63, 0.12);
    border-radius: 0.35rem;
    margin-bottom: 0.35rem;
}
div.pipeline-panel {
    margin: 0.35rem 0 0.75rem 0;
    padding: 0.25rem 0;
}
div.pipeline-panel div[data-testid="stStatusWidget"] {
    width: 100%;
}
.pipeline-status-shell {
    margin: 0.35rem 0 0.9rem 0;
}
.pipeline-status-shell > div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 0.65rem;
}
.pipeline-status-meta {
    font-size: 0.82rem;
    color: rgba(49, 51, 63, 0.74);
}
.pipeline-status-job {
    font-weight: 600;
}
.pipeline-status-spacer {
    height: 0.15rem;
}
"""

JOB_CARD_CSS = """
div[data-testid="stVerticalBlockBorderWrapper"]:has(.job-card-marker) {
    margin-bottom: 0.65rem;
    transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.job-card-marker):hover {
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.07);
    border-color: rgba(0, 103, 197, 0.35) !important;
}
.job-card-marker { display: none; }
.job-card-header { margin-bottom: 0.2rem; }
.job-card-title {
    font-size: 1.05rem;
    font-weight: 600;
    line-height: 1.35;
    color: #0067c5;
    text-decoration: none;
}
.job-card-title:hover { text-decoration: underline; }
.job-card-title-plain { color: inherit; }
.job-card-meta {
    font-size: 0.875rem;
    color: rgba(49, 51, 63, 0.72);
    line-height: 1.45;
}
.job-card-deadline-urgent {
    color: #c0392b;
    font-weight: 500;
}
.job-card-urgency {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 600;
    color: #c0392b;
    margin-right: 0.35rem;
}
.job-score-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2.25rem;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 600;
    line-height: 1.2;
}
.job-score-high {
    background: rgba(46, 125, 50, 0.12);
    color: #2e7d32;
}
.job-score-mid {
    background: rgba(230, 126, 34, 0.14);
    color: #c0651a;
}
.job-score-low {
    background: rgba(49, 51, 63, 0.08);
    color: rgba(49, 51, 63, 0.75);
}
.job-score-none {
    background: rgba(49, 51, 63, 0.06);
    color: rgba(49, 51, 63, 0.5);
}
.job-status-badge {
    display: inline-block;
    margin-top: 0.35rem;
    padding: 0.12rem 0.5rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: lowercase;
    letter-spacing: 0.01em;
}
.job-status-interested { background: rgba(33, 150, 243, 0.14); color: #1565c0; }
.job-status-drafted { background: rgba(255, 152, 0, 0.16); color: #e65100; }
.job-status-applied { background: rgba(76, 175, 80, 0.14); color: #2e7d32; }
.job-status-interview { background: rgba(156, 39, 176, 0.12); color: #7b1fa2; }
.job-status-offer { background: rgba(76, 175, 80, 0.18); color: #1b5e20; }
.job-status-rejected { background: rgba(244, 67, 54, 0.12); color: #c62828; }
.job-status-withdrawn { background: rgba(158, 158, 158, 0.16); color: #616161; }
.job-status-unknown { background: rgba(158, 158, 158, 0.12); color: #757575; }
.job-card-actions {
    margin-top: 0.55rem;
}
div.job-card-list > div[data-testid="stVerticalBlock"] {
    gap: 0.15rem;
}
.pagination-bar {
    margin: 0.35rem 0 0.85rem 0;
    padding: 0.35rem 0;
}
.pagination-info {
    margin: 0;
    font-size: 0.9rem;
    color: rgba(49, 51, 63, 0.82);
}
.pagination-page {
    margin: 0;
    font-size: 0.85rem;
    color: rgba(49, 51, 63, 0.65);
    text-align: center;
    line-height: 2.2;
}
"""

EXPLORER_CSS = """
.explorer-search-shell {
    margin: 0.15rem 0 0.75rem 0;
}
.explorer-search-shell + div [data-testid="stTextInput"] input {
    font-size: 1.05rem;
    padding: 0.65rem 0.85rem;
    border-radius: 0.45rem;
    border: 1px solid rgba(49, 51, 63, 0.25);
}
.explorer-search-shell + div [data-testid="stTextInput"] input:focus {
    border-color: #0063fb;
    box-shadow: 0 0 0 1px #0063fb;
}
.dash-filter-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin: 0.35rem 0 0.65rem 0;
}
.dash-filter-chip {
    display: inline-block;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    background: rgba(0, 99, 251, 0.08);
    border: 1px solid rgba(0, 99, 251, 0.22);
    color: rgb(49, 51, 63);
    font-size: 0.78rem;
    line-height: 1.35;
    white-space: nowrap;
}
.explorer-results-header {
    margin: 0.15rem 0 0.85rem 0;
    padding: 0.55rem 0.75rem;
    border-radius: 0.4rem;
    background: rgba(49, 51, 63, 0.04);
    border: 1px solid rgba(49, 51, 63, 0.1);
}
.explorer-results-header .treff-count {
    font-size: 1.15rem;
    font-weight: 600;
    color: rgb(38, 39, 48);
}
.explorer-results-header .treff-meta {
    font-size: 0.82rem;
    color: rgba(49, 51, 63, 0.72);
    margin-top: 0.15rem;
}
.explorer-secondary-filters {
    margin-bottom: 0.5rem;
    padding: 0.35rem 0.55rem;
    border-radius: 0.35rem;
    border: 1px solid rgba(49, 51, 63, 0.08);
    background: rgba(255, 255, 255, 0.6);
}
"""


def dashboard_css() -> str:
    """Combined dashboard CSS (metrics, job cards, explorer)."""
    return f"<style>{METRIC_CSS}\n{JOB_CARD_CSS}\n{EXPLORER_CSS}</style>"


def render_filter_chips(chips: list[str]) -> None:
    """Render active filter summary chips (read-only)."""
    import streamlit as st

    if not chips:
        return
    inner = "".join(
        f'<span class="dash-filter-chip">{html.escape(label)}</span>' for label in chips
    )
    st.markdown(f'<div class="dash-filter-chips">{inner}</div>', unsafe_allow_html=True)


def format_treff_count(n: int, *, query: str = "") -> str:
    """Norwegian-style results label (Arbeidsplassen-like)."""
    q = (query or "").strip()
    if q:
        short = q if len(q) <= 48 else f"{q[:48]}…"
        return f"{n} treff for «{short}»"
    return f"{n} treff"


def render_results_header(
    *,
    n_results: int,
    text_query: str = "",
    soon_n: int = 0,
    urgency_days: int = 7,
    dedup_note: str = "",
) -> None:
    import streamlit as st

    treff = html.escape(format_treff_count(n_results, query=text_query))
    meta_parts: list[str] = []
    if soon_n:
        meta_parts.append(f"{soon_n} med frist innen {urgency_days} dager")
    if dedup_note:
        meta_parts.append(dedup_note.strip(" ()"))
    meta_html = ""
    if meta_parts:
        meta_html = f'<div class="treff-meta">{" · ".join(html.escape(p) for p in meta_parts)}</div>'
    st.markdown(
        f'<div id="{_JOB_LIST_ANCHOR_ID}" class="explorer-results-header">'
        f'<div class="treff-count">{treff}</div>{meta_html}</div>',
        unsafe_allow_html=True,
    )
