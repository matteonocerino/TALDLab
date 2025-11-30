"""
Report View - Visualizzazione report finale

Questo modulo implementa l'interfaccia utente (Boundary) per la visualizzazione 
del report finale della simulazione. Mostra i risultati del confronto, 
la spiegazione clinica generata dall'AI e fornisce opzioni di export.

Boundary del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_7, RF_8, RF_9 del RAD e mockup UI_4
"""

import streamlit as st
import os
import base64
import re

from src.utils import scroll_to_top
from src.services.report_generator import Report


def _format_clinical_html(text: str) -> str:
    """
    Pulisce il testo dell'AI per la visualizzazione Web:
    - Rimuove titoli duplicati
    - Converte i titoli Markdown (#) in grassetto semplice (evita scritte giganti)
    - Converte grassetto e corsivo in HTML
    """
    if not text: return ""
    
    # 1. Rimuovi righe vuote iniziali
    text = text.strip()

    # 2. Rimuovi la prima riga SE è una ripetizione del titolo "Analisi Clinica..."
    # (Cerca pattern che iniziano con #, ** o nulla, seguiti da "Analisi" o "Report")
    text = re.sub(r'^(#|\*| )*(Analisi|Report).*?\n', '', text, flags=re.IGNORECASE, count=1)

    # Rimuovi di nuovo gli spazi vuoti iniziali rimasti dopo aver tolto il titolo
    text = text.strip()

    # 3. NORMALIZZAZIONE TITOLI (Il fix per le scritte giganti)
    # Trasforma QUALSIASI titolo Markdown (#, ##, ###) in semplice Grassetto HTML + a capo.
    text = re.sub(r'#{1,6}\s*(.*?)(?:\n|$)', r'<br><strong>\1</strong><br>', text)

    # 4. Gestione grassetto standard (**Testo**) -> <strong>
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # 5. Gestione corsivo (*Testo*) -> <em>
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    
    # 6. Gestione a capo (Newlines -> <br>)
    text = text.replace('\n', '<br>')
    
    return text


