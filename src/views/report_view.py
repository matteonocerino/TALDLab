"""
Report View - Visualizzazione report finale

Questo modulo implementa l'interfaccia utente (Boundary) per la visualizzazione 
del report finale della simulazione. 

Gestisce la presentazione dei risultati:
- In Modalità Guidata: confronto puntuale su un singolo item (come da mockup UI_4).
- In Modalità Esplorativa: visualizzazione dettagliata delle metriche vettoriali 
  (Veri Positivi, Falsi Negativi, Falsi Positivi).

Boundary del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_8 del RAD (Visualizzazione Report) e RF_9 (Export PDF)
"""

import streamlit as st
import os
import base64
import re
import html
from typing import List

from src.utils import scroll_to_top
from src.services.report_generator import Report
from src.models.tald_item import TALDItem


def _format_clinical_html(text: str) -> str:
    """
    Pulisce il testo dell'AI per la visualizzazione Web.
    Supporta due livelli di liste (Categorie * e Dettagli -).
    """
    if not text:
        return ""
    
    text = text.strip().replace('\r\n', '\n')
    lines = text.split('\n')

    html_buffer = []
    
    # Stati per gestire la chiusura corretta dei tag
    in_list_lvl1 = False
    in_list_lvl2 = False

    color_primary = "var(--text-color-primary)"
    redundant_titles = ["Report clinico", "Analisi clinica", "Trascrizione"]

    for line in lines:
        raw_line = line.rstrip()
        if not raw_line.strip():
            continue

        s_line = raw_line.strip()

        # Filtro titoli ridondanti
        if any(rt.lower() in s_line.lower() for rt in redundant_titles) and len(s_line) < 60:
            continue

        s_line = re.sub(r'\*+$', '', s_line)

        # 1. TITOLI (###)
        if s_line.startswith('#') or (len(s_line) > 0 and s_line[0].isdigit() and '. ' in s_line[:5]):
            # Chiudiamo tutte le liste aperte prima di un nuovo titolo
            if in_list_lvl2:
                html_buffer.append("</ul>")
                in_list_lvl2 = False
            if in_list_lvl1:
                html_buffer.append("</ul>")
                in_list_lvl1 = False

            clean_title = re.sub(r'^[\#\d\.]+\s*', '', s_line).strip()
            html_buffer.append(
                f'<div style="font-size: 1.3rem; font-weight: 700; '
                f'margin-top: 1.2rem; margin-bottom: 0.8rem; '
                f'border-bottom: 1px solid #ddd; padding-bottom: 5px; '
                f'color: {color_primary};">{clean_title}</div>'
            )
            continue

        # 2. LISTA LIVELLO 1 (Categorie con *)
        if s_line.startswith('* '):
            # Se eravamo dentro una sottolista (livello 2), la chiudiamo
            if in_list_lvl2:
                html_buffer.append("</ul>")
                in_list_lvl2 = False
            
            # Se non eravamo in una lista livello 1, la apriamo
            if not in_list_lvl1:
                html_buffer.append('<ul style="margin-top: 0.5rem; margin-bottom: 0.5rem; padding-left: 1.2rem; list-style-type: disc;">')
                in_list_lvl1 = True

            clean = re.sub(r'^\*\s+', '', s_line)
            # Rimuoviamo i due punti finali per pulizia se presenti
            clean = clean.rstrip(':')
            
            # Grassetto per le categorie
            html_buffer.append(f'<li style="font-weight: 600; margin-top: 8px; color: var(--text-color);">{html.escape(clean)}</li>')
            continue

        # 3. LISTA LIVELLO 2 (Dettagli con -)
        if s_line.startswith('- '):
            # Se non siamo ancora nel livello 2, apriamo la sottolista
            if not in_list_lvl2:
                # Nota: padding-left maggiore per indentare a destra
                html_buffer.append('<ul style="margin-top: 0.2rem; margin-bottom: 0.5rem; padding-left: 2.5rem; list-style-type: circle;">')
                in_list_lvl2 = True
            
            clean = re.sub(r'^\-\s+', '', s_line)
            # Gestione grassetto interno se presente
            clean = html.escape(clean)
            clean = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', clean)

            html_buffer.append(f'<li style="line-height: 1.6; margin-bottom: 4px;">{clean}</li>')
            continue

        # 4. TESTO NORMALE
        # Chiudiamo liste se incontriamo testo normale
        if in_list_lvl2:
            html_buffer.append("</ul>")
            in_list_lvl2 = False
        if in_list_lvl1:
            html_buffer.append("</ul>")
            in_list_lvl1 = False

        clean = html.escape(s_line)
        clean = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', clean)
        html_buffer.append(
            f'<p style="margin-top: 0.5rem; margin-bottom: 0.5rem; line-height: 1.6;">{clean}</p>'
        )

    # Chiusura finale sicura
    if in_list_lvl2:
        html_buffer.append("</ul>")
    if in_list_lvl1:
        html_buffer.append("</ul>")

    return "\n".join(html_buffer)


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
    _render_header()
    
    # Breadcrumb dinamico in base alla modalità
    mode_label = "🎯 Modalità Guidata" if report.ground_truth.is_guided_mode() else "🔍 Modalità Esplorativa"
    
    if report.ground_truth.is_guided_mode():
        breadcrumb = f'<p class="breadcrumb">{mode_label} › Selezione Item › Intervista › Valutazione › <strong>Report</strong></p>'
    else:
        breadcrumb = f'<p class="breadcrumb">{mode_label} › Intervista › Valutazione › <strong>Report</strong></p>'

    st.markdown(breadcrumb, unsafe_allow_html=True)
    st.markdown("---")

    # Sidebar con riepilogo
    _render_report_sidebar(report)

    # 2. Banner Esito (Punteggio)
    _render_score_banner(report)

    # 3. Riepilogo Confronto (Sezione principale)
    st.markdown("## 📊 Riepilogo Valutazione") 
    st.markdown("") 

    # Recuperiamo la lista item per risolvere gli ID in Nomi
    all_items = st.session_state.get('tald_items', [])

    # Logica di visualizzazione differenziata (RF_8)
    if report.ground_truth.is_guided_mode():
        _render_guided_comparison(report)
    else:
        _render_exploratory_comparison(report, all_items)

    st.markdown("---")

    # 4. Spiegazione Clinica (Generata da AI)
    st.markdown("## 🩺 Analisi Clinica")
    st.caption("Analisi generata dall'Intelligenza Artificiale basata sui pattern linguistici emersi.")
    
    html_content = _format_clinical_html(report.clinical_explanation)
    
    with st.container(border=True):
        st.markdown(html_content, unsafe_allow_html=True)

    # FEEDBACK TESTUALE: Lo nascondiamo in un expander perché è ridondante visivamente
    if report.result.feedback_message:
        with st.expander("📄 Dettagli testuali (Riepilogo)", expanded=False):
            st.info(report.result.feedback_message)

    # 5. Note Personali Utente
    if report.user_evaluation.notes:
        st.markdown("---")
        st.markdown("## 📝 Le tue note")
        st.markdown(f"> *{report.user_evaluation.notes}*")

    # 6. Azioni Finali
    st.markdown("---")

    c1, c2 = st.columns(2, gap="medium")
    
    with c1:
        # Gestione download PDF
        handle_pdf_download(report, all_items)
            
    with c2:
        if st.button("🔄 Nuova Simulazione", type="primary", use_container_width=True):
            return "new_simulation"

    # 7. Box Feedback (Call to Action)
    st.markdown("") 
    st.markdown("") 
    _, _, c3, _, _ = st.columns([1, 0.1, 1.5, 0.1, 1])
    
    with c3:
        with st.container(border=True):
            st.markdown(
                """
                <div style="text-align: center;">
                    <h4 style="margin-top: 0; margin-bottom: 0.5rem;">👋 Aiutaci a migliorare!</h4>
                    <p style="font-size: 0.9rem; opacity: 0.8; margin-bottom: 1rem;">
                        Il tuo parere è fondamentale per la validazione del prototipo.
                    </p>
                </div>
                """, 
                unsafe_allow_html=True
            )

            if st.button("💬 Lascia un Feedback", use_container_width=True):
                return "feedback"
            
    st.markdown("") 
            
    return None


