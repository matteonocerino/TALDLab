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
import html
from datetime import datetime
from typing import Optional, List, Dict
from io import BytesIO 

# ReportLab imports per generazione PDF reale
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, Flowable

from src.models.evaluation import UserEvaluation, GroundTruth, EvaluationResult
from src.models.conversation import ConversationHistory
from src.models.tald_item import TALDItem
from src.services.llm_service import LLMService, LLMTimeoutError, LLMConnectionError


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


class NoSpaceAtTop(Flowable):
    """
    Wrapper per Flowable che rimuove lo spazio superiore se l'elemento è in cima alla pagina.
    Utile per evitare spazi vuoti indesiderati nei blocchi KeepTogether.
    """
    def __init__(self, element):
        Flowable.__init__(self)
        self.element = element

    def wrap(self, availWidth, availHeight):
        # Propaga la dimensione corretta
        return self.element.wrap(availWidth, availHeight)

    def draw(self):
        # Non usare drawOn() — lascia gestire coordinate al frame
        self.element.canv = self.canv
        self.element.draw()



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
        tald_item: Optional[TALDItem] = None,
        all_items: List[TALDItem] = None
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

        # Recupera il grado principale per il prompt (utile in modalità guidata)
        # In esplorativa usiamo 0 come default se tald_item è None
        current_grade = 0
        if tald_item:
            current_grade = ground_truth.active_items.get(tald_item.id, 0)

        # Preparazione lista item per LLM (gestione sicurezza)
        # Se all_items non viene passato, creiamo una lista minima con l'item corrente
        items_for_llm = all_items if all_items else []
        if not items_for_llm and tald_item:
            items_for_llm = [tald_item]    

        # 1. Generazione spiegazione clinica (con gestione Fallback)
        try:
            # Tentativo principale: Analisi AI tramite Gemini
            clinical_explanation = self.llm_service.generate_clinical_explanation(
                ground_truth=ground_truth,      
                all_tald_items=items_for_llm,   
                conversation_history=conversation
            )

        except (LLMTimeoutError, LLMConnectionError):
            # Se è un errore di rete/timeout, NON usare il fallback.
            # Rilancia l'errore così app.py può mostrare il bottone "Riprova".
            raise    

        except Exception:
            # Solo per altri errori imprevisti (es. bug di parsing interno),
            # usiamo il fallback statico per non far crashare tutto.
            clinical_explanation = self._generate_basic_explanation(tald_item, current_grade)
        
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
        if not tald_item:
            return "**Errore:** Impossibile generare spiegazione (Item non identificato e AI non disponibile)."

        grade_desc = tald_item.get_grade_description(grade) if tald_item else "N/A"
        
        return f"""**Nota:** Questa è una spiegazione generata dai dati statici (LLM non disponibile al momento).

**Item TALD simulato:** {tald_item.title}

**Descrizione del disturbo:**
{tald_item.description}

**Criteri diagnostici:**
{tald_item.criteria}

**Grado manifestato:** {grade}/4 - {grade_desc}

**Esempio tipico:**
{tald_item.example}
"""
    
    def _create_clinical_flowables(self, text: str, styles: Dict) -> List:
        if not text:
            return []

        flowables = []
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        lines = text.split('\n')

        # --- DEFINIZIONE STILI ---
        # Stile H3 (Titolo Sezione)
        style_h3 = ParagraphStyle(
            'ClinicalH3', parent=styles['Heading3'], fontSize=12,
            textColor=colors.HexColor('#2c3e50'), spaceBefore=12, spaceAfter=6,
            keepWithNext=True
        )

        # Stile Livello 1 (* Categoria): Grassetto, indentato poco
        style_l1 = ParagraphStyle(
            'BulletLvl1', parent=styles['Normal'], fontSize=10, leading=14,
            leftIndent=30, bulletIndent=10, firstLineIndent=0, 
            spaceAfter=2, alignment=TA_JUSTIFY,
            fontName='Helvetica-Bold'
        )

        # Stile Livello 2 (- Dettaglio): Normale, indentato molto
        style_l2 = ParagraphStyle(
            'BulletLvl2', parent=styles['Normal'], fontSize=10, leading=14,
            leftIndent=55, bulletIndent=35, firstLineIndent=0, 
            spaceAfter=4, alignment=TA_JUSTIFY
        )

        style_normal = styles['TALDNormal']
        
        # Variabili di stato per il raggruppamento (KeepTogether)
        pending_h3 = None
        pending_l1 = None

        for line in lines:
            line = line.strip()
            if not line: continue

            # --- 1. RILEVAMENTO TITOLO (###) ---
            if line.startswith('#') or (len(line) > 0 and line[0].isdigit() and '. ' in line[:5]):
                # Se c'erano elementi in sospeso, chiudiamoli
                if pending_l1:
                    group = [pending_l1]
                    if pending_h3: group.insert(0, pending_h3)
                    flowables.append(KeepTogether(group))
                elif pending_h3:
                    flowables.append(KeepTogether([pending_h3]))

                clean = re.sub(r'^[\#\d\.]+\s*', '', line).replace('*', '')
                prefix = line.split(' ')[0] if line[0].isdigit() else "" 
                clean = f"{prefix} {clean}".strip()
                clean = html.escape(clean)
                
                pending_h3 = Paragraph(f"<b>{clean}</b>", style_h3)
                pending_l1 = None # Reset L1
                continue

            # --- 2. RILEVAMENTO CATEGORIA (* ) ---
            if line.startswith('* '):
                # Se c'era un L1 precedente senza figli, chiudiamolo
                if pending_l1:
                    group = [pending_l1]
                    if pending_h3: 
                        group.insert(0, pending_h3)
                        pending_h3 = None # Il titolo è stato usato
                    flowables.append(KeepTogether(group))

                clean = re.sub(r'^\*\s+', '', line)
                clean = html.escape(clean)
                # Creiamo il paragrafo L1 e lo teniamo in sospeso
                pending_l1 = Paragraph(f'<bullet>&bull;</bullet>{clean}', style_l1)
                continue

            # --- 3. RILEVAMENTO DETTAGLIO (- ) ---
            if line.startswith('- '):
                clean = re.sub(r'^\-\s+', '', line)
                clean = html.escape(clean)
                clean = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean)
                p = Paragraph(f'<bullet>-</bullet>{clean}', style_l2)

                if pending_l1:
                    # QUESTO È IL PUNTO CHIAVE:
                    # Abbiamo un L1 in attesa (e forse un H3). Questo è il PRIMO figlio.
                    # Li leghiamo tutti insieme in un blocco indivisibile.
                    group = [pending_l1, p]
                    if pending_h3:
                        group.insert(0, pending_h3)
                        pending_h3 = None # Titolo consumato
                    
                    flowables.append(KeepTogether(group))
                    pending_l1 = None # L1 consumato (già incollato al primo figlio)
                else:
                    # Sono figli successivi (2°, 3° bullet point)
                    # Li aggiungiamo come elementi singoli (così se serve vanno a capo pagina)
                    flowables.append(KeepTogether([p]))
                continue

            # --- 4. TESTO NORMALE (Fallback) ---
            clean = html.escape(line)
            p = Paragraph(clean, style_normal)
            
            # Se c'era roba in sospeso, la incolliamo a questo testo
            if pending_l1:
                group = [pending_l1, p]
                if pending_h3: group.insert(0, pending_h3); pending_h3=None
                flowables.append(KeepTogether(group))
                pending_l1 = None
            elif pending_h3:
                flowables.append(KeepTogether([pending_h3, p]))
                pending_h3 = None
            else:
                flowables.append(p)

        # Pulizia finale (se l'ultimo elemento era un titolo o categoria senza figli)
        if pending_l1:
            group = [pending_l1]
            if pending_h3: group.insert(0, pending_h3)
            flowables.append(KeepTogether(group))
        elif pending_h3:
            flowables.append(KeepTogether([pending_h3]))

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
        
        # Setup Documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=1.5*cm, bottomMargin=1.5*cm,
            title="TALDLab Report"
        )
        
        styles = getSampleStyleSheet()
        story = []

        # --- DEFINIZIONE STILI ---
        # Stili base personalizzati
        style_normal = ParagraphStyle('TALDNormal', parent=styles['Normal'], fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=6)
        styles.add(style_normal) # Lo registriamo per usarlo nell'helper

        style_title = ParagraphStyle('TALDTitle', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#2c3e50'), spaceAfter=2, leading=28)
        style_subtitle = ParagraphStyle('TALDSub', parent=styles['Normal'], fontSize=13, textColor=colors.HexColor('#7f8c8d'), spaceAfter=6, leading=16)
        style_h2 = ParagraphStyle('TALDH2', parent=styles['Heading2'], fontSize=14, spaceBefore=12, spaceAfter=10, textColor=colors.HexColor('#34495e'), backColor=colors.HexColor('#f8f9fa'), borderPadding=5, keepWithNext=True)
        style_h2_free = ParagraphStyle('TALDH2_Free', parent=style_h2, keepWithNext=False) 

        style_score = ParagraphStyle('TALDScore', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER, spaceBefore=6, textColor=colors.HexColor('#27ae60') if report.result.is_passing_score() else colors.HexColor('#c0392b'), fontName='Helvetica-Bold')
        style_footer = ParagraphStyle('Footer', parent=styles['Italic'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)

        # Stili tabella esiti
        style_ok = ParagraphStyle('ResultOK', parent=style_normal, textColor=colors.HexColor('#27ae60'), fontName='Helvetica-Bold', alignment=TA_CENTER)
        style_err = ParagraphStyle('ResultERR', parent=style_normal, textColor=colors.HexColor('#c0392b'), fontName='Helvetica-Bold', alignment=TA_CENTER)
        style_warn = ParagraphStyle('ResultWARN', parent=style_normal, textColor=colors.HexColor('#e67e22'), fontName='Helvetica-Bold', alignment=TA_CENTER)

        # --- 1. HEADER ---
        logo_path = "assets/taldlab_logo.png"
        if os.path.exists(logo_path):
            img = Image(logo_path, width=2.5*cm, height=2.5*cm)
            img.hAlign = 'LEFT'
            col_logo = img
        else:
            col_logo = Paragraph("<b>TALDLab</b>", style_title)

        title_text = [
            Paragraph("TALDLab", style_title),
            Paragraph("Report di Simulazione Clinica", style_subtitle),
            Paragraph(f"Data: {report.timestamp.strftime('%d/%m/%Y %H:%M')}", style_normal)
        ]
        
        header_table = Table([[col_logo, title_text]], colWidths=[2.5*cm, 13.5*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.5*cm))

        # --- 2. RIEPILOGO VALUTAZIONE ---
        # Usiamo lo stile "Free" per non incollare rigidamente il titolo alla tabella intera
        story.append(Paragraph("Riepilogo Valutazione", style_h2_free))
        
        summary_table = self._create_summary_table(report, style_ok, style_err, style_warn, all_items)
        story.append(summary_table)
        story.append(Spacer(1, 0.3*cm))

        # Creazione Paragrafo Punteggio (da usare dopo)
        score_text = f"Punteggio Complessivo: {report.result.score}/100 ({report.result.get_performance_level()})"
        score_paragraph = Paragraph(score_text, style_score)

       # --- GESTIONE LOGICA MODALITÀ ---
        
        # CASO A: ESPLORATIVA CON PAZIENTE SANO (Ground Truth vuoto)
        if not report.ground_truth.active_items:
            # Stile per l'avviso "Paziente Sano"
            style_alert = ParagraphStyle(
                'HealthyAlert', parent=styles['Heading3'], 
                textColor=colors.HexColor('#2980b9'), 
                alignment=TA_CENTER, spaceAfter=2
            )
            
            # Creiamo un blocco unico inscindibile
            block_elements = [
                Paragraph("ℹ️ DIAGNOSI REALE: PAZIENTE SANO", style_alert),
                Paragraph("(Nessun disturbo del pensiero o del linguaggio presente)", style_footer),
                Spacer(1, 0.4*cm),
                score_paragraph  
            ]
            
            story.append(KeepTogether(block_elements))
        
        # CASO B: GUIDATA O ESPLORATIVA CON DISTURBI
        else:
            # Aggiungiamo semplicemente il punteggio sotto la tabella
            story.append(score_paragraph)

        story.append(Spacer(1, 0.8*cm))

       # --- 3. ANALISI CLINICA (AI) ---
        
        # 1. Genera i blocchi
        clinical_objects = self._create_clinical_flowables(report.clinical_explanation, styles)
        
        # 2. Titolo H2 Principale
        analysis_title = Paragraph("Analisi Clinica (AI Generated)", style_h2)
        
        if clinical_objects:
            # Estraiamo il primo blocco (che è già un KeepTogether [H3, P1])
            first_kt = clinical_objects[0]
            
            # Creiamo una lista piatta: [Titolo H2, Titolo H3, Paragrafo 1]
            flat_elements = [analysis_title]
            
            if isinstance(first_kt, KeepTogether):
                # Estraiamo i componenti interni del primo blocco
                flat_elements.extend(first_kt._content)
            else:
                flat_elements.append(first_kt)
            
            # Creiamo un UNICO KeepTogether piatto e pulito
            story.append(KeepTogether(flat_elements))
            
            # Aggiungiamo tutti gli altri blocchi normalmente
            story.extend(clinical_objects[1:])
        else:
            story.append(analysis_title)
            story.append(Paragraph("Nessuna analisi disponibile.", style_normal))
            
        story.append(Spacer(1, 0.8*cm))

        # --- 4. DETTAGLI ITEM ---
        target_items = []
        # Recuperiamo le chiavi degli item ATTIVI (quindi escludiamo automaticamente quelli non presenti)
        active_item_ids = report.ground_truth.active_items.keys()

        # LOGICA DI SELEZIONE
        if report.ground_truth.is_guided_mode():
            # Modalità Guidata: solo l'item studiato
            if report.tald_item:
                target_items.append(report.tald_item)
        else:
            # Modalità Esplorativa: recuperiamo TUTTI gli item reali dal DB completo
            if all_items:
                # Li ordiniamo per ID per averli numerati progressivamente (Item 1, Item 2...)
                sorted_ids = sorted(active_item_ids)
                for iid in sorted_ids:
                    found = next((i for i in all_items if i.id == iid), None)
                    if found:
                        target_items.append(found)

        # GENERAZIONE PDF
        if target_items:
            # 1. Prepariamo l'oggetto Titolo Sezione MA NON lo aggiungiamo ancora alla story
            section_title_text = "Dettagli Item Simulati" if len(target_items) > 1 else "Dettagli Item Simulato"
            section_header_paragraph = Paragraph(section_title_text, style_h2)

            # 2. Cicliamo usando enumerate per sapere se siamo al primo giro (index == 0)
            for index, item in enumerate(target_items):
                
                # --- Preparazione Testi e Colori (Come prima) ---
                title_text = f"Item {item.id}. {item.title}"
                status_text = ""
                status_color = colors.HexColor('#2c3e50') 
                
                if report.ground_truth.is_guided_mode():
                    status_text = "(Modalità Guidata)"
                    status_color = colors.HexColor('#7f8c8d') 
                else:
                    user_grade = report.user_evaluation.get_grade_for_item(item.id)
                    real_grade = report.ground_truth.active_items.get(item.id, 0)
                    
                    if user_grade == 0:
                        status_text = f"OMESSO (Reale: {real_grade}/4)"
                        status_color = colors.HexColor('#c0392b') 
                    elif user_grade == real_grade:
                        status_text = f"CORRETTO (Grado: {user_grade}/4)"
                        status_color = colors.HexColor('#27ae60') 
                    else:
                        status_text = f"IMPRECISO (Tuo: {user_grade}/4 | Reale: {real_grade}/4)"
                        status_color = colors.HexColor('#e67e22') 

                # --- Stili (Come prima) ---
                style_line1 = ParagraphStyle('ItemName', parent=styles['Heading3'], fontSize=12, textColor=colors.HexColor('#2c3e50'), spaceAfter=2)
                style_line2 = ParagraphStyle('ItemStatus', parent=styles['Normal'], fontSize=11, textColor=status_color, fontName='Helvetica-Bold', spaceAfter=6)
                
                # --- COSTRUZIONE BLOCCO ---
                # Creiamo la lista degli elementi di QUESTO item
                item_elements = [
                    Paragraph(title_text, style_line1),
                    Paragraph(status_text, style_line2),
                    self._create_item_details_table_dynamic(item, style_normal)
                ]

                if index == 0:
                    item_elements.insert(0, section_header_paragraph)

                # Aggiungiamo tutto il blocco unito alla storia
                story.append(KeepTogether(item_elements))
                
                story.append(Spacer(1, 0.6*cm))

        story.append(Spacer(1, 0.8*cm))

        # --- 5. STATISTICHE E FOOTER ---
        final_block = []
        stats_text = (
            f"Durata: {report.conversation_summary['duration_minutes']} min | "
            f"Messaggi: {report.conversation_summary['total_messages']} | "
            f"Parole: {report.conversation_summary['total_words']}"
        )
        final_block.append(Paragraph("Statistiche Conversazione", style_h2))
        final_block.append(Paragraph(stats_text, style_normal))
        
        if report.user_evaluation.notes:
            final_block.append(Spacer(1, 0.3*cm))
            final_block.append(Paragraph(f"<b>Note Personali:</b> {html.escape(report.user_evaluation.notes)}", style_normal))
            
        final_block.append(Spacer(1, 0.5*cm))
        final_block.append(Paragraph(f"Generato da TALDLab il {report.timestamp.strftime('%d/%m/%Y')}", style_footer))

        story.append(KeepTogether(final_block))

        # Build
        doc.build(story)
        buffer.seek(0)
        return buffer

    def _create_summary_table(self, report: Report, style_ok, style_err, style_warn, all_items: List[TALDItem] = None) -> Table:
        """Crea la tabella riepilogo per il PDF."""
        
        styles = getSampleStyleSheet()
        
        # 1. Definisco gli stili necessari (ENTRAMBI)
        style_cell_left = ParagraphStyle('CellLeft', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT, textColor=colors.black)
        
        style_cell_center = ParagraphStyle(
            'CellCenter', 
            parent=styles['Normal'], 
            fontSize=10, 
            alignment=TA_CENTER, 
            textColor=colors.black
        )

        # Helper per titolo item
        def get_title(iid):
            if not all_items: return f"Item {iid}"
            item = next((i for i in all_items if i.id == iid), None)
            return item.title if item else f"Item {iid}"

        # === CASO 1: MODALITÀ ESPLORATIVA ===
        if report.ground_truth.is_exploratory_mode():
            data = [["Disturbo (Item TALD)", "Esito Diagnosi", "Tuo Voto", "Reale"]]
            
            tp = report.result.true_positives
            fn = report.result.false_negatives
            fp = report.result.false_positives
            all_involved = sorted(list(set(tp + fn + fp)))
            
            if not all_involved:
                data.append([Paragraph("Nessun disturbo", style_cell_left), Paragraph("CORRETTO", style_ok), "-", "-"])
            else:
                for iid in all_involved:
                    title = get_title(iid)
                    user_g = report.user_evaluation.get_grade_for_item(iid)
                    real_g = report.ground_truth.active_items.get(iid, 0)
                    
                    if iid in tp:
                        diff = abs(user_g - real_g)
                        status = Paragraph("CORRETTO", style_ok) if diff == 0 else Paragraph(f"IMPRECISO", style_warn)
                    elif iid in fn:
                        status = Paragraph("OMESSO", style_err)
                    else: # fp
                        status = Paragraph("NON PRESENTE", style_err)

                    data.append([
                        Paragraph(f"<b>{title}</b>", style_cell_left),
                        status,
                        str(user_g) if user_g > 0 else "-",
                        str(real_g) if real_g > 0 else "-"
                    ])

            col_widths = [6.5*cm, 4.5*cm, 2.5*cm, 2.5*cm]
            
            # Definizione stile Esplorativa
            exploratory_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'), # Prima colonna allineata a SX
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ])

            t = Table(data, colWidths=col_widths, repeatRows=1)
            t.setStyle(exploratory_style)
            return t

        # === CASO 2: MODALITÀ GUIDATA ===
        else:
            # 1. Recupero Dati Sicuro
            if report.tald_item:
                item_full_name = f"{report.tald_item.id}. {report.tald_item.title}"
            else:
                item_full_name = "Item Target"
            
            primary_id, gt_grade = report.ground_truth.get_primary_item()
            user_grade = report.user_evaluation.get_grade_for_item(primary_id)
            diff = abs(gt_grade - user_grade)
            
            # 2. Calcolo Esito
            if diff == 0: 
                res_grade = Paragraph("CORRETTO", style_ok)
            elif diff == 1: 
                res_grade = Paragraph("IMPRECISO", style_warn)
            else: 
                res_grade = Paragraph("ERRATO", style_err)

            # 3. Costruzione Dati 
            data = [
                ["Item Simulato", "Grado Reale", "Tuo Grado", "Esito"],
                [
                    # Qui ho cambiato style_cell_left in style_cell_center
                    Paragraph(f"<b>{item_full_name}</b>", style_cell_center), 
                    Paragraph(f"{gt_grade}/4", style_cell_center),              
                    Paragraph(f"{user_grade}/4", style_cell_center),          
                    res_grade                                                 
                ]
            ]
            
            # 4. Larghezze colonne
            col_widths = [7.0*cm, 3.0*cm, 3.0*cm, 3.0*cm]

            # 5. Definizione stile Guidata
            guided_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white]),
            ])

            t = Table(data, colWidths=col_widths, repeatRows=1)
            t.setStyle(guided_style)
            return t

    def _create_item_details_table_dynamic(self, item: TALDItem, style_normal: ParagraphStyle) -> Table:
        """
        Crea la tabella dettagli item per il PDF.
        Incapsula le informazioni statiche in un box pulito
        """
        if not item: return Table([[""]])
        
        desc = html.escape(item.description)
        crit = html.escape(item.criteria)
        exmp = html.escape(item.example)

        # Grassetto nei titoli
        item_info = [
            [Paragraph(f"<b>Descrizione:</b><br/>{desc}", style_normal)],
            [Paragraph(f"<b>Criteri Diagnostici:</b><br/>{crit}", style_normal)],
            [Paragraph(f"<b>Esempio Clinico:</b><br/>{exmp}", style_normal)]
        ]
        
        t = Table(item_info, colWidths=[16*cm])
        t.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f9f9f9')), 
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey), 
        ]))
        return t