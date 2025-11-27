"""
ReportGenerator - Servizio per generazione report finali

Questo modulo è responsabile della creazione, formattazione ed esportazione
dei report finali delle simulazioni. Aggrega i dati provenienti da diverse
fonti (valutazione utente, ground truth, storico conversazione) e produce
un output strutturato.

Responsabilità principali:
- Aggregazione dati per il report finale (Entity 'Report')
- Generazione spiegazioni cliniche (tramite LLM o fallback statico)
- Esportazione del report in formato PDF professionale (ReportLab) direttamente in memoria

Control del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_8, RF_9 del RAD
"""

import os
import re
from datetime import datetime
from typing import Optional
from io import BytesIO 

# ReportLab imports per generazione PDF reale
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether

from src.models.evaluation import UserEvaluation, GroundTruth, EvaluationResult
from src.models.conversation import ConversationHistory
from src.models.tald_item import TALDItem
from src.services.llm_service import LLMService


class Report:
    """
    Rappresenta il report finale di una simulazione.
    
    Entity che aggrega tutti i dati necessari per la visualizzazione e l'export.
    Viene creato dal ReportGenerator al termine della fase di valutazione.
    
    Attributes:
        ground_truth (GroundTruth): Configurazione reale della simulazione (item/grado).
        user_evaluation (UserEvaluation): Valutazione inserita dall'utente.
        result (EvaluationResult): Esito del confronto (punteggi, correttezza).
        clinical_explanation (str): Analisi testuale generata (AI o statica).
        conversation_summary (dict): Metriche della conversazione (durata, messaggi).
        tald_item (TALDItem): Dettagli completi dell'item TALD simulato.
        timestamp (datetime): Momento di generazione del report.
    """
    
    def __init__(
        self,
        ground_truth: GroundTruth,
        user_evaluation: UserEvaluation,
        result: EvaluationResult,
        clinical_explanation: str,
        conversation_summary: dict,
        tald_item: TALDItem,
        timestamp: Optional[datetime] = None
    ):
        self.ground_truth = ground_truth
        self.user_evaluation = user_evaluation
        self.result = result
        self.clinical_explanation = clinical_explanation
        self.conversation_summary = conversation_summary
        self.tald_item = tald_item
        self.timestamp = timestamp or datetime.now()


