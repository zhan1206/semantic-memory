#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic Memory — Streamlit Web UI
Interactive web interface, no command line needed to manage memories and knowledge bases.

Start: streamlit run scripts/streamlit_app.py
"""
from __future__ import annotations

import os
import sys

# Ensure scripts/ is on the path
_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_SKILL_DIR, "scripts"))

import streamlit as st
import pandas as pd
from datetime import datetime


# ─── Lazy manager import ───────────────────────────────────
def _get_manager():
    if "mgr" not in st.session_state:
        with st.spinner("Initializing semantic memory engine..."):
            from memory_manager import MemoryManager
            st.session_state["mgr"] = MemoryManager()
    return st.session_state["mgr"]


# ─── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title="Semantic Memory",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─── Sidebar ────────────────────────────────────────────────
st.sidebar.title("🧠 Semantic Memory")
st.sidebar.caption("Local semantic memory and retrieval system")

st.sidebar.divider()

PAGES = [
    "🔍 Semantic Search",
    "💾 Add Memory",
    "📋 Memory List",
    "📊 Statistics",
    "📚 Knowledge Base",
    "⚙️ Configuration",
    "🏗️ Batch Operations",
]

page = st.sidebar.radio("Navigate", PAGES, index=0)

st.sidebar.divider()

with st.sidebar.expander("ℹ️ System Info"):
    try:
        mgr = _get_manager()
        stats = mgr.stats()
        st.caption(f"Model: {stats.get('model', 'N/A')}")
        st.caption(f"Dimension: {stats.get('dimension', 'N/A')}")
        st.caption(f"Total memories: {stats.get('total_memories', 0)}")
    except Exception as e:
        st.caption(f"Not connected: {e}")

st.sidebar.caption("Powered by ONNX + FAISS")

# ─── Helpers ────────────────────────────────────────────────
def _fmt_ts(ts: float) -> str:
    if not ts:
        return "N/A"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def _progress_color(score: float) -> str:
    if score > 0.8:
        return "green"
    if score > 0.6:
        return "orange"
    return "red"


# ─── Page: Semantic Search ──────────────────────────────────
if page == "🔍 Semantic Search":
    st.title("🔍 Semantic Search")
    st.markdown("Enter natural language and instantly search all memories.")

    col_q, col_k = st.columns([3, 1])
    with col_q:
        query = st.text_input(
            "Search query",
            placeholder="e.g. What did Zhang San discuss? Project progress?",
            label_visibility="collapsed",
            key="sq_query",
        )
    with col_k:
        top_k = st.slider("Results", 1, 20, 5, key="sq_topk")

    tag_filter = st.text_input(
        "Tag filter (optional)", placeholder="Leave empty for all tags", key="sq_tag"
    )
    mode = st.radio("Scope", ["All memories", "Knowledge base"], horizontal=True, key="sq_mode")

    kb_filter = None
    if mode == "Knowledge base":
        try:
            kb_list = _get_manager().list_kbs()
            kb_names = [kb.get("name", "") for kb in kb_list]
            if kb_names:
                kb_filter = st.selectbox("Knowledge base", kb_names, key="sq_kb")
            else:
                st.warning("No knowledge bases yet. Create one first in the Knowledge Base page.")
        except Exception as e:
            st.error(f"Failed to load knowledge bases: {e}")

    if st.button("🚀 Search", type="primary", use_container_width=True):
        if not query:
            st.warning("Please enter a query")
        else:
            with st.spinner("Searching memories..."):
                try:
                    mgr = _get_manager()
                    results = mgr.search(
                        query,
                        top_k=top_k,
                        tag=tag_filter if tag_filter else None,
                        kb_name=kb_filter,
                    )
                    if not results:
                        st.info("No relevant memories found. Try different terms.")
                    else:
                        st.success(f"Found {len(results)} relevant memories")
                        for i, r in enumerate(results):
                            score = r.get("score", 0)
                            with st.container():
                                c1, c2 = st.columns([1, 4])
                                with c1:
                                    st.metric("Similarity", f"{score:.2%}")
                                    st.progress(score)
                                with c2:
                                    st.markdown("**📝 Content**")
                                    st.text_area(
                                        "",
                                        value=r.get("text", ""),
                                        height=100,
                                        disabled=True,
                                        label_visibility="collapsed",
                                        key=f"rt_{i}",
                                    )
                                    tags = r.get("tags", [])
                                    t_col, i_col, ts_col = st.columns(3)
                                    with t_col:
                                        if tags:
                                            st.markdown("Tags: " + " ".join(tags))
                                    with i_col:
                                        st.caption(f"Importance: {r.get('importance', 0):.1f}")
                                    with ts_col:
                                        st.caption(f"Time: {_fmt_ts(r.get('timestamp', 0))}")
                                    mid = r.get("id", "")
                                    b1, b2 = st.columns(2)
                                    with b1:
                                        if st.button(f"Edit", key=f"edit_{mid}"):
                                            st.session_state["edit_id"] = mid
                                            st.rerun()
                                    with b2:
                                        if st.button(f"Delete", key=f"del_{mid}"):
                                            try:
                                                mgr.delete(mid)
                                                st.success(f"Deleted {mid}")
                                                st.rerun()
                                            except Exception as ex:
                                                st.error(f"Delete failed: {ex}")
                                st.divider()
                except Exception as e:
                    st.error(f"Search failed: {e}")

    # Context recall
    st.divider()
    st.subheader("📄 Recall Context (for AI)")
    col_rq, col_rm = st.columns([3, 1])
    with col_rq:
        recall_q = st.text_input(
            "Generate AI-ready context",
            placeholder="Search and format results as AI context",
            key="recall_q",
        )
    with col_rm:
        recall_max = st.number_input("Max chars", 500, 50000, 3000, 500, key="recall_max")

    if st.button("📦 Generate Context", use_container_width=True):
        if recall_q:
            with st.spinner("Generating context..."):
                try:
                    mgr = _get_manager()
                    results = mgr.search(recall_q, top_k=top_k,
                                         tag=tag_filter if tag_filter else None)
                    parts = []
                    total = 0
                    for r in results:
                        text = r.get("text", "")
                        if total + len(text) + 1 > recall_max:
                            break
                        parts.append(f"[Memory {r['id']}] {text}")
                        total += len(text) + 1
                    ctx = "\n\n".join(parts)
                    st.session_state["ctx_out"] = ctx
                except Exception as e:
                    st.error(f"Generation failed: {e}")

    if "ctx_out" in st.session_state and st.session_state["ctx_out"]:
        st.text_area(
            "AI Context (paste directly to LLM)",
            value=st.session_state["ctx_out"],
            height=200,
            disabled=True,
            key="ctx_disp",
        )
        st.caption(f"{len(st.session_state['ctx_out'])} characters")


# ─── Page: Add Memory ───────────────────────────────────────
elif page == "💾 Add Memory":
    st.title("💾 Add Memory")

    tab_single, tab_batch = st.tabs(["📝 Single", "📦 Batch Import"])

    with tab_single:
        with st.form("add_single", clear_on_submit=True):
            text = st.text_area("Memory content", placeholder="Enter what to remember...", height=150)
            col_t, col_i = st.columns(2)
            with col_t:
                tags_in = st.text_input("Tags (comma-separated)", placeholder="work, important, ai")
            with col_i:
                importance = st.slider("Importance", 0.0, 1.0, 0.5, 0.1)
            col_src, col_skip = st.columns(2)
            with col_src:
                source = st.selectbox(
                    "Source",
                    ["manual", "conversation", "api", "batch", "kb_import"],
                    index=0,
                )
            with col_skip:
                skip_filter = st.toggle("Skip sensitive filter", value=False)
            submitted = st.form_submit_button(
                "💾 Add Memory", type="primary", use_container_width=True
            )
            if submitted:
                if not text.strip():
                    st.warning("Memory content cannot be empty")
                else:
                    try:
                        mgr = _get_manager()
                        tags = [t.strip() for t in tags_in.split(",") if t.strip()]
                        result = mgr.add(text, tags=tags, importance=importance,
                                         source=source, skip_filter=skip_filter)
                        if result.startswith("filtered:"):
                            reason = result.split(":", 1)[1]
                            st.error(f"Blocked by sensitive filter: {reason}")
                        elif result.startswith("dedup:"):
                            dup = result.split(":", 1)[1]
                            st.warning(f"Duplicate detected (ID: {dup}), importance boosted")
                        else:
                            st.success(f"✅ Memory added! ID: `{result}`")
                            st.balloons()
                    except Exception as e:
                        st.error(f"Add failed: {e}")

    with tab_batch:
        st.markdown("**Batch import files** (supports .txt / .md / .pdf / .docx / .xlsx / .pptx)")
        uploaded = st.file_uploader(
            "Select file",
            type=["txt", "md", "pdf", "docx", "xlsx", "pptx"],
            accept_multiple_files=False,
            help="Each line (.txt/.md) or page (PDF/DOCX) will be added as a separate memory",
        )
        # Build KB options safely
        kb_opts = ["-- Do not import to KB --"]
        try:
            kb_opts += [kb.get("name", "") for kb in _get_manager().list_kbs()]
        except Exception:
            pass
        kb_target = st.selectbox("Import to KB (optional)", kb_opts, index=0)
        batch_tags = st.text_input("Batch tags (optional)", placeholder="Auto-tag these labels")

        if uploaded is not None:
            import tempfile
            import uuid
            tmpdir = tempfile.mkdtemp()
            filepath = os.path.join(tmpdir, uploaded.name)
            with open(filepath, "wb") as f:
                f.write(uploaded.getbuffer())
            try:
                from doc_parser import parse_file
                text = parse_file(filepath)
                st.success(f"File parsed: {len(text)} characters")
                if st.button("📥 Start Import", type="primary"):
                    with st.spinner("Importing..."):
                        mgr = _get_manager()
                        tags = [t.strip() for t in batch_tags.split(",") if t.strip()]
                        if kb_target != "-- Do not import to KB --":
                            from doc_parser import import_file_to_kb
                            result = mgr.add_to_kb(
                                kb_name=kb_target,
                                text=text,
                                source_file=uploaded.name,
                                tags=tags,
                            )
                            st.success(f"✅ Imported to KB '{kb_target}': {result}")
                        else:
                            chunks = mgr._chunk_text(text)
                            added = 0
                            for chunk in chunks:
                                r = mgr.add(chunk, tags=tags, source="batch_file")
                                if not r.startswith(("filtered:", "dedup:")):
                                    added += 1
                            st.success(f"✅ Added {added} memories")
            except Exception as e:
                st.error(f"Parse/import failed: {e}")
            finally:
                import shutil
                shutil.rmtree(tmpdir, ignore_errors=True)


# ─── Page: Memory List ──────────────────────────────────────
elif page == "📋 Memory List":
    st.title("📋 Memory List")
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        ftag = st.text_input("Tag filter", placeholder="Leave empty for all", key="ml_tag")
    with col_f2:
        flimit = st.slider("Per page", 10, 100, 50, key="ml_limit")
    sort_opt = st.radio(
        "Sort by",
        ["Newest first", "Oldest first", "By importance"],
        horizontal=True,
        key="ml_sort",
    )
    sort_map = {"Newest first": ("timestamp", True), "Oldest first": ("timestamp", False),
                 "By importance": ("importance", False)}
    try:
        mgr = _get_manager()
        items = mgr.list_memories(
            tag=ftag if ftag else None,
            limit=flimit,
            sort_by=sort_map[sort_opt][0],
        )
        if sort_map[sort_opt][0] == "timestamp":
            items = items[::-1] if sort_map[sort_opt][1] else items
        st.info(f"{len(items)} memories")
        for item in items:
            with st.container():
                c_txt, c_ops = st.columns([4, 1])
                with c_txt:
                    st.text_area(
                        "",
                        value=item.get("text", ""),
                        height=80,
                        disabled=True,
                        label_visibility="collapsed",
                    )
                    t, i, ts = st.columns(3)
                    with t:
                        tags = item.get("tags", [])
                        if tags:
                            st.markdown("Tags: " + " ".join(tags))
                    with i:
                        st.caption(f"Importance: {item.get('importance', 0):.1f}")
                    with ts:
                        st.caption(f"Time: {item.get('created_at', '')[:16]}")
                with c_ops:
                    mid = item.get("id", "")
                    if st.button("🗑️", key=f"del_ml_{mid}", help="Delete"):
                        try:
                            mgr.delete(mid)
                            st.success("Deleted")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Delete failed: {e}")
                st.divider()
    except Exception as e:
        st.error(f"Load failed: {e}")


# ─── Page: Statistics ───────────────────────────────────────
elif page == "📊 Statistics":
    st.title("📊 Statistics")
    try:
        mgr = _get_manager()
        stats = mgr.stats()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Memories", stats.get("total_memories", 0))
        c2.metric("Dimension", stats.get("dimension", "N/A"))
        c3.metric("Index Type", stats.get("index_type", "N/A"))
        c4.metric("Low-value Memories", stats.get("low_value_count", 0))
        st.divider()
        ct, cs = st.columns(2)
        with ct:
            st.subheader("🏷️ Tag Distribution")
            by_tag = stats.get("by_tag", {})
            if by_tag:
                df_tag = pd.DataFrame(
                    [{"Tag": k, "Count": v} for k, v in
                     sorted(by_tag.items(), key=lambda x: -x[1])]
                )
                st.bar_chart(df_tag.set_index("Tag"))
                st.dataframe(df_tag, use_container_width=True, hide_index=True)
            else:
                st.info("No tag data yet")
        with cs:
            st.subheader("📌 Source Distribution")
            by_src = stats.get("by_source", {})
            if by_src:
                df_src = pd.DataFrame(
                    [{"Source": k, "Count": v} for k, v in
                     sorted(by_src.items(), key=lambda x: -x[1])]
                )
                st.bar_chart(df_src.set_index("Source"))
                st.dataframe(df_src, use_container_width=True, hide_index=True)
            else:
                st.info("No source data yet")
        if "metrics" in stats:
            st.divider()
            st.subheader("⚡ Performance Metrics")
            m = stats["metrics"]
            cp = st.columns(4)
            cp[0].metric("Add calls", m.get("add_count", 0))
            cp[1].metric("Add avg", f"{m.get('add_avg_ms', 0):.1f}ms")
            cp[2].metric("Search calls", m.get("search_count", 0))
            cp[3].metric("Search avg", f"{m.get('search_avg_ms', 0):.1f}ms")
        st.divider()
        st.subheader("🧹 Auto-forget Preview")
        forgotten = mgr.auto_forget(dry_run=True)
        if forgotten:
            st.warning(f"{len(forgotten)} low-value memories will be cleaned (preview)")
            st.dataframe(pd.DataFrame(forgotten), use_container_width=True, hide_index=True)
            if st.button("🗑️ Confirm Cleanup", type="primary"):
                mgr.auto_forget(dry_run=False)
                st.success("Cleaned up")
                st.rerun()
        else:
            st.success("All memories are valuable, nothing to forget")
    except Exception as e:
        st.error(f"Load failed: {e}")


# ─── Page: Knowledge Base ────────────────────────────────────
elif page == "📚 Knowledge Base":
    st.title("📚 Knowledge Base Management")
    tab_list, tab_create, tab_query = st.tabs(["📂 Browse", "➕ Create", "🔍 Query"])

    with tab_list:
        st.subheader("Existing Knowledge Bases")
        try:
            kbs = _get_manager().list_kbs()
            if not kbs:
                st.info("No knowledge bases yet")
            else:
                for kb in kbs:
                    with st.expander(f"📚 {kb.get('name', 'N/A')}"):
                        st.caption(f"Description: {kb.get('description', 'None')}")
                        st.caption(f"Documents: {kb.get('document_count', 0)}")
                        st.caption(f"Created: {kb.get('created_at', '')[:19]}")
                        if st.button(f"🗑️ Delete '{kb.get('name')}'", key=f"del_kb_{kb.get('name')}"):
                            try:
                                _get_manager().delete_kb(kb.get("name"))
                                st.success("Deleted")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Delete failed: {e}")
        except Exception as e:
            st.error(f"Load failed: {e}")

    with tab_create:
        kb_name = st.text_input("KB Name", placeholder="e.g. My Documents")
        kb_desc = st.text_input("Description (optional)", placeholder="Short description")
        if st.button("➕ Create KB", type="primary", use_container_width=True):
            if not kb_name.strip():
                st.warning("Please enter a KB name")
            else:
                try:
                    result = _get_manager().create_kb(kb_name.strip(), kb_desc)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.success(f"✅ KB '{kb_name}' created")
                        st.rerun()
                except Exception as e:
                    st.error(f"Create failed: {e}")

    with tab_query:
        try:
            kbs = _get_manager().list_kbs()
            if not kbs:
                st.info("Create a KB first")
            else:
                kb_names = [kb.get("name", "") for kb in kbs]
                sel_kb = st.selectbox("Select KB", kb_names, key="q_kb")
                q_text = st.text_input("Query", placeholder="Search in KB...")
                q_topk = st.slider("Results", 1, 20, 5, key="q_topk")
                if st.button("🔍 Search KB", type="primary", use_container_width=True):
                    if not q_text:
                        st.warning("Enter a query")
                    else:
                        with st.spinner("Searching..."):
                            try:
                                results = _get_manager().query_kb(sel_kb, q_text, top_k=q_topk)
                                st.success(f"{len(results)} results")
                                for r in results:
                                    st.text_area(
                                        "", value=r.get("text", ""),
                                        height=80, disabled=True, label_visibility="collapsed"
                                    )
                                    st.caption(
                                        f"Score: {r.get('score', 0):.4f} | "
                                        f"Tags: {', '.join(r.get('tags', []))}"
                                    )
                                    st.divider()
                            except Exception as e:
                                st.error(f"Query failed: {e}")
        except Exception as e:
            st.error(f"Load failed: {e}")


# ─── Page: Configuration ────────────────────────────────────
elif page == "⚙️ Configuration":
    st.title("⚙️ Configuration")
    try:
        from config import load_config, get_config, set_config
        st.subheader("Current Configuration")
        cfg = load_config()
        important_keys = [
            "model_id", "search_top_k", "search_min_score",
            "half_life_days", "min_importance",
            "dedup_threshold", "dedup_enabled",
            "sensitive_filter_enabled", "metrics_enabled",
            "chunk_max_chars", "chunk_overlap",
        ]
        c_left, c_right = st.columns(2)
        for idx, key in enumerate(important_keys):
            val = get_config(key)
            col = c_left if idx % 2 == 0 else c_right
            with col:
                if isinstance(val, bool):
                    st.toggle(key, value=val, key=f"cfg_{key}")
                elif isinstance(val, (int, float)):
                    st.number_input(key, value=float(val), key=f"cfg_{key}", format="%.4f")
                else:
                    st.text_input(key, value=str(val), key=f"cfg_{key}")
        st.divider()
        if st.button("💾 Save Configuration", type="primary", use_container_width=True):
            for key in important_keys:
                wk = f"cfg_{key}"
                if wk in st.session_state:
                    new_val = st.session_state[wk]
                    cur = get_config(key)
                    if isinstance(cur, bool):
                        new_val = bool(new_val)
                    elif isinstance(cur, (int, float)):
                        new_val = float(new_val)
                    try:
                        set_config(key, new_val)
                    except Exception:
                        pass
            st.success("✅ Configuration saved")
            st.rerun()
        with st.expander("📋 Full Config (JSON)"):
            st.json(cfg)
    except Exception as e:
        st.error(f"Load failed: {e}")


# ─── Page: Batch Operations ─────────────────────────────────
elif page == "🏗️ Batch Operations":
    st.title("🏗️ Batch Operations")
    tab_del, tab_tag, tab_exp = st.tabs(["🗑️ Batch Delete", "🏷️ Batch Tag", "📤 Export"])

    with tab_del:
        st.subheader("Batch Delete by Tag")
        del_tag = st.text_input("Tag name", placeholder="Delete all memories with this tag")
        st.warning("⚠️ This operation is irreversible!")
        dry_run = st.checkbox("Preview mode (no actual delete)", value=True)
        if st.button("🗑️ Execute Delete", type="primary"):
            if del_tag:
                try:
                    mgr = _get_manager()
                    items = mgr.list_memories(tag=del_tag, limit=10000)
                    st.info(f"Will delete {len(items)} memories")
                    if not dry_run:
                        for item in items:
                            mgr.delete(item["id"])
                        st.success(f"Deleted {len(items)} memories")
                        st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")

    with tab_tag:
        st.subheader("Batch Add Tags")
        ids_in = st.text_area(
            "Memory IDs (one per line)",
            placeholder="abc123\ndef456\nghi789",
        )
        new_tags = st.text_input("New tags (comma-separated)", placeholder="important, work")
        if st.button("🏷️ Add Tags", type="primary"):
            if ids_in and new_tags:
                try:
                    mgr = _get_manager()
                    ids = [i.strip() for i in ids_in.split("\n") if i.strip()]
                    tags = [t.strip() for t in new_tags.split(",") if t.strip()]
                    ok = 0
                    for mid in ids:
                        if mgr.tag(mid, tags):
                            ok += 1
                    st.success(f"Tagged {ok}/{len(ids)} memories")
                except Exception as e:
                    st.error(f"Operation failed: {e}")

    with tab_exp:
        st.subheader("Export Memories")
        exp_ids = st.text_area(
            "Memory IDs (one per line)",
            placeholder="abc123\ndef456",
        )
        exp_file = st.text_input("Export filename", value="memories_export.json")
        if st.button("📤 Export", type="primary"):
            if exp_ids:
                try:
                    import json
                    mgr = _get_manager()
                    ids = [i.strip() for i in exp_ids.split("\n") if i.strip()]
                    exported = [item for mid in ids if (item := mgr.get(mid))]
                    json_str = json.dumps(exported, ensure_ascii=False, indent=2)
                    st.download_button(
                        "📥 Download JSON",
                        data=json_str,
                        file_name=exp_file,
                        mime="application/json",
                        use_container_width=True,
                    )
                    st.success(f"Prepared {len(exported)} memories")
                except Exception as e:
                    st.error(f"Export failed: {e}")

# ─── Footer ─────────────────────────────────────────────────
st.divider()
st.caption(
    "🧠 Semantic Memory | ONNX + FAISS local semantic memory | "
    "https://github.com/zhan1206/semantic-memory"
)
