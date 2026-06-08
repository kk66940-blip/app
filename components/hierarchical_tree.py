"""
components/hierarchical_tree.py
Reusable hierarchical tree component for RAB, RAP, Opname, etc.
Professional, consistent, and DRY (Don't Repeat Yourself).
"""

import streamlit as st
from collections import defaultdict
from typing import List, Dict, Any, Callable, Optional


def build_tree(items: List[Dict]) -> Dict[Optional[int], List[Dict]]:
    """Build parent_id → children mapping with sorting."""
    children_map: Dict[Optional[int], List[Dict]] = defaultdict(list)
    for item in items:
        children_map[item.get('parent_id')].append(item)
    
    for pid in children_map:
        children_map[pid] = sorted(
            children_map[pid], 
            key=lambda x: (x.get('sort_order', 0), x.get('id', 0))
        )
    return children_map


def display_hierarchical_tree(
    items: List[Dict],
    get_title: Optional[Callable[[Dict, int], str]] = None,
    render_content: Optional[Callable[[Dict], None]] = None,
    expanded_by_default: bool = False,
    search_term: str = "",
    key_prefix: str = "tree"
) -> None:
    """
    Display a professional hierarchical tree using Streamlit expanders.

    Args:
        items: List of dicts with 'id', 'parent_id', 'level', 'sort_order', etc.
        get_title: Function(item, level) -> title string. If None, uses default.
        render_content: Function(item) -> None. Renders inside the expander.
        expanded_by_default: Whether expanders are open by default.
        search_term: If provided, highlights matching items.
        key_prefix: Unique prefix for Streamlit keys (important for multiple trees).
    """
    if not items:
        st.info("Tidak ada data untuk ditampilkan.")
        return

    children_map = build_tree(items)

    def _default_get_title(item: Dict, level: int) -> str:
        indent = "　" * level * 2
        prefix = "▶ " if level == 0 else "└─ "
        code = item.get('code', '')
        desc = item.get('description', '')
        title = f"{code} - {desc}" if code else desc
        return f"{indent}{prefix}{title}"

    title_func = get_title or _default_get_title

    def _render_node(parent_id: Optional[int] = None, level: int = 0):
        children = children_map.get(parent_id, [])
        for item in children:
            item_id = item['id']
            title = title_func(item, level)

            # Highlight if search matches
            is_match = False
            if search_term:
                search_lower = search_term.lower().strip()
                if (search_lower in str(item.get('code', '')).lower() or 
                    search_lower in str(item.get('description', '')).lower()):
                    is_match = True
                    title = f"✅ {title}"

            with st.expander(title, expanded=expanded_by_default or bool(search_term)):
                if render_content:
                    render_content(item)
                else:
                    # Default simple content
                    st.write(f"**ID:** {item_id}")
                    st.write(f"**Level:** {item.get('level', 0)}")
                    if item.get('volume'):
                        st.write(f"**Volume:** {item['volume']} {item.get('unit', '')}")

                # Recursive children
                _render_node(item_id, level + 1)

    _render_node()


# ==================== CONVENIENCE WRAPPERS ====================

def display_rab_tree(
    items: List[Dict],
    on_edit: Optional[Callable[[Dict], None]] = None,
    on_delete: Optional[Callable[[Dict], None]] = None,
    search_term: str = "",
    key_prefix: str = "rab"
) -> None:
    """Specialized tree for RAB pages with edit/delete actions."""
    
    def render_rab_content(item: Dict):
        from utils.helpers import format_rupiah
        
        vol = item.get('volume') or 0
        price = item.get('unit_price') or 0
        total = vol * price

        col1, col2, col3 = st.columns(3)
        col1.metric("Volume", f"{vol:,.2f} {item.get('unit', '')}")
        col2.metric("Harga Satuan", format_rupiah(price))
        col3.metric("Total", format_rupiah(total))

        col_edit, col_del = st.columns(2)
        with col_edit:
            if st.button("✏️ Edit", key=f"{key_prefix}_edit_{item['id']}", use_container_width=True):
                if on_edit:
                    on_edit(item)
                else:
                    st.session_state[f"{key_prefix}_edit_item"] = item
                    st.rerun()
        with col_del:
            if st.button("🗑️ Hapus", key=f"{key_prefix}_del_{item['id']}", use_container_width=True):
                if on_delete:
                    on_delete(item)
                else:
                    st.session_state[f"{key_prefix}_delete_item"] = item
                    st.rerun()

    display_hierarchical_tree(
        items=items,
        render_content=render_rab_content,
        search_term=search_term,
        key_prefix=key_prefix
    )