class ReportGenerator:
    """
    Service per la gestione della logica di reporting.
    
    Incapsula la logica di business per trasformare i dati grezzi della sessione
    in un documento clinico strutturato. Gestisce anche l'interazione con
    LLMService per l'analisi qualitativa.
    """
    
    def __init__(self, llm_service: LLMService):
        """
        Inizializza il generatore.
        
        Args:
            llm_service (LLMService): Riferimento al servizio LLM per generare spiegazioni.
        """
        self.llm_service = llm_service
    
    def generate_report(
        self,
        ground_truth: GroundTruth,
        user_evaluation: UserEvaluation,
        result: EvaluationResult,
        conversation: ConversationHistory,
        tald_item: TALDItem
    ) -> Report:
        """
        Genera l'oggetto Report completo.
        
        Esegue i seguenti passaggi:
        1. Tenta di generare una spiegazione clinica tramite LLM.
        2. In caso di errore LLM, attiva il fallback statico (dati JSON).
        3. Calcola le statistiche finali della conversazione.
        4. Aggrega tutto nell'entità Report.
        
        Implementa RF_8 (Generazione report).
        
        Args:
            ground_truth: La verità di base della simulazione.
            user_evaluation: L'input dell'utente.
            result: Il risultato calcolato dal ComparisonEngine.
            conversation: Lo storico completo dei messaggi.
            tald_item: L'item TALD oggetto della simulazione.
            
        Returns:
            Report: L'oggetto report popolato.
        """
        # 1. Generazione spiegazione clinica (con gestione Fallback)
        try:
            # Tentativo principale: Analisi AI tramite Gemini
            clinical_explanation = self.llm_service.generate_clinical_explanation(
                tald_item=tald_item,
                conversation_history=conversation,
                grade=ground_truth.grade
            )
        except Exception:
            # Fallback intelligente: Se l'IA non è disponibile (es. quota esaurita, offline),
            # generiamo comunque un report utile usando i dati statici del manuale.
            clinical_explanation = self._generate_basic_explanation(tald_item, ground_truth.grade)
        
        # 2. Calcolo metriche conversazione
        conversation_summary = {
            "total_messages": conversation.get_message_count(),
            "duration_minutes": conversation.get_duration_minutes(),
            "total_words": conversation.get_total_words(),
            "user_messages": len(conversation.get_user_messages()),
            "assistant_messages": len(conversation.get_assistant_messages())
        }
        
        # 3. Creazione Entity Report
        return Report(
            ground_truth=ground_truth,
            user_evaluation=user_evaluation,
            result=result,
            clinical_explanation=clinical_explanation,
            conversation_summary=conversation_summary,
            tald_item=tald_item
        )

    def _generate_basic_explanation(self, tald_item: TALDItem, grade: int) -> str:
        """
        Genera una spiegazione clinica base usando i dati statici (Fallback).
        
        Viene utilizzata quando il servizio LLM non è raggiungibile per garantire
        che il report contenga comunque informazioni didattiche utili provenienti
        dal manuale TALD.
        
        Args:
            tald_item: L'item TALD.
            grade: Il grado simulato.
            
        Returns:
            str: Testo formattato con descrizione e criteri.
        """
        grade_desc = tald_item.get_grade_description(grade)
        
        explanation = f"""**Nota:** Questa è una spiegazione generata dai dati statici (LLM non disponibile al momento).

**Item TALD simulato:** {tald_item.title}

**Descrizione del disturbo:**
{tald_item.description}

**Criteri diagnostici:**
{tald_item.criteria}

**Grado manifestato:** {grade}/4 - {grade_desc}

**Esempio tipico:**
{tald_item.example}
"""
        return explanation
    
    def _clean_markdown_for_pdf(self, text: str) -> str:
        """
        Converte il Markdown base (**, ##, *) in tag XML compatibili con ReportLab.
        """
        if not text: return ""

        # 1. Rimuovi eventuali titoli Markdown (## Titolo) e falli diventare grassetto + a capo
        # Sostituisce "## Titolo" con "<b>Titolo</b><br/>"
        text = re.sub(r'#{2,}\s*(.*?)(?:\n|$)', r'<b>\1</b><br/>', text)

        # 2. Converti grassetto: **Testo** -> <b>Testo</b>
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

        # 3. Converti corsivo: *Testo* -> <i>Testo</i>
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)

        # 4. Gestione elenchi puntati (simulati con <br/> e bullet char)
        text = text.replace('\n- ', '<br/>• ')
        
        # 5. Gestione a capo standard
        text = text.replace('\n', '<br/>')

        return text
    
    def _parse_ai_response_to_flowables(self, text: str, style_normal, style_title) -> list:
        """
        Spezza il testo dell'AI in paragrafi distinti per gestire correttamente
        i salti pagina. Riconosce i titoli e applica keepWithNext.
        """
        flowables = []
        if not text: return flowables
        
        # 1. Normalizziamo e dividiamo per righe
        text = text.replace('\r\n', '\n')
        lines = text.split('\n')
        
        # Flag per saltare il primissimo titolo se ridondante
        first_line_processed = False

        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Se è la prima riga significativa E sembra un titolo ripetuto, lo saltiamo.
            if not first_line_processed:
                # Regex che cerca "Analisi", "Report", "Clinica" all'inizio
                if re.match(r'^(#|\*| )*(Analisi|Report|Colloquio|Disturbo)', line, re.IGNORECASE):
                    first_line_processed = True
                    continue # SALTA QUESTA RIGA (non la scrive nel PDF)
                first_line_processed = True
            
            # 2. Rileviamo se è un sottotitolo
            # Criteri: inizia con ** o ## o numeri puntati grassettati (es. "1. **...")
            is_title = False
            if line.startswith('##') or line.startswith('**') or (len(line) > 0 and line[0].isdigit() and '**' in line[:10]):
                is_title = True
            
            # 3. Pulizia Markdown (usiamo logica simile a clean_markdown)
            clean_text = line
            clean_text = re.sub(r'^#{2,}\s*', '', clean_text) # Via i ##
            clean_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean_text) # Grassetto
            clean_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', clean_text) # Corsivo
            
            # 4. Creazione Oggetto
            if is_title:
                # TITOLO: Usa lo stile apposito che ha keepWithNext=True
                flowables.append(Paragraph(clean_text, style_title))
            else:
                # TESTO: Stile normale
                flowables.append(Paragraph(clean_text, style_normal))
                # Aggiungiamo un piccolo spazio dopo ogni paragrafo di testo
                flowables.append(Spacer(1, 0.2*cm))
                
        return flowables
    
    def export_pdf_to_bytes(self, report: Report, all_items: list[TALDItem] = None) -> BytesIO:
        """
        Genera il PDF direttamente in memoria (buffer BytesIO).
        
        Questo metodo permette il download immediato del file tramite Streamlit
        senza dover salvare file temporanei sul disco del server, migliorando
        sicurezza e performance.
        
        Implementa RF_9 (Esportazione PDF).
        
        Args:
            report (Report): Il report da esportare.
            
        Returns:
            BytesIO: Buffer contenente i dati binari del PDF, pronto per il download.
        """
        buffer = BytesIO()
        
        # Setup Documento PDF (Margini A4 standard)
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm,
            title="TALDLab Report"
        )
        
        # --- Definizione Stili (ReportLab Styles) ---
        styles = getSampleStyleSheet()
        
        # Stile Titolo Principale
        style_title = ParagraphStyle(
            'TALDTitle', 
            parent=styles['Heading1'], 
            alignment=TA_LEFT, 
            fontSize=22, 
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=2,
            leading=28 # Aumentato per spaziare
        )
        
        # Stile Sottotitolo
        style_subtitle = ParagraphStyle(
            'TALDSub', 
            parent=styles['Normal'], 
            alignment=TA_LEFT, 
            fontSize=13, 
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=6,
            leading=16 # Aumentato per spaziare
        )
        
        # Stile Data
        style_date = ParagraphStyle(
            'TALDDate',
            parent=styles['Normal'],
            alignment=TA_LEFT,
            fontSize=10,
            textColor=colors.black,
            leading=12
        )

        # Stile Intestazioni Sezioni (H2) con sfondo grigio chiaro
        style_h2 = ParagraphStyle(
            'TALDH2', 
            parent=styles['Heading2'], 
            fontSize=14, 
            spaceBefore=12, 
            spaceAfter=6,
            textColor=colors.HexColor('#34495e'),
            borderPadding=5,
            borderColor=colors.HexColor('#ecf0f1'),
            borderWidth=0,
            backColor=colors.HexColor('#f8f9fa'),
            keepWithNext=True  # IMPORTANTE: Evita titoli orfani a fine pagina
        )

        # Definizione stile per i Sottotitoli (H3)
        style_h3 = ParagraphStyle(
            'TALDH3',
            parent=styles['Heading3'],
            fontSize=11,
            textColor=colors.HexColor('#2c3e50'),
            spaceBefore=6,
            spaceAfter=2,      # Poco spazio dopo, per stare vicino al testo
            keepWithNext=True  # Non si stacca mai dal prossimo paragrafo
        )
        
        # Testo normale giustificato per leggibilità
        style_normal = ParagraphStyle(
            'TALDNormal', 
            parent=styles['Normal'], 
            fontSize=10, 
            leading=14,
            alignment=TA_JUSTIFY
        )
        
        # Stili per esiti 
        style_ok = ParagraphStyle(
            'ResultOK', 
            parent=style_normal, 
            textColor=colors.HexColor('#27ae60'), 
            fontName='Helvetica-Bold',
            alignment=TA_CENTER  
        )
        
        style_err = ParagraphStyle(
            'ResultERR', 
            parent=style_normal, 
            textColor=colors.HexColor('#c0392b'), 
            fontName='Helvetica-Bold',
            alignment=TA_CENTER  
        )
        
        style_warn = ParagraphStyle(
            'ResultWARN', 
            parent=style_normal, 
            textColor=colors.HexColor('#e67e22'), 
            fontName='Helvetica-Bold',
            alignment=TA_CENTER  
        )
        
        # Stile per il punteggio (Verde/Rosso dinamico)
        score_color = colors.HexColor('#27ae60') if report.result.is_passing_score() else colors.HexColor('#c0392b')
        style_score = ParagraphStyle(
            'TALDScore',
            parent=styles['Normal'],
            fontSize=12,
            textColor=score_color,
            fontName='Helvetica-Bold'
        )

        # --- Costruzione Contenuto (Story) ---
        elements = []

        # 1. HEADER (LOGO + TESTO BEN DISTANZIATI)
        logo_path = "assets/taldlab_logo.png"
        
        # Colonna Logo
        if os.path.exists(logo_path):
            img = Image(logo_path, width=2.5*cm, height=2.5*cm)
            img.hAlign = 'LEFT'
            col_logo = img
        else:
            col_logo = Paragraph("<b>TALDLab</b>", style_title) # Fallback testuale

        # Colonna Testo Intestazione
        title_text = [
            Paragraph("TALDLab", style_title),
            Paragraph("Report di Simulazione Clinica", style_subtitle),
            Paragraph(f"Data: {report.timestamp.strftime('%d/%m/%Y %H:%M')}", style_date)
        ]
        
        # Creazione Tabella Header 
        header_table = Table([[col_logo, title_text]], colWidths=[3*cm, 13*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 20), 
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.2*cm))

        # 2. RIEPILOGO VALUTAZIONE (Tabella)
        elements.append(KeepTogether([
            Paragraph("Riepilogo Valutazione", style_h2),
            self._create_summary_table(report, style_ok, style_err, style_warn, all_items),
            Spacer(1, 0.5*cm)
        ]))
        
        # Punteggio sotto la tabella
        elements.append(Paragraph(f"Punteggio Complessivo: {report.result.score}/100 ({report.result.get_performance_level()})", style_score))
        elements.append(Spacer(1, 1.0*cm))

        # 3. SPIEGAZIONE CLINICA 
        # Titolo Sezione
        elements.append(Paragraph("Analisi Clinica (AI Generated)", style_h2))
        
        # Generazione dinamica dei paragrafi
        ai_flowables = self._parse_ai_response_to_flowables(
            report.clinical_explanation, 
            style_normal, 
            style_h3
        )
        elements.extend(ai_flowables)
        
        # Spazio finale
        elements.append(Spacer(1, 1.0*cm))
        
        # 4. DETTAGLI ITEM (Box informativo bordato)
        elements.append(KeepTogether([
            Paragraph("Dettagli Item Simulato", style_h2),
            self._create_item_details_table(report, style_normal),
            Spacer(1, 1.0*cm)
        ]))

        # 5. STATISTICHE E NOTE PERSONALI
        stats_text = (
            f"Durata: {report.conversation_summary['duration_minutes']} min | "
            f"Messaggi: {report.conversation_summary['total_messages']} | "
            f"Parole: {report.conversation_summary['total_words']}"
        )
        
        notes_section = []
        if report.user_evaluation.notes:
            notes_section.append(Paragraph("<b>Note Personali:</b>", style_normal))
            notes_section.append(Paragraph(report.user_evaluation.notes, style_normal))
            
        elements.append(KeepTogether([
            Paragraph("Statistiche Conversazione", style_h2),
            Paragraph(stats_text, style_normal),
            Spacer(1, 0.5*cm),
            *notes_section
        ]))

        # Footer (Piè di pagina)
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(
            f"Generato da TALDLab il {datetime.now().strftime('%d/%m/%Y')}", 
            ParagraphStyle('Footer', parent=styles['Italic'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        ))

        # Generazione fisica del file in memoria
        doc.build(elements)
        
        # Riposiziona il cursore all'inizio del buffer per la lettura
        buffer.seek(0)
        return buffer

    def _create_summary_table(self, report: Report, style_ok, style_err, style_warn, all_items: list[TALDItem] = None) -> Table:
        """
        Crea la tabella riepilogo per il PDF.
        Usa Paragraph per gestire il testo lungo che va a capo.
        """
        # Creiamo uno stile "neutro" per le celle di testo normale che devono andare a capo
        styles = getSampleStyleSheet()
        style_cell = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER, # Centrato come il resto della tabella
            leading=12,          # Interlinea
            textColor=colors.black
        )

        # --- 1. Preparazione Testo Ground Truth ---
        # Avvolgiamo in Paragraph così va a capo se lungo
        gt_text = f"{report.tald_item.id}. {report.tald_item.title}"
        gt_cell = Paragraph(gt_text, style_cell)

        # --- 2. Preparazione Testo Utente ---
        if report.ground_truth.is_exploratory_mode():
            user_id = report.user_evaluation.item_id
            
            # Cerca il titolo
            user_text_str = f"ID {user_id}" 
            if all_items and user_id:
                found = next((i for i in all_items if i.id == user_id), None)
                if found:
                    user_text_str = f"{found.id}. {found.title}"
            
            # Avvolgiamo in Paragraph
            user_item_cell = Paragraph(user_text_str, style_cell)
            
            # Esito (Paragraph colorato)
            res_item = Paragraph("CORRETTO", style_ok) if report.result.item_correct else Paragraph("ERRATO", style_err)
        else:
            user_item_cell = Paragraph("N/A (Guidata)", style_cell)
            res_item = "-"

        # --- 3. Preparazione Grado ---
        # Anche i gradi li mettiamo in Paragraph per coerenza di font/stile
        gt_grade_cell = Paragraph(f"{report.ground_truth.grade}/4", style_cell)
        user_grade_cell = Paragraph(f"{report.user_evaluation.grade}/4", style_cell)

        if report.result.grade_correct:
            res_grade = Paragraph("CORRETTO", style_ok)
        elif report.result.grade_difference == 1:
            res_grade = Paragraph("IMPRECISO", style_warn)
        else:
            res_grade = Paragraph("ERRATO", style_err)

        # --- 4. Costruzione Dati Tabella ---
        data = [
            ["Parametro", "Ground Truth", "Valutazione Utente", "Esito"],
            # Nota: Ora passiamo gli oggetti Paragraph, non stringhe
            ["Item TALD", gt_cell, user_item_cell, res_item],
            ["Grado", gt_grade_cell, user_grade_cell, res_grade]
        ]
        
        # Le larghezze colonne (colWidths) ora funzionano come limiti:
        # Il testo andrà a capo se supera i 6.0cm o 4.0cm definiti qui sotto.
        t = Table(data, colWidths=[3.5*cm, 6.0*cm, 4.0*cm, 2.5*cm])
        
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),     # Allineamento orizzontale
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),    # Allineamento verticale
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fdfdfd')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            # Rimuoviamo eventuali padding manuali che potrebbero stringere troppo il testo
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        
        return t

    def _create_item_details_table(self, report: Report, style_normal: ParagraphStyle) -> Table:
        """
        Crea la tabella dettagli item per il PDF.
        Incapsula le informazioni statiche in un box pulito.
        """
        item_info = [
            [Paragraph(f"<b>Descrizione:</b> {report.tald_item.description}", style_normal)],
            [Paragraph(f"<b>Criteri:</b> {report.tald_item.criteria}", style_normal)],
            [Paragraph(f"<b>Esempio:</b> {report.tald_item.example}", style_normal)]
        ]
        t = Table(item_info, colWidths=[16*cm])
        t.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.25, colors.grey),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        return t