def _render_guided_comparison(report: Report):
    """
    Renderizza il confronto per la Modalità Guidata.
    """
    # Recupero dati
    _, gt_grade = report.ground_truth.get_primary_item()
    user_grade = report.user_evaluation.get_grade_for_item(report.tald_item.id)
    diff = abs(gt_grade - user_grade)

    # Logica Colori e Testi
    if diff == 0:
        outcome_val = "CORRETTO"
        outcome_color = "#27ae60" # Verde 
        icon = "✅"
        delta_txt = None
        delta_color = None
    else:
        if diff == 1:
            outcome_val = "IMPRECISO"
            outcome_color = "#e67e22" # Arancio
            icon = "⚠️"
            delta_txt = f"{icon} SCARTO: {diff}"
            delta_color = outcome_color
        else:
            outcome_val = "ERRATO"
            outcome_color = "#e74c3c" # Rosso
            icon = "❌"
            delta_txt = None
            delta_color = None

    # --- FUNZIONE HELPER PER CREARE METRICHE ---
    def _metric_html(label, value, value_color=None, sub_text=None, sub_color="gray"):
        color_style = f"color: {value_color};" if value_color else "color: var(--text-color);"
        
        return f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding-bottom: 12px;">
            <div style="font-size: 0.8rem; opacity: 0.7; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">{label}</div>
            <div style="font-size: 1.6rem; font-weight: 700; {color_style} line-height: 1.2;">{value}</div>
            <div style="font-size: 0.85rem; color: {sub_color}; margin-top: 4px; font-weight: 500;">{sub_text if sub_text else '&nbsp;'}</div>
        </div>
        """

    # --- RENDERING ---
    with st.container(border=True):
        
        # 1. Intestazione
        st.markdown(
            f'<div style="font-size: 1.3rem; color: var(--text-color);"><b>{report.tald_item.id}.</b> {report.tald_item.title}</div>', 
            unsafe_allow_html=True
        )

        st.markdown("---")

        # 2. Le 3 Metriche Centrate
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown(_metric_html("Grado Reale", f"{gt_grade}/4"), unsafe_allow_html=True)

        with c2:
            st.markdown(_metric_html("Tuo Grado", f"{user_grade}/4"), unsafe_allow_html=True)

        with c3:
            st.markdown(_metric_html("Esito", outcome_val, outcome_color, delta_txt, delta_color), unsafe_allow_html=True)


def _render_exploratory_comparison(report: Report, all_items: List[TALDItem]):
    """
    Renderizza il confronto per la Modalità Esplorativa (Design a Schede).
    """
    
    # Helper locale
    def get_item_name(iid):
        found = next((i for i in all_items if i.id == iid), None)
        return f"{found.id}. {found.title}" if found else f"ID {iid}"

    tp = report.result.true_positives
    fn = report.result.false_negatives
    fp = report.result.false_positives

    # --- 2. GESTIONE CASO "PAZIENTE SANO" ---
    if not report.ground_truth.active_items:
        if not fp:
            st.success("🌟 **DIAGNOSI PERFETTA:** Il paziente virtuale era SANO e tu non hai rilevato disturbi.")
            return 
        else:
            st.error(f"⚠️ **ATTENZIONE:** Il paziente virtuale era SANO (Nessun disturbo), ma tu ne hai segnalati {len(fp)}.")

    # --- 3. DETTAGLI A SCHEDE ---
    label_successi = f"✅ Successi ({len(tp)})"
    label_omissioni = f"❌ Omissioni ({len(fn)})"
    label_falsi = f"⚠️ Falsi Allarmi ({len(fp)})"

    tab1, tab2, tab3 = st.tabs([label_successi, label_omissioni, label_falsi])

    # TAB 1: VERI POSITIVI
    with tab1:
        if tp:
            for iid in tp:
                name = get_item_name(iid)
                real_g = report.ground_truth.active_items.get(iid, 0)
                user_g = report.user_evaluation.evaluation_sheet.get(iid, 0)
                diff = abs(real_g - user_g)
                
                # Scegliamo colore e icona in base alla precisione del grado
                if diff == 0:
                    icon = "✅"
                    msg_type = st.success
                    sub_msg = "CORRETTO"
                else:
                    icon = "⚠️"
                    msg_type = st.warning
                    sub_msg = f"IMPRECISO (SCARTO: {diff})"

                # Card personalizzata
                with st.container(border=True):
                    c_name, c_real, c_user, c_res = st.columns([3, 1, 1, 2.5])
                    with c_name:
                        st.markdown(f"**{name}**")
                    with c_real:
                        st.caption("Reale")
                        st.markdown(f"**{real_g}/4**")
                    with c_user:
                        st.caption("Tuo")
                        st.markdown(f"**{user_g}/4**")
                    with c_res:
                        msg_type(f"{icon} {sub_msg}")

        else:
            if report.ground_truth.active_items: 
                st.error("Nessun disturbo identificato correttamente.")
            else:
                st.info("Nessun disturbo presente da identificare.")

    # TAB 2: OMISSIONI
    with tab2:
        if fn:
            for iid in fn:
                name = get_item_name(iid)
                gt_g = report.ground_truth.active_items.get(iid, 0)
                
                with st.container(border=True):
                    c_name, c_real, c_msg = st.columns([3, 2, 2.5])
                    with c_name:
                        st.markdown(f"**{name}**")
                    with c_real:
                        st.caption("Reale")
                        st.markdown(f"**{gt_g}/4**")
                    with c_msg:
                        st.error("❌ OMESSO")
        else:
            st.success("Ottimo! Non hai mancato nessun disturbo presente.")

    # TAB 3: FALSI ALLARMI
    with tab3:
        if fp:
            for iid in fp:
                name = get_item_name(iid)
                user_g = report.user_evaluation.evaluation_sheet.get(iid, 0)
                
                with st.container(border=True):
                    c_name, c_user, c_msg = st.columns([3, 2, 2.5])
                    with c_name:
                        st.markdown(f"**{name}**")
                    with c_user:
                        st.caption("Tuo Voto")
                        st.markdown(f"**{user_g}/4**")
                    with c_msg:
                        st.error("⚠️ NON PRESENTE")
        else:
            st.success("Ottimo! Non hai segnalato disturbi inesistenti.")
    

def _render_report_sidebar(report: Report):
    """
    Renderizza la sidebar con layout verticale e statistiche.
    """
    with st.sidebar:
        # Sezione Esito
        st.markdown("## 🏆 Esito Sessione")
        
        score = report.result.score
        # Colore dinamico punteggio
        if score >= 60: score_color = "#27ae60" 
        elif score >= 40: score_color = "#e67e22" 
        else: score_color = "#e74c3c" 

        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 1rem;">
            <span style="font-size: 3rem; font-weight: bold; color: {score_color};">{score}</span>
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
        
        # Sezione Statistiche Chat
        st.markdown("## 💬 Statistiche Chat")
        
        c1, c2 = st.columns(2)
        with c1: 
            st.metric("Messaggi", report.conversation_summary['total_messages'])
        with c2: 
            st.metric("Minuti", f"{report.conversation_summary['duration_minutes']}")
        
        st.caption(f"Parole scambiate: {report.conversation_summary['total_words']}")


def _render_score_banner(report: Report):
    """
    Renderizza il banner colorato col punteggio finale.
    """
    score = report.result.score
    level = report.result.get_performance_level()
    
    # Logica Colori Originale 
    if score >= 60:
        # SUCCESSO
        bg_color = "rgba(39, 174, 96, 0.9)" 
        icon = "✅"
        title = "Ottimo Lavoro!" if score >= 80 else "Esercitazione Superata"
        
    elif score >= 40:
        # MIGLIORABILE
        bg_color = "rgba(230, 126, 34, 0.9)" 
        icon = "⚠️"
        title = "Esercitazione Migliorabile"
        
    else:
        # INSUFFICIENTE
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


def _render_header():
    """Renderizza header con logo."""
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
            <div class="brand-title">Report Finale</div>
            <div class="brand-sub">Risultati della simulazione clinica</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def handle_pdf_download(report: Report, all_items: List[TALDItem]):
    """Gestisce la generazione e il download del PDF."""
    try:
        with st.spinner("📄 Generazione documento PDF..."):
            generator = st.session_state.report_generator
            
            # Generazione binaria
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