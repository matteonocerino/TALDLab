"""
Item Selection View - Schermata selezione item TALD (Modalità Guidata)

Questo modulo implementa l'interfaccia per la selezione dell'item TALD
da esercitare in modalità guidata.

Boundary del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_2 del RAD (modalità guidata) e mockup UI_2
"""

import streamlit as st
from typing import Optional, List

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.models.tald_item import TALDItem


def render_item_selection(tald_items: List[TALDItem]) -> Optional[TALDItem]:
    """
    Renderizza l'interfaccia di selezione item TALD.
    
    Implementa RF_2 (modalità guidata): gestione item TALD.
    Mostra elenco completo dei 30 item con descrizioni.
    
    Args:
        tald_items (List[TALDItem]): Lista completa degli item TALD
        
    Returns:
        TALDItem | None: Item selezionato o None se nessuna selezione
        
    Example:
        >>> selected = render_item_selection(items)
        >>> if selected:
        ...     # Avvia intervista con questo item
    """
    
    # Header con logo
    _render_header()
    
    # Breadcrumb
    st.markdown("🎯 **Modalità Guidata** › Selezione Item")
    st.markdown("---")
    
    # Titolo e istruzioni
    st.markdown("## 📚 Seleziona l'Item TALD da Esercitare")
    st.markdown("""
    Scegli quale disturbo del pensiero e del linguaggio vuoi studiare. 
    Puoi filtrare per tipo (oggettivo/soggettivo) o cercare per nome.
    """)
    
    st.markdown("")  # Spacing
    
    # Filtri e ricerca
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        search_term = st.text_input(
            "🔍 Cerca per nome",
            placeholder="es. Circumstantiality, Derailment...",
            label_visibility="collapsed"
        )
    
    with col2:
        filter_type = st.selectbox(
            "Filtra per tipo",
            options=["Tutti", "Oggettivi", "Soggettivi"],
            label_visibility="collapsed"
        )
    
    with col3:
        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Reset", use_container_width=True):
            st.rerun()
    
    # Filtra items
    filtered_items = _filter_items(tald_items, search_term, filter_type)
    
    # Mostra conteggio risultati
    st.caption(f"Mostrando {len(filtered_items)} di {len(tald_items)} item")
    
    st.markdown("")  # Spacing
    
    # Lista items
    if not filtered_items:
        st.warning("Nessun item trovato con i filtri selezionati.")
        return None
    
    # Separa per tipo
    objective_items = [item for item in filtered_items if item.is_objective()]
    subjective_items = [item for item in filtered_items if item.is_subjective()]
    
    # Mostra items oggettivi
    if objective_items:
        st.markdown("### 👁️ Fenomeni Oggettivi (osservabili)")
        st.caption(f"{len(objective_items)} item disponibili")
        
        selected_objective = _render_item_list(objective_items, "objective")
        if selected_objective:
            return selected_objective
    
    # Mostra items soggettivi
    if subjective_items:
        st.markdown("### 💭 Fenomeni Soggettivi (riportati)")
        st.caption(f"{len(subjective_items)} item disponibili")
        
        selected_subjective = _render_item_list(subjective_items, "subjective")
        if selected_subjective:
            return selected_subjective
    
    return None


