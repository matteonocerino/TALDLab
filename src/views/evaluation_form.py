"""
Evaluation Form View - Form valutazione finale

Questo modulo implementa l'interfaccia per la valutazione finale
dell'intervista condotta dall'utente.

Boundary del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_6 del RAD e mockup UI_3
"""

import streamlit as st
from typing import Optional, List

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.models.tald_item import TALDItem
from src.models.evaluation import UserEvaluation
from src.models.conversation import ConversationHistory
from src.services.evaluation_service import EvaluationService, EvaluationValidationError


def render_evaluation_form(
    tald_items: List[TALDItem],
    current_item: TALDItem,
    conversation: ConversationHistory,
    mode: str
) -> Optional[UserEvaluation]:
    """
    Renderizza il form di valutazione finale.
    
    Implementa RF_6: valutazione finale con form differenziato per modalità.
    
    Args:
        tald_items (List[TALDItem]): Lista completa item TALD
        current_item (TALDItem): Item simulato (ground truth)
        conversation (ConversationHistory): Storico conversazione
        mode (str): "guided" o "exploratory"
        
    Returns:
        UserEvaluation | None: Valutazione validata se confermata, altrimenti None
        
    Example:
        >>> user_eval = render_evaluation_form(
        ...     tald_items=items,
        ...     current_item=item,
        ...     conversation=history,
        ...     mode="guided"
        ... )
        >>> if user_eval:
        ...     # Procedi al confronto e report
    """
    
    # CSS minimo per radio buttons e layout
    st.markdown(_get_evaluation_css(), unsafe_allow_html=True)
    
    # Header con logo
    _render_header(mode)
    
    # Breadcrumb
    mode_label = "📚 Modalità Guidata" if mode == "guided" else "🔍 Modalità Esplorativa"
    st.markdown(f"**{mode_label}** › Intervista › **Valutazione**")
    st.markdown("---")
    
    # Sidebar con riepilogo
    _render_evaluation_sidebar(conversation, current_item, mode)
    
    # Info box iniziale
    _render_info_box(mode, current_item)
    
    # Form principale
    with st.form(key="evaluation_form", clear_on_submit=False):
        
        # CAMPO 1: Identificazione item (solo modalità esplorativa)
        selected_item_id = None
        if mode == "exploratory":
            st.markdown("## 🔍 Identificazione Item TALD")
            st.markdown("**Campo obbligatorio** - Identifica quale disturbo hai osservato")
            
            selected_item_id = _render_item_selector(tald_items)
            
            st.markdown("")
            st.markdown("---")
        
        # CAMPO 2: Attribuzione grado (entrambe le modalità)
        st.markdown("## 📊 Attribuzione Grado TALD")
        st.markdown("**Campo obbligatorio** - Valuta la severità osservata (0-4)")
        
        selected_grade = _render_grade_selector(current_item if mode == "guided" else None)
        
        st.markdown("")
        st.markdown("---")
        
        # CAMPO 3: Note opzionali (entrambe le modalità)
        st.markdown("## 📝 Note Personali")
        st.markdown("*Campo opzionale* - Aggiungi osservazioni sul tuo ragionamento diagnostico")
        
        notes = st.text_area(
            "Le tue note:",
            height=120,
            placeholder="Es: Ho notato almeno 4 intrusioni significative durante l'intervista, "
                       "soprattutto quando parlava del sonno... Il paziente sembrava consapevole "
                       "di perdere il filo ma faticava a riprenderlo.",
            label_visibility="collapsed",
            key="eval_notes"
        )
        
        st.caption("💡 Queste note appariranno nel report finale e ti aiuteranno a riflettere sulla valutazione")
        
        st.markdown("")
        st.markdown("---")
        
        # Pulsanti
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            back_button = st.form_submit_button(
                "← Torna all'Intervista",
                use_container_width=True
            )
        
        with col3:
            submit_button = st.form_submit_button(
                "Conferma Valutazione →",
                use_container_width=True,
                type="primary"
            )
    
    # Gestione pulsante "Torna"
    if back_button:
        st.warning("⚠️ Se torni all'intervista, questa valutazione andrà persa.")
        if st.button("Confermo, torna indietro", type="secondary"):
            return "BACK"  # Segnale speciale per tornare indietro
    
    # Gestione submit
    if submit_button:
        return _handle_evaluation_submit(
            selected_item_id=selected_item_id,
            selected_grade=selected_grade,
            notes=notes,
            mode=mode,
            tald_items=tald_items
        )
    
    return None


