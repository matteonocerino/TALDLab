"""
Evaluation Form View - Form valutazione finale

Questo modulo implementa l'interfaccia per la valutazione finale
dell'intervista condotta dall'utente.

Boundary del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_6 del RAD e mockup UI_3
"""

from typing import Optional, List, Dict
import base64
import os

import streamlit as st

from src.utils import scroll_to_top
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
        UserEvaluation (se submit valido)
        "RESET" (torna a selezione modalità)
        "BACK_TO_ITEMS" (torna a selezione item)
        None (se nessuna azione)
    """
    # Forza scroll in alto all'apertura della pagina
    scroll_to_top("eval-top-marker")

    # Header con logo
    _render_header(mode)
    
    # Breadcrumb
    mode_label = "🎯 Modalità Guidata" if mode == "guided" else "🔍 Modalità Esplorativa"
    
    if mode == "guided":
        breadcrumb = f'<p class="breadcrumb">{mode_label} › Selezione Item › Intervista › <strong>Valutazione</strong></p>'
    else:
        breadcrumb = f'<p class="breadcrumb">{mode_label} › Intervista › <strong>Valutazione</strong></p>'

    st.markdown(breadcrumb, unsafe_allow_html=True)
    st.markdown("---")

    # Gestione stati di blocco
    if 'eval_submitting' not in st.session_state:
        st.session_state.eval_submitting = False
    
    # Se c'è un popup di conferma nella sidebar, blocchiamo il form centrale
    is_confirming_exit = st.session_state.get("confirm_back_from_eval", False)
    is_form_disabled = st.session_state.eval_submitting or is_confirming_exit

    # sidebar riepilogo 
    back_action = _render_evaluation_sidebar(conversation, current_item, mode)
    if back_action:
        return back_action

    # info box iniziale
    _render_info_box(mode, current_item)

    # Assicura che la session key esista per la selezione item (exploratory)
    if 'eval_selected_item_id' not in st.session_state:
        st.session_state['eval_selected_item_id'] = None

    selected_item_id = None
    selected_item = None

    if mode == "exploratory":
        st.markdown("## 🔍 Identificazione Item TALD")
        st.markdown("**Campo obbligatorio** - Identifica quale disturbo hai osservato")

        # prepara etichette per selectbox (più leggibile)
        options = [f"-- Seleziona item --"]
        id_map: Dict[str, Optional[int]] = {options[0]: None}
        for it in tald_items:
            label = f"{it.id}. {it.title}"
            options.append(label)
            id_map[label] = it.id

        # mantiene scelta in session_state per aggiornare dinamicamente il legend
        selected_label = st.selectbox(
            "Cerca e seleziona l'item manifestato:",
            options=options,
            index=0,
            key="eval_item_selector",
            help="Inizia a digitare per filtrare tra i 30 item TALD disponibili",
            disabled=is_form_disabled
        )

        selected_item_id = id_map.get(selected_label)
        st.session_state['eval_selected_item_id'] = selected_item_id

        if selected_item_id:
            selected_item = next((x for x in tald_items if x.id == selected_item_id), None)
            with st.expander(f"📖 Dettagli {selected_item.title}" if selected_item else "📖 Dettagli"):
                if selected_item:
                    st.markdown(f"**Tipo:** {selected_item.type.capitalize()}")
                    st.markdown(f"**Descrizione:**\n{selected_item.description}")

        st.markdown("---")

    # --- Grade selector (dinamico) ---
    st.markdown("## 📊 Attribuzione Grado TALD")
    st.markdown("**Campo obbligatorio** - Valuta la severità osservata (0-4)")

    # determina item di riferimento per legenda: in guided -> current_item, in exploratory -> selected_item
    item_for_legend = current_item if mode == "guided" else (selected_item if selected_item else None)

    grade = _render_dynamic_grade_selector(item_for_legend, disabled=is_form_disabled)

    st.markdown("---")

    # --- Note ---
    st.markdown("## 📝 Note Personali")
    st.markdown("*Campo opzionale* - Aggiungi osservazioni sul tuo ragionamento diagnostico")

    notes = st.text_area(
        "Le tue note:",
        height=120,
        placeholder="Es: Ho notato almeno 4 intrusioni significative durante l'intervista...",
        label_visibility="collapsed",
        key="eval_notes",
        disabled=is_form_disabled
    )

    st.caption("💡 Queste note appariranno nel report finale e ti aiuteranno a riflettere sulla valutazione")

    st.markdown("")
    st.markdown("---")

    # 1. Inizializzazione stati se non esistono
    if 'eval_error_message' not in st.session_state:
        st.session_state.eval_error_message = None
    if 'eval_message_type' not in st.session_state:
        st.session_state.eval_message_type = "warning"
    if 'eval_message_icon' not in st.session_state:
        st.session_state.eval_message_icon = "⚠️"    
    if 'eval_submitting' not in st.session_state:
        st.session_state.eval_submitting = False

    def _lock_submission():
        st.session_state.eval_submitting = True
        st.session_state.eval_error_message = None

    # 2. DEFINIZIONE COLONNE CENTRALI
    _, col_center, _ = st.columns([1, 1.5, 1])

    with col_center:
        # A. Placeholder Errore (DENTRO la colonna centrale)
        error_container = st.empty()
        
        # B. Spaziatura
        st.markdown("")
        
        # C. Bottone
        st.button(
            "Conferma Valutazione ▶️", 
            use_container_width=True, 
            type="primary",
            disabled=is_form_disabled,
            on_click=_lock_submission
        )

    # 3. Logica di Elaborazione
    if st.session_state.eval_submitting:
        try:
            # VALIDAZIONI
            if mode == "exploratory":
                selected_id_session = st.session_state.get('eval_selected_item_id')
                if selected_id_session is None:
                    raise EvaluationValidationError("Seleziona l'item TALD che hai identificato per procedere.")

            if grade is None:
                raise EvaluationValidationError("Seleziona un grado di severità (0-4) per completare la valutazione.")

            # CREAZIONE OGGETTO
            if mode == "guided":
                user_eval = EvaluationService.create_guided_evaluation(grade=grade, notes=notes)
            else:
                user_eval = EvaluationService.create_exploratory_evaluation(
                    item_id=selected_id_session, grade=grade, items=tald_items, notes=notes
                )

            return user_eval 

        except EvaluationValidationError as e:
            st.session_state.eval_submitting = False
            st.session_state.eval_error_message = str(e)
            st.session_state.eval_message_type = "warning"
            st.session_state.eval_message_icon = "⚠️"
            st.rerun()
            
        except Exception as e:
            st.session_state.eval_submitting = False
            st.session_state.eval_error_message = f"Errore imprevisto: {str(e)}"
            st.session_state.eval_message_type = "error"
            st.session_state.eval_message_icon = "❌"
            st.rerun()

    # 4. Rendering del Messaggio di Errore
    if st.session_state.eval_error_message:
        # Scrive nel container 
        with error_container.container():
            if st.session_state.eval_message_type == "error":
                st.error(st.session_state.eval_error_message, icon=st.session_state.eval_message_icon)
            else:
                st.warning(st.session_state.eval_error_message, icon=st.session_state.eval_message_icon)

    return None


def _clear_error_state():
    """
    Helper per pulire i messaggi di errore dalla sessione.
    Da chiamare quando si esce dalla pagina.
    """
    keys = ['eval_error_message', 'eval_message_type', 'eval_message_icon', 'eval_submitting']
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]


def _render_header(mode: str):
    """Renderizza header con logo e branding coerente."""
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
            <div class="brand-title">Valutazione Finale</div>
            <div class="brand-sub">Valuta le manifestazioni osservate durante l'intervista</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_info_box(mode: str, current_item: TALDItem):
    """Info box differenziato per modalità."""
    if mode == "guided":
        st.info(f"""
        **📚 Modalità Guidata**
        
        Hai condotto l'intervista sapendo che il paziente manifesta:
        **Item {current_item.id}. {current_item.title}**
        
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


