"""
Feedback Form View - Form feedback qualitativo avanzato

Questo modulo implementa l'interfaccia per la raccolta dati di validazione.
Visualizza i 5 quesiti specifici richiesti per la tesi (S1-S4 + Commenti)
utilizzando un layout a griglia responsive.

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
) -> object:
    """
    Renderizza la dashboard di feedback post-simulazione.
    
    Raccoglie valutazioni su 4 dimensioni specifiche (Scala Likert 1-5):
    - Accuratezza Punteggio
    - Qualità Spiegazione
    - Soddisfazione Generale
    - Realismo Simulazione
    
    Returns: 
        bool: True se l'utente ha completato o saltato il feedback (flusso terminato).
        str: "back_to_report" se l'utente vuole rivedere il report.
    """
    
    # --- GESTIONE STATO ---
    if "fb_submission_status" not in st.session_state:
        st.session_state.fb_submission_status = "pending"

    # Forza scroll in alto all'apertura della pagina
    scroll_to_top("feedback-top-marker")

    # 1. Header Standard
    _render_header()
    
    # 2. Sidebar con riepilogo contesto
    _render_sidebar(item_id, item_title, mode, score)
    
    # Breadcrumb di navigazione
    mode_label = "🎯 Modalità Guidata" if mode == "guided" else "🔍 Modalità Esplorativa"
    
    if mode == "guided":
        breadcrumb = f'<p class="breadcrumb">{mode_label} › Selezione Item › Intervista › Valutazione › Report › <strong>Feedback</strong></p>'
    else:
        breadcrumb = f'<p class="breadcrumb">{mode_label} › Intervista › Valutazione › Report › <strong>Feedback</strong></p>'

    st.markdown(breadcrumb, unsafe_allow_html=True)
    st.markdown("---")
    
    is_disabled = st.session_state.fb_submission_status != "pending"
    
    # 3. Area Feedback - Introduzione
    st.markdown("## 📊 Questionario di Validazione")
    if is_disabled:
        if st.session_state.fb_submission_status == "submitted":
            st.caption("🔒 Feedback inviato. Grazie per il tuo contributo.")
    else:
        st.caption("Per favore valuta i seguenti aspetti della simulazione (1 = Minimo, 5 = Massimo).")
    st.markdown("")

    # --- GRIGLIA DI VALUTAZIONE (S1 - S4) ---
    
    # RIGA 1: Aspetti Tecnici (S1, S2)
    c1, c2 = st.columns(2, gap="large")
    
    with c1:
        st.markdown("#### 🎯 Accuratezza Punteggio")
        st.markdown("Il punteggio TALD assegnato riflette accuratamente la performance del paziente?")
        s1_val = st.feedback("stars", key="fb_s1_input", disabled=is_disabled)
        _render_rating_label(s1_val, color="#2980b9") # Blu

    with c2:
        st.markdown("#### 🩺 Qualità Spiegazione")
        st.markdown("La spiegazione fornita dimostra competenza clinica e giustifica il punteggio?")
        s2_val = st.feedback("stars", key="fb_s2_input", disabled=is_disabled)
        _render_rating_label(s2_val, color="#2980b9") # Blu

    st.markdown("---") 

    # RIGA 2: Esperienza Utente (S3, S4)
    c3, c4 = st.columns(2, gap="large")

    with c3:
        st.markdown("#### ⭐ Soddisfazione")
        st.markdown("Sei soddisfatto della qualità e chiarezza complessiva dell'analisi?")
        s3_val = st.feedback("stars", key="fb_s3_input", disabled=is_disabled)
        _render_rating_label(s3_val, color="#27ae60") # Verde

    with c4:
        st.markdown("#### 🎭 Realismo")
        st.markdown("Il paziente virtuale è stato simulato in modo realistico rispetto a un caso vero?")
        s4_val = st.feedback("faces", key="fb_s4_input", disabled=is_disabled)
        _render_rating_label(s4_val, color="#8e44ad", is_faces=True) # Viola

    st.markdown("---")

    # --- CAMPO TESTUALE ---
    st.markdown("#### 📝 Commenti Qualitativi (Opzionale)")
    comments = st.text_area(
        "Punti di forza, debolezza o suggerimenti:",
        placeholder="Es: La simulazione del deragliamento era molto convincente, ma...",
        height=100,
        label_visibility="collapsed",
        key="fb_comments_input",
        disabled=is_disabled
    )

    st.markdown("---")
    
    # === FOOTER DINAMICO (Gestione Stati) ===
    
    # FASE 1: IN ATTESA DI INVIO (PENDING)
    if st.session_state.fb_submission_status == "pending":
        
        col_privacy, col_actions = st.columns([1, 1])
        
        with col_privacy:
            st.markdown("<div style='padding-top: 10px;'>", unsafe_allow_html=True)
            st.caption("🔒 **Dato Anonimo:** Il feedback viene salvato per fini statistici senza riferimenti all'utente.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_actions:
            # Placeholder per messaggi di errore (sopra i bottoni)
            error_container = st.empty()
            
            b_skip, b_send = st.columns(2)

            with b_skip:
                st.button("⏭️ Salta", use_container_width=True, on_click=_skip_callback)

            with b_send:
                if st.button("✅ Invia Feedback", use_container_width=True, type="primary"):
                    # Normalizzazione valori (da 0-4 a 1-5 per il DB)
                    v1 = (s1_val + 1) if s1_val is not None else None
                    v2 = (s2_val + 1) if s2_val is not None else None
                    v3 = (s3_val + 1) if s3_val is not None else None
                    v4 = (s4_val + 1) if s4_val is not None else None
                    
                    # Validazione: Almeno un campo deve essere compilato
                    if not any([v1, v2, v3, v4, comments.strip()]):
                        error_container.warning("⚠️ Compila almeno una valutazione o inserisci un commento.")
                    else:
                        # Chiamata al Service per il salvataggio
                        success = _process_submission(
                            v1, v2, v3, v4, comments, 
                            item_id, item_title, mode, score
                        )
                        if success:
                            st.session_state.fb_submission_status = "submitted"
                            st.session_state.fb_just_submitted = True # Flag per animazione
                            st.rerun()

    # FASE 2: FEEDBACK CHIUSO (Inviato o Saltato)
    else:
        st.markdown("")
        _, center_col, _ = st.columns([1, 2, 1])
            
        with center_col:
            # Caso A: Appena inviato con successo
            if st.session_state.fb_submission_status == "submitted":

                if st.session_state.get("fb_just_submitted"):
                    st.balloons()
                    del st.session_state["fb_just_submitted"]
                
                with st.container(border=True):
                    st.success("✅ **Feedback registrato.** Grazie per il contributo.")
                    st.caption("Non è possibile inviare nuovi dati per questa sessione.")
                    st.markdown("")

                    # Bottoni normali (Torna al report lascia lo stato Submitted)
                    b_report, b_new = st.columns(2)
                    with b_report:
                        if st.button("⬅️ Rivedi Report", use_container_width=True):
                            return "back_to_report"
                    with b_new:
                        if st.button("🔄 Nuova Simulazione", type="primary", use_container_width=True):
                            del st.session_state.fb_submission_status
                            return True    

            # Caso B: Saltato dall'utente
            elif st.session_state.fb_submission_status == "skipped":
                with st.container(border=True):
                    st.info("ℹ️ **Feedback saltato.** La sessione è conclusa.")
                    st.caption("Hai scelto di non inviare dati per questa sessione.")  
                    st.markdown("") 

                    b_report, b_new = st.columns(2)
                    with b_report:
                        if st.button("⬅️ Rivedi Report", use_container_width=True):
                            st.session_state.fb_submission_status = "pending"
                            return "back_to_report"
                    with b_new:
                        if st.button("🔄 Nuova Simulazione", type="primary", use_container_width=True):
                            del st.session_state.fb_submission_status
                            return True  
                    
    return False


def _skip_callback():
    """
    Callback eseguita al click di 'Salta'.
    Gestisce la modifica dello stato e la pulizia dei widget in sicurezza.
    """
    # 1. Imposta lo stato su skipped
    st.session_state.fb_submission_status = "skipped"
    # 2. Pulisce i campi per estetica (così se rientra li trova vuoti)
    _clear_form_inputs()

    
def _clear_form_inputs():
    """Pulisce i widget di input per resettare il form."""
    keys = ["fb_s1_input", "fb_s2_input", "fb_s3_input", "fb_s4_input", "fb_comments_input"]
    for k in keys:
        if k in st.session_state:
            st.session_state[k] = None


def _render_rating_label(value, color, is_faces=False):
    """Visualizza un'etichetta testuale sotto le stelle/faccine."""
    if value is not None:
        if is_faces:
            labels = ["Molto Artificiale", "Poco Realistico", "Neutro", "Realistico", "Molto Naturale"]
            text = labels[value]
        else:
            text = f"{value + 1} / 5"
            
        st.markdown(f"<div style='text-align: center; color: {color}; font-size: 1.0rem; font-weight: 600; margin-top: 5px;'>{text}</div>", unsafe_allow_html=True)
    else:
        # Spazio vuoto per mantenere l'allineamento delle card
        st.markdown("<div style='height: 29px;'></div>", unsafe_allow_html=True)


