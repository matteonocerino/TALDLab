"""
Feedback Form View - Form feedback qualitativo avanzato

Questo modulo implementa l'interfaccia per la raccolta dati di validazione.
Gestisce l'allineamento avanzato (Flexbox) nella sidebar per i testi lunghi
e corregge il posizionamento dei messaggi di errore nel footer.

Boundary del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_10 del RAD
"""

import streamlit as st
import os
import base64

from src.utils import scroll_to_top
from src.services.feedback_service import FeedbackService


def render_feedback_form(
    item_id: int,
    item_title: str,
    mode: str,
    score: int
) -> bool:
    """
    Renderizza la dashboard di feedback post-simulazione.
    Returns: bool (True se concluso).
    """
    
    # --- GESTIONE STATO ---
    if "fb_submission_status" not in st.session_state:
        st.session_state.fb_submission_status = "pending"

    # Forza scroll in alto all'apertura della pagina
    scroll_to_top("feedback-top-marker")

    # 2. Header
    _render_header()
    
    # 3. Sidebar
    _render_sidebar(item_id, item_title, mode, score)
    
    # Breadcrumb
    mode_label = "🎯 Modalità Guidata" if mode == "guided" else "🔍 Modalità Esplorativa"
    
    if mode == "guided":
        # In guidata mostriamo lo step "Selezione Item"
        breadcrumb = f'<p class="breadcrumb">{mode_label} › Selezione Item › Intervista › Valutazione › Report › <strong>Feedback</strong></p>'
    else:
        # In esplorativa saltiamo direttamente all'Intervista
        breadcrumb = f'<p class="breadcrumb">{mode_label} › Intervista › Valutazione › Report › <strong>Feedback</strong></p>'

    st.markdown(breadcrumb, unsafe_allow_html=True)
    st.markdown("---")
    
    is_disabled = st.session_state.fb_submission_status != "pending"
    
    # 4. Area Feedback
    st.markdown("### 📊 Valutazione Sperimentale")
    if is_disabled:
        st.caption("🔒 Sessione chiusa. Grazie per il tuo contributo.")
    else:
        st.caption("Valuta i parametri chiave per la validazione del modello.")
    st.markdown("")

    # LAYOUT CARD
    c1, c2, c3 = st.columns(3, gap="medium")
    
    with c1:
        with st.container(border=True):
            st.markdown("#### 🗣️ Realismo")
            st.caption("Coerenza clinica delle risposte")
            realism = st.feedback("faces", key="fb_realism_input", disabled=is_disabled)
            if realism is not None:
                labels = ["Molto Artificiale", "Poco Realistico", "Neutro", "Realistico", "Molto Naturale"]
                st.markdown(f"<div style='text-align: center; color: #6c5ce7; font-size: 1.1rem; font-weight: 600; margin-top: 5px;'>{labels[realism]}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

    with c2:
        with st.container(border=True):
            st.markdown("#### 🎓 Efficacia")
            st.caption("Utilità per l'apprendimento")
            usefulness = st.feedback("stars", key="fb_usefulness_input", disabled=is_disabled)
            if usefulness is not None:
                st.markdown(f"<div style='text-align: center; color: #e67e22; font-size: 1.1rem; font-weight: 600; margin-top: 5px;'>{usefulness + 1} / 5</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

    with c3:
        with st.container(border=True):
            st.markdown("#### ⭐ Generale")
            st.caption("Esperienza d'uso complessiva")
            overall = st.feedback("stars", key="fb_overall_input", disabled=is_disabled)
            if overall is not None:
                st.markdown(f"<div style='text-align: center; color: #27ae60; font-size: 1.1rem; font-weight: 600; margin-top: 5px;'>{overall + 1} / 5</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

    st.markdown("") 

    st.markdown("#### 📝 Note Qualitative (Opzionale)")
    comments = st.text_area(
        "Segnala incongruenze o suggerimenti:",
        placeholder="Es: Il comportamento verbale era coerente, ma...",
        height=100,
        label_visibility="collapsed",
        key="fb_comments_input",
        disabled=is_disabled
    )

    st.markdown("---")
    
    # === FOOTER DINAMICO ===
    
    # FASE 1: PENDING
    if st.session_state.fb_submission_status == "pending":
        
        col_privacy, col_actions = st.columns([1, 1])
        
        with col_privacy:
            st.markdown("<div style='padding-top: 10px;'>", unsafe_allow_html=True)
            st.caption("🔒 **Dato Anonimo:** Il feedback viene salvato per fini statistici senza riferimenti all'utente.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_actions:
            # Placeholder per errori a larghezza intera (sopra i bottoni)
            error_container = st.empty()
            
            b_skip, b_send = st.columns(2)
            with b_skip:
                st.button(
                    "⏭️ Salta", 
                    use_container_width=True, 
                    on_click=_skip_feedback_callback
                )

            with b_send:
                if st.button("✅ Invia", use_container_width=True, type="primary"):
                    # Logica di validazione inline per controllare dove mostrare l'errore
                    val_overall = (overall + 1) if overall is not None else None
                    val_realism = (realism + 1) if realism is not None else None
                    val_usefulness = (usefulness + 1) if usefulness is not None else None
                    
                    if not any([val_overall, val_realism, val_usefulness, comments]):
                        # MOSTRA ERRORE NEL CONTAINER LARGO
                        error_container.warning("⚠️ Compila almeno una valutazione o inserisci un commento.")
                    else:
                        # Procedi al salvataggio
                        success = _process_submission(overall, realism, usefulness, comments, item_id, item_title, mode, score)
                        if success:
                            st.session_state.fb_submission_status = "submitted"
                            # Flag per mostrare i palloncini SOLO ora
                            st.session_state.fb_just_submitted = True
                            st.rerun()

    # FASE 2: BLOCCATO (Già Inviato o Saltato)
    else:
        st.markdown("")
        _, center_col, _ = st.columns([1, 2, 1])
            
        with center_col:
            # Caso A: Inviato
            if st.session_state.fb_submission_status == "submitted":

                # Palloncini SOLO la prima volta
                if st.session_state.get("fb_just_submitted"):
                    st.balloons()
                    del st.session_state["fb_just_submitted"] # Reset flag
                
                with st.container(border=True):
                    # Messaggio di stato finale
                    st.success("✅ **Feedback registrato.** Grazie per il contributo.")
                    st.caption("Non è possibile inviare nuovi dati per questa sessione.")
                    
                    st.markdown("")
                        
                    # Bottoni Navigazione
                    b_report, b_new = st.columns(2)
                    with b_report:
                        if st.button("⬅️ Rivedi Report", use_container_width=True):
                            return "back_to_report"
                    with b_new:
                        if st.button("🔄 Nuova Simulazione", type="primary", use_container_width=True):
                            del st.session_state.fb_submission_status
                            return True

            # Caso B: Saltato
            elif st.session_state.fb_submission_status == "skipped":
                with st.container(border=True):
                    st.info("ℹ️ **Feedback saltato.** La sessione è conclusa.")
                    st.caption("Hai scelto di non inviare dati per questa sessione.")

                    st.markdown("")   
                        
                    b_report, b_new = st.columns(2)
                    with b_report:
                        if st.button("⬅️ Rivedi Report", use_container_width=True):
                            del st.session_state.fb_submission_status
                            return "back_to_report"
                    with b_new:
                        if st.button("🔄 Nuova Simulazione", type="primary", use_container_width=True):
                            del st.session_state.fb_submission_status
                            return True
    return False


def _skip_feedback_callback():
    """
    Callback per il tasto Salta.
    Pulisce i widget PRIMA del rerun.
    """
    st.session_state.fb_submission_status = "skipped"
    
    keys_to_reset = ["fb_realism_input", "fb_usefulness_input", "fb_overall_input"]
    for key in keys_to_reset:
        if key in st.session_state:
            st.session_state[key] = None
    
    if "fb_comments_input" in st.session_state:
        st.session_state["fb_comments_input"] = ""


def _render_sidebar(item_id, item_title, mode, score):
    """
    Popola la sidebar con i dettagli della sessione corrente.
    Usa i box nativi di Streamlit (st.info/st.warning).
    """
    with st.sidebar:
        # 1. Dettagli Sessione
        st.markdown("## 📋 Oggetto Valutazione")
        
        content = f"**Item:** {item_id}. {item_title}"
        
        if mode == "guided":
            # Modalità Guidata -> BLU
            st.info(f"**Modalità Guidata**\n\n{content}", icon="🎯")
        else:
            # Modalità Esplorativa -> GIALLO
            st.warning(f"**Modalità Esplorativa**\n\n{content}", icon="🔍") 
        
        # 2. ESITO
        if score >= 60:
            st.success(f"**Esito:** Superato ({score}/100)", icon="✅")
        elif score >= 40:
            st.warning(f"**Esito:** Migliorabile ({score}/100)", icon="⚠️")
        else:
            st.error(f"**Esito:** Non Superato ({score}/100)", icon="❌")
            
        st.markdown("---")

        # 3. Info Ricerca
        st.markdown("## ℹ️ Info Ricerca")
        st.caption("I dati raccolti servono a validare l'accuratezza clinica del modello LLM nel simulare i disturbi TALD.")
        
        st.markdown("---")
        st.markdown("## 🔒 Privacy & Dati")
        st.caption("""
        - **Anonimato:** No IP/Email.
        - **Storage:** Locale (JSON).
        """)
        
        st.markdown("---")
        st.caption("Progetto TALDLab 2024")


def _process_submission(overall, realism, usefulness, comments, item_id, item_title, mode, score):
    """Prepara i dati e chiama il service (la validazione UI è fatta prima)."""
    
    # Mapping
    val_overall = (overall + 1) if overall is not None else None
    val_realism = (realism + 1) if realism is not None else None
    val_usefulness = (usefulness + 1) if usefulness is not None else None

    if not any([val_overall, val_realism, val_usefulness, comments]):
        return False
    
    fb_data = {
        "overall_rating": val_overall,
        "realism_rating": val_realism,
        "usefulness_rating": val_usefulness,
        "comments": comments
    }
    
    metadata = {
        "item_id": item_id,
        "item_title": item_title,
        "mode": mode,
        "score": score
    }

    try:
        FeedbackService.save_feedback(fb_data, metadata)
        return True
    except Exception as e:
        st.error(f"❌ **Errore tecnico nel salvataggio**: {e}")
        return False


def _render_header():
    """Renderizza l'header standard."""
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
            <div class="brand-title">Validazione Prototipo</div>
            <div class="brand-sub">Raccolta dati per progetto di ricerca sperimentale</div>
        </div>
    </div>
    """, unsafe_allow_html=True)