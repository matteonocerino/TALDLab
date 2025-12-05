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
        current_item (TALDItem): Item simulato (o placeholder in esplorativa)
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

    # Controlla se il warning "paziente sano" è attivo
    is_showing_healthy_warning = st.session_state.get("show_healthy_warning", False)
    
    # Se c'è un popup di conferma nella sidebar, blocchiamo il form centrale
    is_confirming_exit = st.session_state.get("confirm_back_from_eval", False)

    is_form_disabled = (
        st.session_state.eval_submitting or 
        is_confirming_exit or 
        is_showing_healthy_warning  
    )

    # sidebar riepilogo 
    back_action = _render_evaluation_sidebar(conversation, current_item, mode)
    if back_action:
        return back_action

    # info box iniziale
    _render_info_box(mode, current_item)

    # Inizializzazione variabili per il submit
    user_eval = None
    notes = ""

    # === LOGICA DIFFERENZIATA PER MODALITÀ ===
    
    if mode == "guided":
        # --- MODALITÀ GUIDATA (Singolo Item) ---
        st.markdown(f"## 📊 Attribuzione Grado: {current_item.title}")
        st.markdown("**Campo obbligatorio** - Valuta la severità osservata (0-4)")

        # Usa il selettore dinamico specifico per l'item corrente
        grade = _render_dynamic_grade_selector(current_item, key_suffix="guided", disabled=is_form_disabled)
        
        st.markdown("---")
        
        # Campo Note
        st.markdown("## 📝 Note Personali")
        st.markdown("*Campo opzionale* - Aggiungi osservazioni sul tuo ragionamento diagnostico")
        notes = st.text_area(
            "Le tue note:",
            height=120,
            placeholder="Es: Ho notato...",
            label_visibility="collapsed",
            key="eval_notes_guided",
            disabled=is_form_disabled
        )
        
        # Prepariamo i dati per il submit (singolo valore)
        submit_data = grade

    else:
        # --- MODALITÀ ESPLORATIVA (Scheda Completa 30 Item) ---
        st.markdown("## 📋 Scheda di Valutazione TALD")
        st.info("Compila la scheda assegnando un grado (0-4) ai disturbi rilevati. Lascia a 0 quelli assenti.")

        # Inizializzazione dello sheet in session state per persistenza
        if "exploratory_sheet" not in st.session_state:
            st.session_state.exploratory_sheet = {}

        evaluation_sheet = st.session_state.exploratory_sheet

        # --- FILTRI (Ricerca + Tipo) ---
        col_search, col_filter = st.columns([3, 1])
        
        with col_search:
            search_query = st.text_input(
                "🔍 Cerca disturbo...", 
                placeholder="Digita per cercare (es. 'block', 'thought')...",
                label_visibility="collapsed",
                disabled=is_form_disabled
            )
            
        with col_filter:
            filter_type = st.selectbox(
                "Filtra per tipo",
                ["Tutti", "Oggettivi", "Soggettivi"],
                label_visibility="collapsed",
                disabled=is_form_disabled
            )
        
        # 1. Filtro Testuale (Base)
        if search_query:
            filtered_items = [
                i for i in tald_items 
                if search_query.lower() in i.title.lower() or search_query.lower() in i.description.lower()
            ]
        else:
            filtered_items = tald_items

        # 2. Suddivisione liste (dopo filtro testo)
        obj_filtered = [i for i in filtered_items if i.is_objective()]
        subj_filtered = [i for i in filtered_items if i.is_subjective()]

        # 3. Rendering Condizionale (Logica del Dropdown)
        items_shown = False # Flag per sapere se abbiamo mostrato qualcosa

        # SEZIONE OGGETTIVI: Mostra se il filtro è 'Tutti' o 'Oggettivi' E ci sono item
        if filter_type in ["Tutti", "Oggettivi"] and obj_filtered:
            st.markdown('<h3 class="section-title">👁️ Fenomeni Oggettivi (osservabili)</h3>', unsafe_allow_html=True)
            _render_item_grid(obj_filtered, evaluation_sheet, is_form_disabled)
            items_shown = True
        
        # SEZIONE SOGGETTIVI: Mostra se il filtro è 'Tutti' o 'Soggettivi' E ci sono item
        if filter_type in ["Tutti", "Soggettivi"] and subj_filtered:
            if items_shown: st.markdown("---") # Separatore estetico se c'era la sezione prima
            st.markdown('<h3 class="section-title">💭 Fenomeni Soggettivi (riportati)</h3>', unsafe_allow_html=True)
            _render_item_grid(subj_filtered, evaluation_sheet, is_form_disabled)
            items_shown = True

        # Messaggio se i filtri hanno nascosto tutto
        if not items_shown:
            st.warning("Nessun item corrisponde ai criteri di ricerca selezionati.")

        st.markdown("---")

        # Campo Note
        st.markdown("## 📝 Note Personali")
        notes = st.text_area(
            "Le tue note:",
            height=120,
            placeholder="Motiva la diagnosi...",
            label_visibility="collapsed",
            key="eval_notes_exploratory",
            disabled=is_form_disabled
        )
        
        # Prepariamo i dati per il submit (intero sheet)
        submit_data = evaluation_sheet

    st.markdown("---")

    # 1. Inizializzazione stati errore
    if 'eval_error_message' not in st.session_state:
        st.session_state.eval_error_message = None
    if 'eval_message_type' not in st.session_state:
        st.session_state.eval_message_type = "warning"
    if 'eval_message_icon' not in st.session_state:
        st.session_state.eval_message_icon = "⚠️"    

    def _lock_submission():
        st.session_state.eval_submitting = True
        st.session_state.eval_error_message = None

    # 2. BOTTONE CONFERMA
    _, col_center, _ = st.columns([1, 1.5, 1])

    # Nascondi il pulsante "Conferma Valutazione" se il warning è attivo
    if not is_showing_healthy_warning:
        # Rendering del pulsante Conferma
        _, col_center, _ = st.columns([1, 1.5, 1])
        with col_center:
            error_container = st.empty()
            st.markdown("")
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
            if mode == "exploratory":
                # Verifica se tutti i valori sono 0 o None
                is_empty_sheet = not submit_data or all(v == 0 for v in submit_data.values())
                
                # Se la scheda è vuota E l'utente non ha ancora confermato esplicitamente
                if is_empty_sheet and not st.session_state.get("confirm_healthy_patient", False):
                    st.session_state.eval_submitting = False  # Blocca l'invio
                    st.session_state.show_healthy_warning = True  # Mostra il warning
                    st.rerun()

            if mode == "guided" and submit_data is None:
                raise EvaluationValidationError("Seleziona un grado di severità (0-4) per completare la valutazione.")

            # VALIDAZIONE TRAMITE SERVICE
            if mode == "guided":
                user_eval = EvaluationService.create_guided_evaluation(
                    target_item_id=current_item.id,
                    grade=submit_data,
                    notes=notes
                )
            else:
                user_eval = EvaluationService.create_exploratory_evaluation(
                    evaluation_sheet=submit_data,
                    all_items=tald_items,
                    notes=notes
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

    # Rendering del Warning 
    if is_showing_healthy_warning:
        st.warning("""
        ⚠️ **Attenzione: Nessun disturbo rilevato**
        
        Tutti i valori sono a 0. Stai indicando che il paziente è **ASINTOMATICO (Sano)**.
        Sei sicuro di non aver rilevato alcun fenomeno TALD?
        """)

        col_h1, col_h2 = st.columns(2)
        with col_h1:
            if st.button("❌ No, ho dimenticato di compilare", use_container_width=True):
                st.session_state.show_healthy_warning = False
                st.rerun()
        with col_h2:
            if st.button("✅ Sì, confermo Paziente Sano", use_container_width=True, type="primary"):
                st.session_state.confirm_healthy_patient = True # Sblocca il check
                st.session_state.show_healthy_warning = False
                _lock_submission() # Ri-innesca il submit
                st.rerun()
        
        # Interrompe qui il rendering per impedire di vedere errori doppi
        return None

    # 4. Rendering del Messaggio di Errore
    if st.session_state.eval_error_message:
        with error_container.container():
            if st.session_state.eval_message_type == "error":
                st.error(st.session_state.eval_error_message, icon=st.session_state.eval_message_icon)
            else:
                st.warning(st.session_state.eval_error_message, icon=st.session_state.eval_message_icon)

    return None


def _render_item_grid(items: List[TALDItem], sheet_storage: Dict, disabled: bool):
    """
    Renderizza la griglia di item con selettori per ciascuno.
    """
    for item in items:
        current_val = sheet_storage.get(item.id, 0)

        with st.container(border=True):
            st.markdown(f"##### {item.id}. {item.title}")

            with st.expander("ℹ️ Guida Clinica (Descrizione, Criteri, Esempi)"):
                st.markdown(f"**Descrizione:** {item.description}")
                st.markdown(f"**Criteri Diagnostici:** {item.criteria}")
                st.info(f"**Esempio:** {item.example}")

            st.markdown("---")

            options = []
            format_map = {}

            for g in range(5):
                raw = item.graduation.get(str(g), "").strip()

                grade_text = ""
                desc_text = ""

                if ":" in raw:
                    parts = raw.split(":", 1)
                    grade_text = parts[0].strip()
                    desc_text = parts[1].strip()
                else:
                    grade_text = raw
                    desc_text = ""

                if not grade_text:
                    grade_text = f"Livello {g}"
                
                grade_text = grade_text.capitalize()

                if desc_text:
                    option_label = f"{g} = **{grade_text}**: *{desc_text}*"
                else:
                    option_label = f"{g} = **{grade_text}**"

                options.append(option_label)
                format_map[option_label] = g

            selected_label = st.radio(
                label=f"Valutazione {item.title}",
                options=options,
                index=(current_val if 0 <= current_val < len(options) else None),
                key=f"rad_item_{item.id}",
                disabled=disabled,
                label_visibility="collapsed"
            )

            if selected_label is None:
                selected_grade = 0
            else:
                selected_grade = format_map[selected_label]

            sheet_storage[item.id] = selected_grade


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
        
        Il paziente presentava un quadro clinico complesso (uno, più disturbi o nessuno).
        Compila la scheda completa assegnando un grado ai sintomi presenti.
        """)


def _render_dynamic_grade_selector(item: TALDItem, key_suffix: str, disabled: bool) -> int:
    """
    Render dinamico della scala 0-4 per un singlolo item.
    """
    options = []
    format_map = {}

    for g in range(5):
        raw = item.graduation.get(str(g), "").strip()

        grade_text = ""
        desc_text = ""

        if ":" in raw:
            parts = raw.split(":", 1)
            grade_text = parts[0].strip()
            desc_text = parts[1].strip()
        else:
            grade_text = raw
            desc_text = ""

        if not grade_text:
            grade_text = f"Livello {g}"

        grade_text = grade_text.capitalize()    

        if desc_text:
            option_label = f"{g} = **{grade_text}**: *{desc_text}*"
        else:
            option_label = f"{g} = **{grade_text}**"

        options.append(option_label)
        format_map[option_label] = g

    selected_label = st.radio(
        "Seleziona il grado osservato:",
        options=options,
        index=None,
        key=f"eval_grade_selector_{key_suffix}",
        disabled=disabled
    )

    if selected_label is None:
        return None

    return format_map[selected_label]


def _render_evaluation_sidebar(
    conversation: ConversationHistory,
    current_item: TALDItem,
    mode: str
) -> Optional[str]:
    """
    Sidebar con riepilogo coerente alle altre view.
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
            st.warning("**Compilazione Scheda TALD**\n\nValuta tutti i 30 item.")

        st.markdown("---")

        st.markdown("## 💡 Suggerimenti")
        st.markdown("""
        - Rivedi **mentalmente** la conversazione
        - Valuta **frequenza** manifestazioni
        - Considera **impatto** sulla comunicazione
        """)

        st.markdown("---")
        
        # Controlla se c'è warning attivo
        if st.session_state.get("confirm_back_from_eval"):
            return _render_sidebar_back_warning(mode)
        
        # Bottone normale
        label = "← Torna a Selezione Item" if mode == "guided" else "← Torna a Selezione Modalità"
        
        if st.button(label, use_container_width=True, disabled=st.session_state.eval_submitting):
            st.session_state.confirm_back_from_eval = True
            st.rerun()
    
    return None


def _render_sidebar_back_warning(mode: str) -> Optional[str]:
    """
    Renderizza il warning di conferma DENTRO la sidebar.
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
            
            # Pulizia stati locali
            keys = ['eval_error_message', 'eval_message_type', 'eval_submitting', 'exploratory_sheet']
            for k in keys:
                if k in st.session_state: del st.session_state[k]

            if mode == "guided":
                return "BACK_TO_ITEMS"
            else:
                return "RESET"
    
    return None