def _get_evaluation_css() -> str:
    """CSS minimo per form valutazione."""
    return """
    <style>
    /* Radio button container */
    .grade-option {
        background: #f8f9fa;
        border: 2px solid #dee2e6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.3s;
        cursor: pointer;
    }
    
    .grade-option:hover {
        border-color: #3498db;
        background: #e3f2fd;
    }
    
    .grade-option.selected {
        background: #3498db;
        border-color: #2980b9;
        color: white;
    }
    
    /* Legend box */
    .grade-legend {
        background: #e8f4f8;
        border-left: 4px solid #3498db;
        padding: 1rem;
        border-radius: 4px;
        margin-top: 1rem;
    }
    
    .grade-legend h4 {
        color: #2980b9;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    
    .grade-legend ul {
        margin: 0;
        padding-left: 1.5rem;
        font-size: 0.85rem;
        line-height: 1.8;
    }
    </style>
    """


def _render_header(mode: str):
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
            <h2 style="margin: 0; color: #2c3e50;">Valutazione dell'Intervista</h2>
            <p style="color: #7f8c8d; margin: 0; font-size: 0.9rem;">
                Completa la valutazione basandoti sulle osservazioni effettuate
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("")


def _render_info_box(mode: str, current_item: TALDItem):
    """Renderizza info box iniziale differenziato per modalità."""
    if mode == "guided":
        st.info(f"""
        **📚 Modalità Guidata**
        
        Hai condotto l'intervista sapendo che il paziente manifesta:
        **Item #{current_item.id}: {current_item.title}**
        
        Ora assegna il **grado di severità** (0-4) che hai osservato durante la conversazione.
        """)
    else:
        st.warning("""
        **🔍 Modalità Esplorativa**
        
        Il paziente ha manifestato un disturbo TALD specifico durante l'intervista.
        
        Devi:
        1. **Identificare** quale item TALD hai osservato
        2. **Valutare** il grado di severità (0-4) manifestato
        """)
    
    st.markdown("")


def _render_item_selector(tald_items: List[TALDItem]) -> Optional[int]:
    """
    Renderizza dropdown con ricerca per selezione item (modalità esplorativa).
    
    Implementa RF_6: dropdown con funzionalità ricerca/filtro.
    """
    # Prepara opzioni per selectbox
    item_options = {
        f"Item #{item.id}: {item.title} ({item.type})": item.id
        for item in tald_items
    }
    
    # Aggiungi opzione vuota
    item_options = {"-- Seleziona item --": None, **item_options}
    
    selected_label = st.selectbox(
        "Cerca e seleziona l'item manifestato:",
        options=list(item_options.keys()),
        index=0,
        key="item_selector",
        help="Inizia a digitare per filtrare tra i 30 item TALD disponibili"
    )
    
    selected_id = item_options[selected_label]
    
    # Mostra dettagli item selezionato
    if selected_id:
        selected_item = next(item for item in tald_items if item.id == selected_id)
        
        with st.expander(f"📖 Dettagli {selected_item.title}"):
            st.markdown(f"**Tipo:** {selected_item.type.capitalize()}")
            st.markdown(f"**Descrizione:**")
            st.markdown(selected_item.description)
    
    return selected_id


