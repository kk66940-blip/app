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


# ==================== OPNAME TREE ====================
def display_opname_tree(
    items: List[Dict],
    actual_map: Optional[Dict] = None,
    on_save: Optional[Callable] = None,
    show_photo_upload: bool = False,
    rap_price_map: Optional[Dict] = None,
    photo_map: Optional[Dict] = None,
    search_term: str = "",
    key_prefix: str = "opname",
) -> None:
    """Specialized tree untuk halaman Opname dengan input volume inline.

    Parameters
    ----------
    items           : Daftar RAB items (parent dan leaf) dari Supabase.
    actual_map      : {rab_item_id: actual_volume} dari opname_details.
    on_save         : Callback fn(item, new_volume, uploaded_file) untuk simpan.
    show_photo_upload: Tampilkan widget upload foto (Opname utama).
    rap_price_map   : {rab_item_id: execution_price} untuk Opname Sub.
                      Jika None, digunakan unit_price dari RAB.
    photo_map       : {rab_item_id: photo_url} untuk tampil foto yang sudah ada.
    search_term     : Filter pencarian.
    key_prefix      : Prefix unik agar tidak ada konflik widget key.
    """
    from utils.helpers import format_rupiah

    # Normalisasi default
    if actual_map is None:
        actual_map = {}
    if rap_price_map is None:
        rap_price_map = {}
    if photo_map is None:
        photo_map = {}

    # Bangun children_map sekali untuk kalkulasi subtotal header
    children_map_local = build_tree(items)

    def _calc_subtotal(parent_id) -> float:
        """Hitung total nilai opname seluruh descendants secara rekursif."""
        total = 0.0
        for child in children_map_local.get(parent_id, []):
            cid = child['id']
            vol = actual_map.get(cid, 0) or 0
            price = (rap_price_map.get(cid, 0) or 0) if rap_price_map \
                    else (child.get('unit_price', 0) or 0)
            total += vol * price
            total += _calc_subtotal(cid)
        return total

    def render_opname_content(item: Dict):
        item_id = item.get('id')
        vol_rab = item.get('volume', 0) or 0
        unit    = item.get('unit', '')

        # Tentukan harga: RAP atau RAB
        if rap_price_map:
            price       = rap_price_map.get(item_id, 0) or 0
            price_label = "Harga RAP"
        else:
            price       = item.get('unit_price', 0) or 0
            price_label = "Harga RAB"

        # ── Header / grup (vol_rab == 0): tampilkan ringkasan subtotal ──
        if vol_rab == 0:
            subtotal = _calc_subtotal(item_id)
            if subtotal > 0:
                st.caption(f"📊 Total nilai opname grup ini: **{format_rupiah(subtotal)}**")
            else:
                st.caption("— Belum ada data opname di grup ini")
            return

        # ── Leaf item: tampilkan metrics + form input ──
        vol_opname  = actual_map.get(item_id, 0) or 0
        nilai_opname = vol_opname * price

        # Metrics row
        col1, col2, col3 = st.columns(3)
        col1.metric("Volume RAB", f"{vol_rab:,.2f} {unit}")
        col2.metric("Volume Opname", f"{vol_opname:,.2f} {unit}")
        col3.metric(price_label, format_rupiah(price))

        # Nilai & persentase (hanya jika sudah ada data)
        if vol_opname > 0:
            persen = (vol_opname / vol_rab * 100) if vol_rab > 0 else 0
            st.success(
                f"✅  Nilai: **{format_rupiah(nilai_opname)}** "
                f"({persen:.1f}% dari volume RAB)"
            )

        # Foto sebelumnya (di luar form)
        if show_photo_upload and photo_map.get(item_id):
            with st.expander("🖼️ Lihat Foto Sebelumnya", expanded=False):
                st.image(photo_map[item_id], use_container_width=True)

        # ── Form input volume (+ foto opsional) ──
        with st.form(key=f"{key_prefix}_form_{item_id}"):
            new_volume = st.number_input(
                "📥 Input Volume Opname",
                min_value=0.0,
                value=float(vol_opname),
                step=0.01,
                format="%.2f",
            )

            uploaded_file = None
            if show_photo_upload:
                uploaded_file = st.file_uploader(
                    "📸 Upload Foto (opsional)",
                    type=["jpg", "jpeg", "png"],
                )

            # Pratinjau nilai baru sebelum simpan
            if price > 0:
                nilai_baru = new_volume * price
                st.caption(f"💡 Pratinjau nilai: {format_rupiah(nilai_baru)}")

            submitted = st.form_submit_button(
                "💾 Simpan",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                if on_save:
                    on_save(item, new_volume, uploaded_file)
                else:
                    st.warning("⚠️ Fungsi simpan belum dikonfigurasi")

    display_hierarchical_tree(
        items=items,
        render_content=render_opname_content,
        search_term=search_term,
        key_prefix=key_prefix,
    )
