"""
Item Selection View - Schermata selezione item TALD (Modalità Guidata)

Questo modulo implementa l'interfaccia per la selezione dell'item TALD
da esercitare in modalità guidata.

Boundary del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_2 del RAD (modalità guidata) e mockup UI_2
"""

import streamlit as st
from typing import Optional, List
import base64
import os

from src.utils import scroll_to_top
from src.models.tald_item import TALDItem


def render_item_selection(tald_items: List[TALDItem]) -> Optional[TALDItem]:
    """
    Renderizza l'interfaccia di selezione item TALD per la Modalità Guidata.
    
    Mostra l'elenco completo dei 30 item con filtri e un flusso di conferma.
    
    Args:
        tald_items (List[TALDItem]): Lista completa degli oggetti TALDItem.
        
    Returns:
        TALDItem: L'item TALD selezionato e confermato dall'utente.
        "reset": Se l'utente ha cliccato per tornare alla selezione modalità.
        None: Se nessuna azione è stata completata.
    """

    # Forza scroll in alto all'apertura della pagina
    scroll_to_top("selection-view-top")
    
    render_item_selection_sidebar(tald_items)

    if _render_back_button_sidebar():
        return "reset"

    logo_path = os.path.join("assets", "taldlab_logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            b64_logo = base64.b64encode(f.read()).decode("utf-8")
        logo_element_html = f'<img src="data:image/png;base64,{b64_logo}" alt="TALDLab logo" />'
    else:
        logo_element_html = '<div class="emoji-fallback">🧠</div>'

    st.markdown(f"""
    <div class="brand">
        {logo_element_html}
        <div class="brand-text-container">
            <div class="brand-title">TALDLab</div>
            <div class="brand-sub">Selezione Item TALD</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="breadcrumb">🎯 <strong>Modalità Guidata</strong> › Selezione Item</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    if 'pending_item_selection' in st.session_state:
        selected_item = st.session_state['pending_item_selection']
        return _show_item_confirmation(selected_item)

    st.markdown("## 📚 Seleziona l'Item TALD da Esercitare")
    st.markdown("Scegli quale disturbo del pensiero e del linguaggio vuoi studiare. Puoi filtrare per tipo o cercare per nome.")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        search_term = st.text_input("Cerca per nome o descrizione...", placeholder="es. Derailment...", label_visibility="collapsed")
    with col2:
        filter_type = st.selectbox("Filtra per tipo", ["Tutti", "Oggettivi", "Soggettivi"], label_visibility="collapsed")
    
    filtered_items = _filter_items(tald_items, search_term, filter_type)
    st.caption(f"Mostrando {len(filtered_items)} di {len(tald_items)} item.")

    if not filtered_items:
        st.warning("Nessun item trovato con i filtri selezionati.")
        return None
    
    objective_items = [item for item in filtered_items if item.is_objective()]
    subjective_items = [item for item in filtered_items if item.is_subjective()]
    
    if objective_items:
        st.markdown('<h3 class="section-title">👁️ Fenomeni Oggettivi (osservabili)</h3>', unsafe_allow_html=True)
        if _render_item_list(objective_items, "objective"):
            st.rerun() 
    
    if subjective_items:
        st.markdown('<h3 class="section-title">💭 Fenomeni Soggettivi (riportati)</h3>', unsafe_allow_html=True)
        if _render_item_list(subjective_items, "subjective"):
            st.rerun()
            
    return None


def _filter_items(items: List[TALDItem], search_term: str, filter_type: str) -> List[TALDItem]:
    """Filtra la lista degli item TALD in base ai criteri di ricerca."""
    filtered = items
    if filter_type == "Oggettivi":
        filtered = [item for item in items if item.is_objective()]
    elif filter_type == "Soggettivi":
        filtered = [item for item in items if item.is_subjective()]
    if search_term:
        search_lower = search_term.lower()
        filtered = [item for item in filtered if search_lower in item.title.lower() or search_lower in item.description.lower()]
    return sorted(filtered, key=lambda x: x.id)


def _render_item_list(items: List[TALDItem], key_prefix: str) -> bool:
    """Renderizza una lista di item, restituendo True se uno viene selezionato."""
    for item in items:
        with st.container():
            st.markdown('<div class="item-container">', unsafe_allow_html=True)
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"##### **{item.id}. {item.title}**")
                short_desc = (item.description[:120] + "...") if len(item.description) > 120 else item.description
                st.caption(short_desc)
            with col2:
                if st.button("Seleziona", key=f"select_{key_prefix}_{item.id}", use_container_width=True):
                    st.session_state['pending_item_selection'] = item
                    return True
            
            with st.expander("📖 Dettagli completi"):
                _render_item_details(item)
            st.markdown('</div>', unsafe_allow_html=True)
    return False


def _render_item_details(item: TALDItem):
    """Renderizza i dettagli di un singolo item TALD, inclusa la sua scala di graduazione formattata."""
    type_label = "Oggettivo (osservabile)" if item.is_objective() else "Soggettivo (riportato)"
    st.markdown(f"**Tipo:** {type_label}")
    st.markdown("**Descrizione clinica:**")
    st.markdown(f"*{item.description}*")
    st.markdown("**Criteri diagnostici:**")
    st.markdown(f"*{item.criteria}*")
    if item.example:
        st.markdown("**Esempio tipico:**")
        st.info(item.example)
    
    st.markdown("**Scala di Graduazione Specifica:**")
    
    graduation_lines = []
    grades = sorted(item.graduation.items(), key=lambda x: int(x[0]))
    
    for key, value in grades:
        parts = value.split(':', 1)
        if len(parts) == 2:
            level_name = parts[0].strip().capitalize()
            description = parts[1].strip()
            line = f"- {key} = **{level_name}**: *{description}*"
            graduation_lines.append(line)
        else:
            line = f"- {key} = **{value.strip().capitalize()}**"
            graduation_lines.append(line)

    full_graduation_text = "  \n".join(graduation_lines)
    st.markdown(full_graduation_text)


def _show_item_confirmation(item: TALDItem) -> Optional[TALDItem]:
    """Mostra un banner di conferma e i pulsanti per iniziare o annullare."""

    st.markdown("## Convalida la tua scelta")
    st.success(f"✅ **Item Selezionato:** {item.id}. {item.title}")
    
    with st.expander("Rivedi i dettagli dell'item selezionato", expanded=True):
        _render_item_details(item)

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Annulla e scegli un altro item", use_container_width=True, key="cancel_selection"):
            del st.session_state['pending_item_selection']
            st.rerun()

    with col2:
        if st.button("Conferma e Inizia Intervista ▶️", use_container_width=True, key="confirm_start"):
            del st.session_state['pending_item_selection']
            return item
    
    return None


def render_item_selection_sidebar(tald_items: List[TALDItem]):
    """Renderizza informazioni nella sidebar durante selezione item."""
    with st.sidebar:
        st.markdown("## 📊 Statistiche Item")
        objective_count = len([i for i in tald_items if i.is_objective()])
        subjective_count = len([i for i in tald_items if i.is_subjective()])
        
        col1, col2 = st.columns(2)
        with col1: st.metric("Oggettivi", objective_count)
        with col2: st.metric("Soggettivi", subjective_count)


def _render_back_button_sidebar() -> bool:
    """Mostra un pulsante per tornare alla selezione della modalità e restituisce True se cliccato."""
    if st.sidebar.button("← Torna a Selezione Modalità"):
        if 'pending_item_selection' in st.session_state:
            del st.session_state['pending_item_selection']
        return True
    return False