"""
Report View - Visualizzazione report finale

Questo modulo implementa l'interfaccia per la visualizzazione del report
finale con esito valutazione, feedback e spiegazione clinica.

Boundary del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_7, RF_8, RF_9 del RAD e mockup UI_4
"""

import streamlit as st
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.services.report_generator import Report
from src.models.evaluation import EvaluationResult


def render_report_view(report: Report) -> str:
    """
    Renderizza la view del report finale.
    
    Implementa RF_7: visualizzazione confronto automatico
    Implementa RF_8: generazione e visualizzazione report
    Implementa RF_9: esportazione report PDF
    
    Args:
        report (Report): Report completo generato da ReportGenerator
        
    Returns:
        str: Azione da intraprendere ("download_pdf", "new_simulation", "feedback", None)
        
    Example:
        >>> action = render_report_view(report)
        >>> if action == "new_simulation":
        ...     # Reset sessione e torna a mode selection
    """
    
    # CSS minimo per badge e box
    st.markdown(_get_report_css(), unsafe_allow_html=True)
    
    # Header con logo
    _render_header(report)
    
    # Breadcrumb
    mode_label = "📚 Modalità Guidata" if report.ground_truth.is_guided_mode() else "🔍 Modalità Esplorativa"
    st.markdown(f"**{mode_label}** › Intervista › Valutazione › **Report**")
    st.markdown("---")
    
    # Sidebar con statistiche
    _render_report_sidebar(report)
    
    # Metadati sessione
    _render_metadata(report)
    
    # Riepilogo valutazione (RF_7)
    _render_evaluation_summary(report)
    
    # Feedback testuale
    _render_feedback_section(report)
    
    # Spiegazione clinica (RF_8)
    _render_clinical_explanation(report)
    
    # Note utente (se presenti)
    if report.user_evaluation.notes:
        _render_user_notes(report)
    
    # Pulsanti azione
    st.markdown("---")
    action = _render_action_buttons()
    
    # Suggerimento feedback opzionale
    if action != "feedback":
        _render_feedback_prompt()
    
    return action


def _get_report_css() -> str:
    """CSS minimo per report."""
    return """
    <style>
    /* Badge risultato */
    .result-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        margin: 0.5rem 0;
    }
    
    .badge-success {
        background: #d4edda;
        color: #27ae60;
        border: 2px solid #27ae60;
    }
    
    .badge-warning {
        background: #fff3cd;
        color: #e67e22;
        border: 2px solid #e67e22;
    }
    
    .badge-error {
        background: #f8d7da;
        color: #e74c3c;
        border: 2px solid #e74c3c;
    }
    
    /* Box colorati */
    .info-box {
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid;
    }
    
    .info-box.success {
        background: #d4edda;
        border-color: #27ae60;
    }
    
    .info-box.warning {
        background: #fff3cd;
        border-color: #ffc107;
    }
    
    .info-box.error {
        background: #f8d7da;
        border-color: #e74c3c;
    }
    
    .info-box.info {
        background: #e8f4f8;
        border-color: #3498db;
    }
    
    /* Metadata */
    .metadata-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .metadata-item {
        text-align: center;
        font-size: 0.85rem;
        color: #7f8c8d;
    }
    
    .metadata-value {
        font-size: 1.2rem;
        font-weight: 700;
        color: #2c3e50;
    }
    </style>
    """


