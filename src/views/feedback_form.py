"""
Feedback Form View - Form feedback qualitativo opzionale

Questo modulo implementa l'interfaccia per la raccolta di feedback
anonimizzato sulla qualità della simulazione.

Boundary del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_10 del RAD
"""

import streamlit as st
from typing import Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.services.feedback_service import FeedbackService


def render_feedback_form(
    item_id: int,
    item_title: str,
    mode: str,
    score: int
) -> bool:
    """
    Renderizza il form di feedback opzionale.
    
    Implementa RF_10: raccolta e persistenza feedback anonimizzato.
    
    Args:
        item_id (int): ID item simulato (per metadata)
        item_title (str): Titolo item (per metadata)
        mode (str): "guided" o "exploratory"
        score (int): Punteggio ottenuto (per metadata)
        
    Returns:
        bool: True se feedback inviato o saltato (procedi), False altrimenti
        
    Example:
        >>> completed = render_feedback_form(
        ...     item_id=5,
        ...     item_title="Crosstalk",
        ...     mode="guided",
        ...     score=100
        ... )
        >>> if completed:
        ...     # Torna a mode selection o fine
    """
    
    # CSS minimo per stelle
    st.markdown(_get_feedback_css(), unsafe_allow_html=True)
    
    # Header con logo
    _render_header()
    
    # Breadcrumb
    st.markdown("**Report** › **Feedback (opzionale)**")
    st.markdown("---")
    
    # Intro
    _render_intro()
    
    # Form feedback
    with st.form(key="feedback_form", clear_on_submit=False):
        
        st.markdown("### 📊 Valutazioni (opzionali)")
        st.caption("Lascia vuoto se preferisci non rispondere")
        
        # Rating 1: Overall
        st.markdown("**Valutazione generale dell'esperienza**")
        overall_rating = st.select_slider(
            "Quanto ti è piaciuta l'esperienza complessiva?",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: "⭐" * x,
            label_visibility="collapsed",
            key="overall"
        )
        
        st.markdown("")
        
        # Rating 2: Realism
        st.markdown("**Realismo della simulazione**")
        realism_rating = st.select_slider(
            "Quanto realistico era il paziente virtuale?",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: "⭐" * x,
            label_visibility="collapsed",
            key="realism"
        )
        
        st.markdown("")
        
        # Rating 3: Usefulness
        st.markdown("**Utilità didattica percepita**")
        usefulness_rating = st.select_slider(
            "Quanto utile è stato per il tuo apprendimento?",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: "⭐" * x,
            label_visibility="collapsed",
            key="usefulness"
        )
        
        st.markdown("---")
        
        # Commenti liberi
        st.markdown("### 💬 Commenti e Suggerimenti (opzionali)")
        comments = st.text_area(
            "Condividi le tue osservazioni:",
            height=120,
            placeholder="Es: Il paziente era molto realistico, soprattutto nelle intrusioni. "
                       "Forse potrebbe essere utile avere più item da esplorare...",
            label_visibility="collapsed",
            key="comments"
        )
        
        st.caption("💡 I tuoi commenti ci aiutano a migliorare TALDLab")
        
        st.markdown("---")
        
        # Pulsanti
        col1, col2 = st.columns(2)
        
        with col1:
            skip_button = st.form_submit_button(
                "⏭️ Salta Feedback",
                use_container_width=True
            )
        
        with col2:
            submit_button = st.form_submit_button(
                "✅ Invia Feedback",
                use_container_width=True,
                type="primary"
            )
    
    # Gestione skip
    if skip_button:
        st.info("👍 Va bene, nessun problema! Grazie per aver usato TALDLab.")
        return True
    
    # Gestione submit
    if submit_button:
        return _handle_feedback_submit(
            overall_rating=overall_rating,
            realism_rating=realism_rating,
            usefulness_rating=usefulness_rating,
            comments=comments,
            item_id=item_id,
            item_title=item_title,
            mode=mode,
            score=score
        )
    
    return False


def _get_feedback_css() -> str:
    """CSS minimo per feedback form."""
    return """
    <style>
    .info-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
    }
    
    .info-banner h3 {
        margin: 0 0 0.5rem 0;
        font-size: 1.3rem;
    }
    
    .info-banner p {
        margin: 0;
        font-size: 0.95rem;
        opacity: 0.95;
    }
    </style>
    """


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
            <h2 style="margin: 0; color: #2c3e50;">💬 Feedback sulla Simulazione</h2>
            <p style="color: #7f8c8d; margin: 0; font-size: 0.9rem;">
                Aiutaci a migliorare TALDLab (completamente opzionale e anonimo)
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("")