def render_report_view(report: Report) -> str:
    """
    Renderizza la schermata del report finale.
    
    Costruisce l'interfaccia completa con header, sidebar, riepiloghi 
    allineati e azioni finali.
    
    Args:
        report (Report): L'oggetto Report contenente tutti i dati della sessione.
        
    Returns:
        str: L'azione successiva scelta dall'utente ("new_simulation", "feedback", None).
    """

    # Forza scroll in alto all'apertura della pagina
    scroll_to_top("report-top-marker")
    
    # 1. Header e Brand
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
            <div class="brand-title">Report Finale</div>
            <div class="brand-sub">Risultati della simulazione clinica</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    mode_label = "🎯 Modalità Guidata" if report.ground_truth.is_guided_mode() else "🔍 Modalità Esplorativa"
    
    if report.ground_truth.is_guided_mode():
        breadcrumb = f'<p class="breadcrumb">{mode_label} › Selezione Item › Intervista › Valutazione › <strong>Report</strong></p>'
    else:
        breadcrumb = f'<p class="breadcrumb">{mode_label} › Intervista › Valutazione › <strong>Report</strong></p>'

    st.markdown(breadcrumb, unsafe_allow_html=True)
    st.markdown("---")

    _render_report_sidebar(report)

    # 2. Banner Esito
    _render_score_banner(report)

    # 3. Riepilogo Confronto 
    st.markdown("### 📊 Riepilogo Valutazione") 
    st.markdown("") 

    # Due colonne principali per separare i blocchi
    col_item_card, col_grade_card = st.columns(2, gap="large")
    
    # === CARD SINISTRA: ITEM TALD ===
    with col_item_card:
        i1, i2 = st.columns(2)
        with i1:
            # ITEM REALE
            _render_fixed_height_text("ITEM REALE", f"<b>{report.tald_item.id}. {report.tald_item.title}</b>")
        with i2:
            # ITEM UTENTE
            if report.ground_truth.is_exploratory_mode():
                chosen_id = report.user_evaluation.item_id
                all_items = st.session_state.get('tald_items', [])
                chosen_item = next((i for i in all_items if i.id == chosen_id), None)

                if chosen_item:
                    user_text = f"<b>{chosen_item.id}. {chosen_item.title}</b>"
                else:
                    user_text = f"<b>ID {chosen_id}</b>"

                _render_fixed_height_text("TUA IDENTIFICAZIONE", user_text, align="right")
            else:
                _render_fixed_height_text("TUA IDENTIFICAZIONE", "<em>(Già noto)</em>", align="right")
    
        # Box Esito 
        if report.ground_truth.is_exploratory_mode():
            if report.result.item_correct:
                st.success("✅ Identificazione **CORRETTA**")
            else:
                st.error("❌ Identificazione **ERRATA**")
        else:
            st.info("ℹ️ Modalità Guidata (Item noto)")

    # === CARD DESTRA: GRADO ===
    with col_grade_card:
        g1, g2 = st.columns(2)
        with g1:
            # GRADO REALE
            _render_fixed_height_text("GRADO REALE", f"<b>{report.ground_truth.grade} / 4</b>")
        with g2:
            # GRADO UTENTE
            _render_fixed_height_text("TUO GRADO", f"<b>{report.user_evaluation.grade} / 4</b>", align="right")

        # Box Esito (Allineato geometricamente con quello di sinistra)
        if report.result.grade_correct:
            st.success("✅ Attribuzione **CORRETTA**")
        else:
            diff = report.result.grade_difference
            msg = f"Scostamento: {diff}"
            if diff == 1:
                st.warning(f"⚠️ **IMPRECISA** ({msg})")
            else:
                st.error(f"❌ **ERRATA** ({msg})")

    st.markdown("---")

    # 4. Spiegazione Clinica
    st.markdown("## 🩺 Analisi Clinica")
    st.caption("Analisi generata dall'AI basata sui pattern linguistici emersi nella conversazione.")
    
    # Puliamo il testo con la funzione helper
    html_content = _format_clinical_html(report.clinical_explanation)
    
    with st.container(border=True):
        # Usiamo unsafe_allow_html=True per far interpretare i tag <strong> e <br>
        st.markdown(html_content, unsafe_allow_html=True)

    if report.result.feedback_message:
        st.info(f"💡 **Feedback Didattico:** {report.result.feedback_message}")

    # 5. Note Personali
    if report.user_evaluation.notes:
        st.markdown("---")
        st.markdown("### 📝 Le tue note")
        st.markdown(f"> *{report.user_evaluation.notes}*")

    # 6. Azioni Finali
    st.markdown("---")

    c1, c2 = st.columns(2, gap="medium")
    
    with c1:
        handle_pdf_download(report)
            
    with c2:
        if st.button("🔄 Nuova Simulazione", type="primary", use_container_width=True):
            return "new_simulation"

    # 7. SEZIONE FEEDBACK APP (Box Dedicato)
    st.markdown("") 
    st.markdown("") 
    
    # Creiamo un container visivo nativo con bordo
    _, _, c3, _, _ = st.columns([1, 0.1, 1.5, 0.1, 1])
    
    with c3:
        with st.container(border=True):
            st.markdown(
                """
                <div style="text-align: center;">
                    <h4 style="margin-top: 0; margin-bottom: 0.5rem;">👋 Aiutaci a migliorare!</h4>
                    <p style="font-size: 0.9rem; opacity: 0.8; margin-bottom: 1rem;">
                        Il tuo parere è fondamentale per lo sviluppo di questo progetto. 
                        Valuta l'esperienza in modo anonimo.
                    </p>
                </div>
                """, 
                unsafe_allow_html=True
            )

            if st.button("💬 Lascia un Feedback", use_container_width=True):
                return "feedback"
            
    st.markdown("") 
            
    return None


def _render_fixed_height_text(label: str, value: str, align: str = "left", height: str = "130px"):
    """
    Helper per renderizzare un blocco di testo con altezza minima fissa.
    Garantisce l'allineamento orizzontale dei box sottostanti.
    """
    st.markdown(
        f"""
        <div style="min-height: {height}; display: flex; flex-direction: column; justify-content: flex-start; text-align: {align};">
            <div style="color: gray; font-size: 0.8rem; margin-bottom: 4px; text-transform: uppercase;">{label}</div>
            <div style="font-size: 1rem;"><strong>{value}</strong></div>
        </div>
        """,
        unsafe_allow_html=True
    )
    

