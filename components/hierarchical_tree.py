"""
components/hierarchical_tree.py
Reusable hierarchical tree component for RAB, RAP, Opname, etc.
"""

import streamlit as st
from collections import defaultdict
from typing import List, Dict, Any, Callable, Optional
"""
components/hierarchical_tree.py
Reusable hierarchical tree component for RAB, RAP, Opname, etc.
"""

import streamlit as st
from collections import defaultdict
from typing import List, Dict, Any, Callable, Optional

def display_rap_tree(
    items: List[Dict],
    on_edit_price: Optional[Callable[[Dict], None]] = None,
    search_term: str = "",
    key_prefix: str = "rap"
) -> None:
    """
    RAP Tree dengan dukungan hierarchy di mana parent_id di rap_items 
    merujuk ke rab_items.id (bukan self-referencing).
    """
    if not items:
        st.info("Tidak ada data untuk ditampilkan.")
        return

    from collections import defaultdict

    # Group children berdasarkan parent_id (ID dari rab_items)
    children_map: Dict[Optional[int], List[Dict]] = defaultdict(list)
    for item in items:
        children_map[item.get('parent_id')].append(item)

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

    def _render_node(parent_id: Optional[int] = None, level: int = 0):
        children = children_map.get(parent_id, [])
        for item in sorted(children, key=lambda x: (x.get('sort_order', 0), x.get('id', 0))):
            code = item.get('code', '')
            desc = item.get('description', '')
            title = f"{code} - {desc}" if code else desc

            if search_term:
                search_lower = search_term.lower().strip()
                if search_lower in str(code).lower() or search_lower in str(desc).lower():
                    title = f"✅ {title}"

            with st.expander(title, expanded=bool(search_term)):
                render_rap_content(item)
                # Recursive menggunakan rab_item_id sebagai parent key
                _render_node(item.get('rab_item_id'), level + 1)

    _render_node()