def _render_dynamic_grade_selector(item: Optional[TALDItem], disabled: bool = False) -> int:
    """
    Rendering dinamico della scala 0–4 in funzione dell'item selezionato.
    
    - Se l'item è noto (guided o exploratory con item selezionato):
      usa label e descrizioni specifiche dell'item.
    - Se l'item non è disponibile, usa etichette generiche TALD.

    Ritorna il grado selezionato (int).
    """

    # Preparazione opzioni radio
    options = []
    format_map = {}

    for g in range(5):
        if item:
            # Estrae il nome del livello dal campo graduation dell'item
            label = _extract_grade_label_from_item(item, g)
            option_label = f"{g} – {label}"
        else:
            # Fallback a etichette generiche
            option_label = f"{g} – {_get_generic_grade_label(g)}"

        options.append(option_label)
        format_map[option_label] = g

    # Radio button con etichette già formattate
    selected_label = st.radio(
        "Seleziona il grado osservato:",
        options=options,
        index=None,
        key="eval_grade_selector",
        help="Scegli il livello che più rappresenta la manifestazione osservata",
        disabled=disabled
    )

    if selected_label is None:
        selected_grade = None
    else:
        selected_grade = format_map[selected_label]


    # Mostra legenda sotto il selettore
    if item:
        # Costruzione dinamica della lista descrizioni basata sul JSON dell'item
        lines = []
        for g in range(5):
            raw_desc = item.get_grade_description(g)
            
            # Separiamo "Nome Livello" da "Descrizione"
            parts = raw_desc.split(':', 1)
            
            if len(parts) == 2:
                # Caso: "Lieve: descrizione..."
                level_name = parts[0].strip().capitalize()
                description = parts[1].strip()
                # Formato: 2 = **Lieve**: *descrizione*
                line = f"<li>{g} = <b>{level_name}</b>: <i>{description}</i></li>"
            else:
                # Caso: "Lieve" (senza descrizione extra)
                level_name = raw_desc.strip().capitalize()
                line = f"<li>{g} = <b>{level_name}</b></li>"
            
            lines.append(line)

        legend_html = (
            "<div class='grade-legend'>"
            "<h4>Criteri specifici:</h4>"
            "<ul>" + "".join(lines) + "</ul>"
            "</div>"
        )
        st.markdown(legend_html, unsafe_allow_html=True)
        
    else:
        # Legend generica, usata solo se item non selezionato (exploratory pre-selezione)
        st.info("""
        **Scala TALD standard:**
        - **0**: Disturbo non presente
        - **1**: Dubbio/Minimo
        - **2**: Lieve
        - **3**: Moderato
        - **4**: Severo
        """)

    return selected_grade