def _render_grade_selector(current_item: Optional[TALDItem]) -> Optional[int]:
    """
    Renderizza selezione grado con radio buttons e legend.
    
    Args:
        current_item (TALDItem | None): Item corrente (solo in modalità guidata)
    """
    # Radio buttons con Streamlit nativo
    grade = st.radio(
        "Seleziona il grado osservato:",
        options=[0, 1, 2, 3, 4],
        format_func=lambda x: f"{x} - {_get_generic_grade_label(x)}",
        horizontal=True,
        key="grade_selector",
        help="0 = Assente, 1 = Minimo, 2 = Lieve, 3 = Moderato, 4 = Severo"
    )
    
    # Legend con descrizioni specifiche (se item noto)
    if current_item:
        st.markdown(f"""
        <div class="grade-legend">
            <h4>Criteri specifici per {current_item.title}:</h4>
            <ul>
                <li><strong>0:</strong> {current_item.get_grade_description(0)}</li>
                <li><strong>1:</strong> {current_item.get_grade_description(1)}</li>
                <li><strong>2:</strong> {current_item.get_grade_description(2)}</li>
                <li><strong>3:</strong> {current_item.get_grade_description(3)}</li>
                <li><strong>4:</strong> {current_item.get_grade_description(4)}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Legend generica (modalità esplorativa)
        st.info("""
        **Scala TALD standard:**
        - **0**: Disturbo non presente
        - **1**: Dubbio/Minimo (può verificarsi anche in soggetti sani)
        - **2**: Lieve (manifestazione presente ma non grave)
        - **3**: Moderato (manifestazione evidente e frequente)
        - **4**: Severo (manifestazione pervasiva e grave)
        """)
    
    return grade


def _get_generic_grade_label(grade: int) -> str:
    """Restituisce label generica per grado."""
    labels = {
        0: "Assente",
        1: "Minimo",
        2: "Lieve",
        3: "Moderato",
        4: "Severo"
    }
    return labels.get(grade, "")


def _handle_evaluation_submit(
    selected_item_id: Optional[int],
    selected_grade: Optional[int],
    notes: str,
    mode: str,
    tald_items: List[TALDItem]
) -> Optional[UserEvaluation]:
    """
    Gestisce submit della valutazione con validazione.
    
    Usa EvaluationService per validare e creare UserEvaluation.
    """
    try:
        if mode == "guided":
            # Modalità guidata: solo grado
            user_eval = EvaluationService.create_guided_evaluation(
                grade=selected_grade,
                notes=notes
            )
        else:
            # Modalità esplorativa: item + grado
            if selected_item_id is None:
                raise EvaluationValidationError(
                    "Devi selezionare un item TALD dalla lista"
                )
            
            user_eval = EvaluationService.create_exploratory_evaluation(
                item_id=selected_item_id,
                grade=selected_grade,
                items=tald_items,
                notes=notes
            )
        
        # Validazione riuscita
        st.success("✅ Valutazione confermata! Generazione report in corso...")
        return user_eval
    
    except EvaluationValidationError as e:
        st.error(f"❌ **Errore di validazione**\n\n{str(e)}")
        return None
    
    except Exception as e:
        st.error(f"❌ **Errore imprevisto**\n\n{str(e)}")
        return None


def _render_evaluation_sidebar(
    conversation: ConversationHistory,
    current_item: TALDItem,
    mode: str
):
    """Renderizza sidebar con riepilogo conversazione."""
    with st.sidebar:
        st.markdown("## 📊 Riepilogo Intervista")
        
        # Statistiche conversazione
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Messaggi", conversation.get_message_count())
        
        with col2:
            st.metric("Durata", f"{conversation.get_duration_minutes()} min")
        
        st.markdown(f"""
        **Dettagli:**
        - Tue domande: {len(conversation.get_user_messages())}
        - Risposte: {len(conversation.get_assistant_messages())}
        - Parole: {conversation.get_total_words()}
        """)
        
        st.markdown("---")
        
        # Info item (solo guidata)
        if mode == "guided":
            st.markdown("## 📋 Item Simulato")
            st.info(f"""
            **{current_item.id}. {current_item.title}**
            
            Tipo: {current_item.type.capitalize()}
            """)
            
            with st.expander("📖 Criteri"):
                st.markdown(current_item.criteria)
        
        st.markdown("---")
        
        # Suggerimenti
        st.markdown("## 💡 Suggerimenti")
        st.markdown("""
        - Rivedi **mentalmente** la conversazione
        - Valuta **frequenza** manifestazioni
        - Considera **impatto** sulla comunicazione
        - Sii **onesto** nella valutazione
        """)


def show_evaluation_confirmation_dialog() -> bool:
    """
    Mostra dialog di conferma prima di sottomettere valutazione.
    
    Returns:
        bool: True se utente conferma
    """
    st.warning("""
    ⚠️ **Conferma valutazione**
    
    Una volta confermata, non potrai più modificare la tua valutazione.
    Sei sicuro di voler procedere?
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("❌ Rivedi", use_container_width=True):
            return False
    
    with col2:
        if st.button("✅ Conferma", use_container_width=True, type="primary"):
            return True
    
    return False