def display_rap_tree(
    items: List[Dict],
    on_edit: Optional[Callable[[Dict], None]] = None,
    on_delete: Optional[Callable[[Dict], None]] = None,
    search_term: str = "",
    key_prefix: str = "rap",
    expanded_by_default: bool = False,
) -> None:
    """
    Specialized tree untuk RAP (lebih baik & konsisten).
    """
    from utils.helpers import format_rupiah

    def render_rap_content(item: Dict):
        vol = item.get("volume") or 0
        unit = item.get("unit", "")
        planned = item.get("planned_price") or 0
        exec_price = item.get("execution_price") or 0
        upah = item.get("upah") or 0

        total_rencana = vol * planned
        total_pelaksanaan = vol * exec_price
        total_upah = vol * upah

        col1, col2, col3 = st.columns(3)
        col1.metric("Volume", f"{vol:,.2f} {unit}")
        col2.metric("Harga Rencana", format_rupiah(planned))
        col3.metric("Harga Pelaksanaan", format_rupiah(exec_price))

        st.caption(
            f"**Total Rencana:** {format_rupiah(total_rencana)} | "
            f"**Total Pelaksanaan:** {format_rupiah(total_pelaksanaan)} | "
            f"**Total + Upah:** {format_rupiah(total_upah)}"
        )

        col_edit, col_del = st.columns(2)
        with col_edit:
            if st.button("✏️ Edit Harga", key=f"{key_prefix}_edit_{item['id']}", use_container_width=True):
                if on_edit:
                    on_edit(item)
                else:
                    st.session_state[f"{key_prefix}_edit_item"] = item
                    st.rerun()

        with col_del:
            if st.button("🗑️ Hapus", key=f"{key_prefix}_del_{item['id']}", use_container_width=True):
                if on_delete:
                    on_delete(item)
                else:
                    st.session_state[f"{key_prefix}_delete_item"] = item
                    st.rerun()

    display_hierarchical_tree(
        items=items,
        render_content=render_rap_content,
        search_term=search_term,
        key_prefix=key_prefix,
        expanded_by_default=expanded_by_default,
    )


# ============================================================
# OPNAME TREE (Flexible - supports both Opname & Opname Sub)
# ============================================================

def display_opname_tree(
    items: List[Dict],
    actual_map: Dict[int, float],
    rap_price_map: Optional[Dict[int, float]] = None,
    on_save: Optional[Callable[[Dict, float, Any], None]] = None,
    show_photo_upload: bool = True,
    search_term: str = "",
    key_prefix: str = "opname"
) -> None:
    """
    Reusable hierarchical tree for Opname pages.
    
    Args:
        items: RAB items
        actual_map: {rab_item_id: actual_volume}
        rap_price_map: Optional {rab_item_id: execution_price} for Opname Sub
        on_save: Callback(item, new_actual_volume, uploaded_file_or_None)
        show_photo_upload: Show photo upload section
        search_term: For live search highlighting
        key_prefix: Unique key prefix
    """
    from utils.helpers import format_rupiah
    import uuid

    def render_opname_content(item: Dict):
        rab_id = item['id']
        actual_vol = actual_map.get(rab_id, 0)
        vol = item.get('volume') or 0

        # Determine price (RAB or RAP)
        if rap_price_map:
            price = rap_price_map.get(rab_id, 0)
            price_label = "Harga RAP"
        else:
            price = item.get('unit_price') or 0
            price_label = "Harga Satuan"

        total_rencana = vol * price
        total_realisasi = actual_vol * price
        persen = (actual_vol / vol * 100) if vol > 0 else 0

        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Volume Rencana", f"{vol:,.2f} {item.get('unit', '')}")
        col2.metric(price_label, format_rupiah(price))
        col3.metric("Total Rencana", format_rupiah(total_rencana))

        st.caption(f"**Realisasi:** {format_rupiah(total_realisasi)} ({persen:.1f}%)")

        st.divider()

        # Volume Input
        new_actual = st.number_input(
            "Volume Aktual Periode Ini",
            value=float(actual_vol),
            step=0.01,
            key=f"{key_prefix}_actual_{rab_id}"
        )

        # Photo Upload (optional)
        uploaded_file = None
        if show_photo_upload:
            st.markdown("**📸 Upload Bukti Foto**")
            uploaded_file = st.file_uploader(
                "Pilih foto (jpg/png/jpeg)",
                type=["jpg", "png", "jpeg"],
                key=f"{key_prefix}_foto_{rab_id}"
            )

        # Save Button
        if st.button("💾 Simpan", key=f"{key_prefix}_save_{rab_id}", use_container_width=True):
            if on_save:
                on_save(item, new_actual, uploaded_file)
            else:
                st.warning("on_save callback belum diimplementasikan")

        # Show existing photo if available (for Opname)
        # Note: photo_url handling should be done in the page that calls this component

    display_hierarchical_tree(
        items=items,
        render_content=render_opname_content,
        search_term=search_term,
        key_prefix=key_prefix
    )