def _render_intro():
    """Renderizza intro esplicativa."""
    st.markdown("""
    <div class="info-banner">
        <h3>🙏 Il tuo parere è importante</h3>
        <p>Questo feedback è completamente <strong>anonimo</strong> e ci aiuta a validare 
        il prototipo e migliorare l'esperienza formativa. Tutti i campi sono opzionali.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("")


def _handle_feedback_submit(
    overall_rating: int,
    realism_rating: int,
    usefulness_rating: int,
    comments: str,
    item_id: int,
    item_title: str,
    mode: str,
    score: int
) -> bool:
    """
    Gestisce submit del feedback.
    
    Usa FeedbackService per validare e salvare in feedback_log.json.
    """
    # Verifica che almeno un campo sia compilato
    has_ratings = (overall_rating is not None or 
                   realism_rating is not None or 
                   usefulness_rating is not None)
    has_comments = comments and comments.strip()
    
    if not has_ratings and not has_comments:
        st.warning("""
        ⚠️ **Nessun feedback fornito**
        
        Compila almeno una valutazione o aggiungi un commento, 
        oppure clicca "Salta Feedback" per continuare.
        """)
        return False
    
    try:
        # Prepara dati feedback
        feedback_data = {
            "overall_rating": overall_rating,
            "realism_rating": realism_rating,
            "usefulness_rating": usefulness_rating,
            "comments": comments.strip() if comments else ""
        }
        
        # Prepara metadata anonimizzati
        metadata = {
            "item_id": item_id,
            "item_title": item_title,
            "mode": mode,
            "score": score
        }
        
        # Salva feedback
        FeedbackService.save_feedback(feedback_data, metadata)
        
        # Successo
        st.success("""
        ✅ **Grazie per il tuo feedback!**
        
        Il tuo contributo è stato salvato e ci aiuterà a migliorare TALDLab.
        """)
        
        # Mostra statistiche aggregate (se disponibili)
        _show_aggregate_stats()
        
        return True
    
    except Exception as e:
        st.error(f"""
        ❌ **Errore nel salvataggio del feedback**
        
        {str(e)}
        
        Puoi comunque continuare cliccando "Salta Feedback".
        """)
        return False


def _show_aggregate_stats():
    """Mostra statistiche aggregate feedback (opzionale)."""
    try:
        stats = FeedbackService.get_feedback_statistics()
        
        if stats['count'] > 0:
            st.markdown("---")
            st.markdown("### 📊 Statistiche Aggregate")
            st.caption(f"Basate su {stats['count']} feedback raccolti finora")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if stats['average_ratings']['overall']:
                    st.metric(
                        "Overall medio",
                        f"{stats['average_ratings']['overall']:.1f}/5",
                        help="Valutazione generale media"
                    )
            
            with col2:
                if stats['average_ratings']['realism']:
                    st.metric(
                        "Realismo medio",
                        f"{stats['average_ratings']['realism']:.1f}/5",
                        help="Realismo simulazione medio"
                    )
            
            with col3:
                if stats['average_ratings']['usefulness']:
                    st.metric(
                        "Utilità media",
                        f"{stats['average_ratings']['usefulness']:.1f}/5",
                        help="Utilità didattica media"
                    )
    
    except Exception:
        # Se fallisce, non mostrare nulla (non è critico)
        pass


def render_feedback_sidebar():
    """Renderizza sidebar con info feedback."""
    with st.sidebar:
        st.markdown("## 💬 Info Feedback")
        
        st.info("""
        **Cosa raccogliamo:**
        - Valutazioni 1-5 (opzionali)
        - Commenti liberi (opzionali)
        - Metadati anonimi (item, modalità, score)
        
        **Cosa NON raccogliamo:**
        - Nome o email
        - Dati identificativi
        - Storico conversazioni
        """)
        
        st.markdown("---")
        
        st.markdown("## 🔒 Privacy")
        
        st.success("""
        ✅ **100% Anonimo**
        
        Nessun dato personale viene salvato.
        Il feedback è utilizzato solo per validare il prototipo.
        """)
        
        st.markdown("---")
        
        st.markdown("## ℹ️ Perché è importante?")
        
        st.markdown("""
        I tuoi feedback ci aiutano a:
        - Validare il prototipo
        - Migliorare il realismo
        - Identificare bug
        - Pubblicare ricerca scientifica
        """)


def show_feedback_skip_confirmation() -> bool:
    """
    Mostra dialog conferma per saltare feedback.
    
    Returns:
        bool: True se utente conferma di saltare
    """
    st.warning("""
    ⚠️ **Vuoi davvero saltare il feedback?**
    
    Ci vogliono solo 30 secondi e ci aiuteresti molto!
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Compila Feedback", use_container_width=True):
            return False
    
    with col2:
        if st.button("Salta →", use_container_width=True, type="secondary"):
            return True
    
    return False