def _render_header(report: Report):
    """Renderizza header con logo e titolo."""
    header_col1, header_col2 = st.columns([1, 11])
    
    with header_col1:
        try:
            st.image("assets/taldlab_logo.png", width=60)
        except:
            st.markdown("<div style='font-size: 3rem;'>🧠</div>", unsafe_allow_html=True)
    
    with header_col2:
        # Header colorato in base a performance
        if report.result.score >= 90:
            emoji = "🎉"
            color = "#27ae60"
        elif report.result.score >= 75:
            emoji = "👍"
            color = "#3498db"
        elif report.result.score >= 60:
            emoji = "✓"
            color = "#e67e22"
        else:
            emoji = "📊"
            color = "#95a5a6"
        
        st.markdown(f"""
        <div style="margin-top: 5px;">
            <h2 style="margin: 0; color: {color};">{emoji} Simulazione Completata</h2>
            <p style="color: #7f8c8d; margin: 0; font-size: 0.9rem;">
                Report della tua esercitazione con il paziente virtuale
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("")


def _render_metadata(report: Report):
    """Renderizza metadati sessione."""
    st.markdown(f"""
    <div class="metadata-grid">
        <div class="metadata-item">
            <div>📅 Data</div>
            <div class="metadata-value">{report.timestamp.strftime("%d/%m/%Y %H:%M")}</div>
        </div>
        <div class="metadata-item">
            <div>⏱️ Durata</div>
            <div class="metadata-value">{report.conversation_summary['duration_minutes']} min</div>
        </div>
        <div class="metadata-item">
            <div>💬 Messaggi</div>
            <div class="metadata-value">{report.conversation_summary['total_messages']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_evaluation_summary(report: Report):
    """
    Renderizza riepilogo valutazione con confronto.
    
    Implementa RF_7: confronto automatico con ground truth.
    """
    st.markdown("## 📊 Riepilogo Valutazione")
    
    # Badge punteggio generale
    performance = report.result.get_performance_level()
    
    if report.result.score >= 90:
        badge_class = "badge-success"
        icon = "✅"
    elif report.result.score >= 75:
        badge_class = "badge-success"
        icon = "✓"
    elif report.result.score >= 60:
        badge_class = "badge-warning"
        icon = "⚠️"
    else:
        badge_class = "badge-error"
        icon = "❌"
    
    st.markdown(f"""
    <div style="text-align: center; margin: 1.5rem 0;">
        <div class="result-badge {badge_class}">
            {icon} Punteggio: {report.result.score}/100 - {performance}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Confronto in colonne
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 Item TALD")
        
        if report.ground_truth.is_exploratory_mode():
            # Modalità esplorativa: mostra item identificato vs reale
            if report.result.item_correct:
                st.markdown(f"""
                <div class="info-box success">
                    <strong>✅ Item identificato correttamente!</strong><br>
                    <strong>Item simulato:</strong> #{report.tald_item.id} {report.tald_item.title}<br>
                    <strong>Tua identificazione:</strong> #{report.user_evaluation.item_id}
                </div>
                """, unsafe_allow_html=True)
            else:
                # Trova item identificato dall'utente
                from src.services.configuration_service import ConfigurationService
                user_item = ConfigurationService.get_item_by_id(
                    st.session_state.get('tald_items', []),
                    report.user_evaluation.item_id
                )
                
                st.markdown(f"""
                <div class="info-box error">
                    <strong>❌ Item non corretto</strong><br>
                    <strong>Item simulato:</strong> #{report.tald_item.id} {report.tald_item.title}<br>
                    <strong>Tua identificazione:</strong> #{user_item.id if user_item else '?'} {user_item.title if user_item else 'Sconosciuto'}
                </div>
                """, unsafe_allow_html=True)
        else:
            # Modalità guidata: item noto
            st.markdown(f"""
            <div class="info-box info">
                <strong>Item simulato:</strong><br>
                #{report.tald_item.id} {report.tald_item.title}<br>
                <em>Tipo: {report.tald_item.type.capitalize()}</em>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📏 Grado Manifestazione")
        
        if report.result.grade_correct:
            st.markdown(f"""
            <div class="info-box success">
                <strong>✅ Grado corretto!</strong><br>
                <strong>Grado simulato:</strong> {report.ground_truth.grade}/4<br>
                <strong>Tua valutazione:</strong> {report.user_evaluation.grade}/4
            </div>
            """, unsafe_allow_html=True)
        else:
            diff = report.result.grade_difference
            direction = "sovrastimato" if report.user_evaluation.grade > report.ground_truth.grade else "sottostimato"
            
            box_class = "warning" if diff == 1 else "error"
            
            st.markdown(f"""
            <div class="info-box {box_class}">
                <strong>{"⚠️" if diff == 1 else "❌"} Grado {direction}</strong><br>
                <strong>Grado simulato:</strong> {report.ground_truth.grade}/4<br>
                <strong>Tua valutazione:</strong> {report.user_evaluation.grade}/4<br>
                <strong>Differenza:</strong> {diff} {'punto' if diff == 1 else 'punti'}
            </div>
            """, unsafe_allow_html=True)


def _render_feedback_section(report: Report):
    """Renderizza feedback testuale."""
    st.markdown("---")
    st.markdown("## 💬 Feedback")
    
    st.info(report.result.feedback_message)


def _render_clinical_explanation(report: Report):
    """
    Renderizza spiegazione clinica.
    
    Implementa RF_8: spiegazione clinica dei segnali linguistici.
    """
    st.markdown("---")
    st.markdown("## 🧠 Spiegazione Clinica")
    
    with st.expander("📖 **Clicca per leggere l'analisi dettagliata dei segnali linguistici osservati**", expanded=True):
        st.markdown(report.clinical_explanation)
        
        st.markdown("---")
        st.markdown("### 📋 Ground Truth Completo")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            **Item simulato:**  
            #{report.tald_item.id} - {report.tald_item.title}
            
            **Tipo:**  
            {report.tald_item.type.capitalize()}
            
            **Grado configurato:**  
            {report.ground_truth.grade}/4
            """)
        
        with col2:
            st.markdown(f"""
            **Descrizione grado:**  
            {report.tald_item.get_grade_description(report.ground_truth.grade)}
            
            **Modalità:**  
            {report.ground_truth.mode.capitalize()}
            """)


def _render_user_notes(report: Report):
    """Renderizza note utente se presenti."""
    st.markdown("---")
    st.markdown("## 📝 Le Tue Note")
    
    st.markdown(f"""
    <div class="info-box warning">
        <strong>Osservazioni personali:</strong><br>
        <em>"{report.user_evaluation.notes}"</em>
    </div>
    """, unsafe_allow_html=True)


def _render_action_buttons() -> str:
    """
    Renderizza pulsanti azione finale.
    
    Returns:
        str: Azione scelta ("download_pdf", "new_simulation", None)
    """
    st.markdown("---")
    st.markdown("## 🎯 Prossimi Passi")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(
            "📥 Scarica Report PDF",
            use_container_width=True,
            type="secondary",
            key="download_pdf_btn"
        ):
            return "download_pdf"
    
    with col2:
        if st.button(
            "🔄 Avvia Nuova Simulazione",
            use_container_width=True,
            type="primary",
            key="new_simulation_btn"
        ):
            return "new_simulation"
    
    return None


def _render_feedback_prompt():
    """Renderizza suggerimento feedback opzionale."""
    st.markdown("")
    
    st.markdown("""
    <div style="background: #f8f9fa; border: 2px dashed #bdc3c7; padding: 1.5rem; 
                border-radius: 8px; text-align: center; margin-top: 2rem;">
        <h3 style="color: #2c3e50; margin-bottom: 0.5rem; font-size: 1.1rem;">
            💬 Aiutaci a migliorare
        </h3>
        <p style="color: #7f8c8d; margin-bottom: 1rem; font-size: 0.9rem;">
            Valuta la tua esperienza con questa simulazione (opzionale e anonimo)
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Compila Feedback", use_container_width=True, key="feedback_btn"):
        return "feedback"


def _render_report_sidebar(report: Report):
    """Renderizza sidebar con info aggiuntive."""
    with st.sidebar:
        st.markdown("## 📊 Dettagli Report")
        
        # Performance level con colore
        performance = report.result.get_performance_level()
        
        if report.result.score >= 90:
            color = "#27ae60"
        elif report.result.score >= 75:
            color = "#3498db"
        elif report.result.score >= 60:
            color = "#e67e22"
        else:
            color = "#95a5a6"
        
        st.markdown(f"""
        <div style="background: {color}; color: white; padding: 1rem; 
                    border-radius: 8px; text-align: center; margin-bottom: 1rem;">
            <div style="font-size: 2rem; font-weight: bold;">{report.result.score}</div>
            <div style="font-size: 0.9rem;">/ 100</div>
            <div style="margin-top: 0.5rem; font-size: 0.85rem; opacity: 0.9;">{performance}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Statistiche conversazione
        st.markdown("### 💬 Statistiche Conversazione")
        
        st.metric("Messaggi totali", report.conversation_summary['total_messages'])
        st.metric("Parole scambiate", report.conversation_summary['total_words'])
        st.metric("Durata", f"{report.conversation_summary['duration_minutes']} min")
        
        st.markdown("---")
        
        # Info modalità
        st.markdown("### ℹ️ Info Simulazione")
        
        mode_emoji = "📚" if report.ground_truth.is_guided_mode() else "🔍"
        mode_label = "Guidata" if report.ground_truth.is_guided_mode() else "Esplorativa"
        
        st.info(f"""
        **Modalità:** {mode_emoji} {mode_label}
        
        **Data:** {report.timestamp.strftime("%d/%m/%Y")}
        
        **Ora:** {report.timestamp.strftime("%H:%M")}
        """)


def handle_pdf_download(report: Report):
    """
    Gestisce il download del report in PDF.
    
    Implementa RF_9: esportazione report in PDF.
    """
    from src.services.report_generator import ReportGenerator
    
    try:
        # Genera testo formattato del report
        report_generator = ReportGenerator(None)  # Non serve LLM per export
        report_text = report_generator.format_report_text(report)
        
        # Offri download come file di testo (placeholder PDF)
        filename = f"TALDLab_Report_{report.timestamp.strftime('%Y%m%d_%H%M%S')}.txt"
        
        st.download_button(
            label="⬇️ Scarica Report (TXT)",
            data=report_text,
            file_name=filename,
            mime="text/plain",
            use_container_width=True,
            key="download_txt"
        )
        
        st.info("""
        ℹ️ **Export PDF in sviluppo**
        
        Per ora il report viene esportato in formato testo (.txt).
        L'implementazione completa del PDF richiede la libreria ReportLab.
        """)
        
    except Exception as e:
        st.error(f"Errore durante l'export: {e}")