def _extract_grade_label_from_item(item: TALDItem, grade: int) -> str:
    """
    Estrae il "nome" del livello di gravità dagli item TALD.

    I campi graduation nel JSON hanno struttura:
    "2": "Lieve: tendenza alla deviazione del tema..."

    Da qui estraggo:
    - prima della ':' se esiste
    - altrimenti prima del primo '.', come fallback
    - se non trovato, restituisco stringa ripulita e capitalizzata
    """

    try:
        raw = item.graduation.get(str(grade)) if hasattr(item, "graduation") else None

        if not raw:
            return _get_generic_grade_label(grade)

        if ":" in raw:
            return raw.split(":", 1)[0].strip().capitalize()

        if "." in raw:
            return raw.split(".", 1)[0].strip().capitalize()

        return raw.strip().capitalize()

    except Exception:
        # Protezione in caso di errore inatteso nella struttura del JSON
        return _get_generic_grade_label(grade)


def _get_generic_grade_label(grade: int) -> str:
    """
    Label standard TALD per la scala 0–4.
    """
    labels = {
        0: "Assente",
        1: "Minimo",
        2: "Lieve",
        3: "Moderato",
        4: "Severo"
    }
    return labels.get(grade, "")


def _render_evaluation_sidebar(
    conversation: ConversationHistory,
    current_item: TALDItem,
    mode: str
) -> Optional[str]:
    """
    Sidebar con riepilogo coerente alle altre view.

    Mostra:
    - Statistiche conversazione
    - Info item (solo in modalità guidata)
    - Suggerimenti
    - Bottone back con warning inline
    
    Returns:
        "RESET": torna a selezione modalità
        "BACK_TO_ITEMS": torna a selezione item (guided)
        None: nessuna azione
    """
    with st.sidebar:

        st.markdown("## 📊 Riepilogo Intervista")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Messaggi", conversation.get_message_count())
        with col2:
            st.metric("Minuti", f"{conversation.get_duration_minutes()}")

        st.caption(f"Parole scambiate: {conversation.get_total_words()}")

        st.markdown("---")

        if mode == "guided":
            st.markdown("## 📋 Item Simulato")
            st.info(f"**{current_item.id}. {current_item.title}**\n\nTipo: {current_item.type.capitalize()}")

            with st.expander("📖 Criteri diagnostici"):
                st.markdown(current_item.criteria)

        else:
            st.markdown("## 📋 Obiettivo")
            st.warning("**Identifica l'item TALD** e valutane il grado di manifestazione.")

        st.markdown("---")

        st.markdown("## 💡 Suggerimenti")
        st.markdown("""
        - Rivedi **mentalmente** la conversazione
        - Valuta **frequenza** manifestazioni
        - Considera **impatto** sulla comunicazione
        - Sii **onesto** nella valutazione
        """)

        # BACK BUTTON CON WARNING INLINE
        st.markdown("---")
        
        # Controlla se c'è warning attivo
        if st.session_state.get("confirm_back_from_eval"):
            return _render_sidebar_back_warning(mode)
        
        # Bottone normale
        label = "← Torna a Selezione Item" if mode == "guided" else "← Torna a Selezione Modalità"
        # Disabilita il bottone se stiamo inviando
        if st.button(label, use_container_width=True, disabled=st.session_state.eval_submitting):
            st.session_state.confirm_back_from_eval = True
            st.rerun()
    
    return None


def _render_sidebar_back_warning(mode: str) -> Optional[str]:
    """
    Renderizza il warning di conferma DENTRO la sidebar.
    
    Returns:
        "RESET" o "BACK_TO_ITEMS" se confermato
        None se annullato
    """
    st.warning("""
    ⚠️ **Attenzione**
    
    Se torni indietro perderai la sessione corrente.
    Confermi?
    """)

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("❌ Annulla", use_container_width=True, key="cancel_back_eval"):
            del st.session_state["confirm_back_from_eval"]
            st.rerun()
    
    with col2:
        if st.button("✅ Conferma", use_container_width=True, type="primary", key="confirm_back_eval"):
            del st.session_state["confirm_back_from_eval"]
            
            _clear_error_state()

            if mode == "guided":
                return "BACK_TO_ITEMS"
            else:
                return "RESET"
    
    return None