def _render_report_sidebar(report: Report):
    """
    Renderizza la sidebar con layout verticale.
    """
    with st.sidebar:
        # Sezione Esito
        st.markdown("## 🏆 Esito Sessione")
        
        if report.result.score >= 60:
            score_color = "#27ae60" 
        elif report.result.score >= 40:
            score_color = "#e67e22" 
        else:
            score_color = "#e74c3c" 

        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 1rem;">
            <span style="font-size: 3rem; font-weight: bold; color: {score_color};">{report.result.score}</span>
            <span style="font-size: 1.2rem; color: #666;">/ 100</span>
        </div>
        """, unsafe_allow_html=True)
        
        level = report.result.get_performance_level()
        st.markdown(f"""
        <div style="text-align: center; font-size: 1.1rem; margin-bottom: 1.5rem; opacity: 0.9;">
            Livello: <strong>{level}</strong>
        </div>
        """, unsafe_allow_html=True)
            
        st.markdown("---")
        
        # Sezione Dettagli
        st.markdown("## ℹ️ Dettagli Sessione")
        
        mode_icon = "🎯" if report.ground_truth.is_guided_mode() else "🔍"
        mode_text = "Guidata" if report.ground_truth.is_guided_mode() else "Esplorativa"
        
        st.info(f"""
        **Modalità:** {mode_icon} {mode_text}
        
        **Data:** {report.timestamp.strftime('%d/%m/%Y')}
        """)
        
        st.markdown("---")
        
        # Sezione Statistiche
        st.markdown("## 💬 Statistiche Chat")
        
        c1, c2 = st.columns(2)
        with c1: 
            st.metric("Messaggi", report.conversation_summary['total_messages'])
        with c2: 
            st.metric("Minuti", f"{report.conversation_summary['duration_minutes']}")
        
        st.caption(f"Parole scambiate: {report.conversation_summary['total_words']}")


def _render_score_banner(report: Report):
    """Renderizza il banner colorato col punteggio finale."""
    score = report.result.score
    level = report.result.get_performance_level()
    
    # Logica Colori a 3 livelli
    if score >= 60:
        # SUCCESSO (Verde)
        bg_color = "rgba(39, 174, 96, 0.9)" 
        icon = "✅"
        title = "Ottimo Lavoro!" if score >= 80 else "Esercitazione Superata"
        
    elif score >= 40:
        # MIGLIORABILE (Arancio/Giallo scuro) - Per chi prende 50
        bg_color = "rgba(230, 126, 34, 0.9)" 
        icon = "⚠️"
        title = "Esercitazione Migliorabile"
        
    else:
        # INSUFFICIENTE (Rosso) - Per chi prende 0
        bg_color = "rgba(192, 57, 43, 0.9)" 
        icon = "❌"
        title = "Esercitazione Non Superata"
    
    st.markdown(f"""
    <div style="
        background-color: {bg_color}; 
        padding: 1.5rem; 
        border-radius: 10px; 
        color: #f8f9fa; 
        text-align: center; 
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="color: #ffffff; margin:0; font-size: 1.8rem; font-weight: 700;">{icon} {title}</h2>
        <div style="font-size: 1.2rem; margin-top: 0.5rem;">
            Punteggio: <strong>{score}/100</strong> <span style="opacity:0.9; font-size: 1rem;">({level})</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def handle_pdf_download(report: Report):
    """Gestisce la generazione e il download del PDF."""
    try:
        with st.spinner("📄 Generazione documento PDF..."):
            generator = st.session_state.report_generator

           # RECUPERA LA LISTA ITEM DALLO STATO
            all_items = st.session_state.get('tald_items', [])
            
            # PASSALA AL GENERATORE
            pdf_bytes = generator.export_pdf_to_bytes(report, all_items=all_items)
            
            filename = f"TALDLab_Report_{report.timestamp.strftime('%Y%m%d_%H%M')}.pdf"
            
            st.download_button(
                label="📥 Scarica PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
                type="secondary",
                key="btn_download_report_pdf"
            )
            
    except Exception as e:
        st.error(f"❌ Errore PDF: {str(e)}")        