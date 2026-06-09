"""
components/hierarchical_tree.py
Reusable hierarchical tree component for RAB, RAP, Opname, etc.
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

            if search_term:
                search_lower = search_term.lower().strip()
                if (search_lower in str(item.get('code', '')).lower() or 
                    search_lower in str(item.get('description', '')).lower()):
                    title = f"✅ {title}"

            with st.expander(title, expanded=expanded_by_default or bool(search_term)):
                if render_content:
                    render_content(item)
                else:
                    st.write(f"**ID:** {item_id}")
                    st.write(f"**Level:** {item.get('level', 0)}")
                    if item.get('volume'):
                        st.write(f"**Volume:** {item['volume']} {item.get('unit', '')}")

                _render_node(item_id, level + 1)

    _render_node()


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
    on_edit_price: Optional[Callable[[Dict], None]] = None,
    search_term: str = "",
    key_prefix: str = "rap"
) -> None:
    """Specialized tree for RAP pages (focus on execution price & upah)."""
    
    def render_rap_content(item: Dict):
        from utils.helpers import format_rupiah
        
        vol = item.get('volume') or 0
        planned = item.get('planned_price') or 0
        exec_price = item.get('execution_price') or 0
        upah = item.get('upah') or 0

        total_rencana = vol * planned
        total_pelaksanaan = vol * exec_price
        total_upah = vol * upah

        col1, col2, col3 = st.columns(3)
        col1.metric("Volume", f"{vol:,.2f} {item.get('unit', '')}")
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
                if on_edit_price:
                    on_edit_price(item)
                else:
                    st.session_state[f"{key_prefix}_edit_item"] = item
                    st.rerun()
        with col_del:
            if st.button("🗑️ Hapus", key=f"{key_prefix}_del_{item['id']}", use_container_width=True):
                st.warning("Fitur hapus akan ditambahkan nanti")

    display_hierarchical_tree(
        items=items,
        render_content=render_rap_content,
        search_term=search_term,
        key_prefix=key_prefix
    )
    
# ==================== OPNAME TREE (VERSI FLEXIBLE) ====================
def display_opname_tree(
    items: List[Dict],
    search_term: str = "",
    key_prefix: str = "opname",
    **kwargs  # menangkap parameter ekstra agar tidak error
) -> None:
    """Specialized tree untuk halaman Opname (versi aman)."""
    
    def render_opname_content(item: Dict):
        from utils.helpers import format_rupiah
        
        vol = item.get('volume', 0) or 0
        volume_opname = item.get('volume_opname', 0) or 0
        persentase = item.get('persentase', 0) or 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Volume RAB", f"{vol:,.2f} {item.get('unit', '')}")
        col2.metric("Volume Opname", f"{volume_opname:,.2f}")
        col3.metric("Persentase", f"{persentase:.1f}%")

        # Tombol aksi (placeholder)
        col_edit, col_del = st.columns(2)
        with col_edit:
            if st.button("✏️ Edit Opname", key=f"{key_prefix}_edit_{item.get('id', 'x')}", use_container_width=True):
                st.session_state[f"{key_prefix}_edit_item"] = item
                st.rerun()
        with col_del:
            if st.button("🗑️ Hapus", key=f"{key_prefix}_del_{item.get('id', 'x')}", use_container_width=True):
                st.warning("Fitur hapus Opname belum aktif")

    display_hierarchical_tree(
        items=items,
        render_content=render_opname_content,
        search_term=search_term,
        key_prefix=key_prefix
    )