def _render_header():
    """Renderizza header con logo."""
    header_col1, header_col2 = st.columns([1, 11])
    
    with header_col1:
        try:
            st.image("assets/taldlab_logo.png", width=60)
        except:
            st.markdown("<div style='font-size: 3rem;'>🧠</div>", unsafe_allow_html=True)
    
    with header_col2:
        st.markdown("""
        <div style="margin-top: 5px;">
            <h2 style="margin: 0; color: #2c3e50;">TALDLab</h2>
            <p style="color: #7f8c8d; margin: 0; font-size: 0.9rem;">Selezione Item TALD</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("")


def _filter_items(
    items: List[TALDItem], 
    search_term: str, 
    filter_type: str
) -> List[TALDItem]:
    """
    Filtra gli item in base a ricerca e tipo.
    
    Args:
        items (List[TALDItem]): Lista completa
        search_term (str): Termine di ricerca
        filter_type (str): "Tutti", "Oggettivi", "Soggettivi"
        
    Returns:
        List[TALDItem]: Items filtrati
    """
    filtered = items.copy()
    
    # Filtro per tipo
    if filter_type == "Oggettivi":
        filtered = [item for item in filtered if item.is_objective()]
    elif filter_type == "Soggettivi":
        filtered = [item for item in filtered if item.is_subjective()]
    
    # Filtro per ricerca
    if search_term:
        search_lower = search_term.lower()
        filtered = [
            item for item in filtered 
            if search_lower in item.title.lower() or 
               search_lower in item.description.lower()
        ]
    
    # Ordina per ID
    filtered.sort(key=lambda x: x.id)
    
    return filtered


def _render_item_list(items: List[TALDItem], item_type: str) -> Optional[TALDItem]:
    """
    Renderizza lista di item con expander per dettagli.
    
    Args:
        items (List[TALDItem]): Items da mostrare
        item_type (str): "objective" o "subjective" (per key unici)
        
    Returns:
        TALDItem | None: Item selezionato o None
    """
    for item in items:
        # Container per ogni item
        with st.container():
            col1, col2 = st.columns([10, 2])
            
            with col1:
                # Titolo item
                st.markdown(f"**{item.id}. {item.title}**")
                
                # Descrizione breve (primo pezzo)
                short_desc = item.description[:120] + "..." if len(item.description) > 120 else item.description
                st.caption(short_desc)
            
            with col2:
                # Pulsante selezione
                if st.button(
                    "Seleziona",
                    key=f"select_{item_type}_{item.id}",
                    use_container_width=True,
                    type="primary"
                ):
                    # Mostra dettagli e conferma
                    return _show_item_confirmation(item)
            
            # Expander per dettagli completi
            with st.expander(f"📖 Dettagli {item.title}"):
                _render_item_details(item)
            
            st.markdown("")  # Spacing tra item
    
    return None


def _render_item_details(item: TALDItem):
    """
    Renderizza i dettagli completi di un item.
    
    Args:
        item (TALDItem): Item da visualizzare
    """
    # Tipo
    type_label = "Oggettivo (osservabile)" if item.is_objective() else "Soggettivo (riportato)"
    st.markdown(f"**Tipo:** {type_label}")
    
    # Descrizione completa
    st.markdown("**Descrizione clinica:**")
    st.markdown(item.description)
    
    # Criteri diagnostici
    st.markdown("**Criteri diagnostici:**")
    st.markdown(item.criteria)
    
    # Esempio
    if item.example:
        st.markdown("**Esempio tipico:**")
        st.info(item.example)
    
    # Scala graduazione
    st.markdown("**Scala di graduazione (0-4):**")
    for grade in range(5):
        grade_desc = item.get_grade_description(grade)
        st.markdown(f"- **{grade}**: {grade_desc}")


def _show_item_confirmation(item: TALDItem) -> TALDItem:
    """
    Mostra dialog di conferma selezione item.
    
    Args:
        item (TALDItem): Item selezionato
        
    Returns:
        TALDItem: Item confermato
    """
    # Salva in session_state temporaneo per conferma
    st.session_state['pending_item_selection'] = item
    
    # Mostra modal di conferma
    st.markdown("---")
    st.success(f"✅ Hai selezionato: **{item.id}. {item.title}**")
    
    col1, col2 = st.columns([8, 4])
    
    with col1:
        st.markdown("**Riepilogo:**")
        st.markdown(f"- **Tipo:** {'Oggettivo' if item.is_objective() else 'Soggettivo'}")
        st.markdown(f"- **Grado predefinito simulazione:** {item.default_grade}/4")
        st.caption(item.description[:150] + "...")
    
    with col2:
        st.markdown("")  # Spacing
        if st.button(
            "▶️ Inizia Intervista",
            use_container_width=True,
            type="primary",
            key="confirm_start"
        ):
            return item
        
        if st.button(
            "← Cambia Item",
            use_container_width=True,
            key="cancel_selection"
        ):
            if 'pending_item_selection' in st.session_state:
                del st.session_state['pending_item_selection']
            st.rerun()
    
    return None


def render_item_selection_sidebar(tald_items: List[TALDItem]):
    """
    Renderizza informazioni nella sidebar durante selezione item.
    
    Args:
        tald_items (List[TALDItem]): Lista completa item
    """
    with st.sidebar:
        st.markdown("## 📊 Statistiche Item")
        
        objective_count = len([i for i in tald_items if i.is_objective()])
        subjective_count = len([i for i in tald_items if i.is_subjective()])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Oggettivi", objective_count)
        with col2:
            st.metric("Soggettivi", subjective_count)
        
        st.markdown("---")
        
        st.markdown("## ℹ️ Scala TALD")
        st.info("""
        **Graduazione 0-4:**
        - 0: Non presente
        - 1: Dubbio
        - 2: Lieve (mild)
        - 3: Moderato (moderate)
        - 4: Severo (severe)
        
        *Ogni item ha descrizioni specifiche per i gradi*
        """)
        
        st.markdown("---")
        
        st.markdown("## 💡 Suggerimenti")
        st.markdown("""
        - Leggi i **dettagli** prima di selezionare
        - Nota il **tipo** (oggettivo/soggettivo)
        - Consulta gli **esempi** tipici
        """)


def show_cancel_selection_dialog():
    """
    Mostra dialog per annullare la selezione e tornare a scelta modalità.
    """
    if st.sidebar.button("← Torna a Selezione Modalità", use_container_width=True):
        # Reset a mode selection
        if 'pending_item_selection' in st.session_state:
            del st.session_state['pending_item_selection']
        
        from src.views.mode_selection import reset_to_mode_selection
        reset_to_mode_selection()