def _render_sidebar(item_id, item_title, mode, score):
    """Popola la sidebar con i dettagli della sessione."""
    with st.sidebar:
        st.markdown("## 📋 Oggetto Valutazione")

        if mode == "guided":
            content = f"**Item:** {item_id}. {item_title}"
            st.info(f"**Modalità Guidata**\n\n{content}", icon="🎯")
        else:
            # In esplorativa usiamo il titolo generico passato dal controller 
            st.warning(f"**Modalità Esplorativa**\n\n{item_title}", icon="🔍")
        
        if score >= 60:
            st.success(f"**Esito:** Superato ({score}/100)", icon="✅")
        elif score >= 40:
            st.warning(f"**Esito:** Migliorabile ({score}/100)", icon="⚠️")
        else:
            st.error(f"**Esito:** Non Superato ({score}/100)", icon="❌")
            
        st.markdown("---")
        st.markdown("## ℹ️ Info Ricerca")
        st.caption("I dati raccolti servono a validare l'accuratezza clinica del modello LLM nel simulare i disturbi TALD.")
        st.markdown("---")
        st.markdown("## 🔒 Privacy & Dati")
        st.caption("""
        - **Anonimato:** No IP/Email.
        - **Storage:** Locale (JSON).
        """)
        st.markdown("---")
        st.caption("Progetto TALDLab 2025")


def _process_submission(s1, s2, s3, s4, comments, item_id, item_title, mode, score):
    """Prepara il payload e invia al service."""
    fb_data = {
        "score_accuracy": s1,
        "explanation_quality": s2,
        "overall_satisfaction": s3,
        "simulation_realism": s4,
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
    """Header standard con logo."""
    logo_path = os.path.join("assets", "taldlab_logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            b64_logo = base64.b64encode(f.read()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{b64_logo}" alt="Logo" />'
    else:
        logo_html = '<div class="emoji-fallback">🧠</div>'

    st.markdown(f"""
    <div class="brand">
        {logo_html}
        <div class="brand-text-container">
            <div class="brand-title">Validazione Prototipo</div>
            <div class="brand-sub">Raccolta dati per progetto di ricerca sperimentale</div>
        </div>
    </div>
    """, unsafe_allow_html=True)