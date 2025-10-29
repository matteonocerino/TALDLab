"""
ReportGenerator - Servizio per generazione report finali

Questo modulo genera i report finali delle simulazioni:
- Aggrega dati da ground truth, valutazione utente e risultato confronto
- Genera spiegazioni cliniche tramite LLM
- Formatta report per visualizzazione e export PDF
- Include metadati temporali e statistiche conversazione

Control del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_8, RF_9 del RAD
"""

from datetime import datetime
from typing import Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from models.evaluation import UserEvaluation, GroundTruth, EvaluationResult
from models.conversation import ConversationHistory
from models.tald_item import TALDItem
from services.llm_service import LLMService, LLMConnectionError


class Report:
    """
    Rappresenta un report finale di simulazione.
    
    Entity che aggrega tutti i dati necessari per il report.
    
    Attributes:
        ground_truth (GroundTruth): Ground truth della simulazione
        user_evaluation (UserEvaluation): Valutazione fornita dall'utente
        result (EvaluationResult): Risultato del confronto
        clinical_explanation (str): Spiegazione clinica generata
        conversation_summary (dict): Statistiche conversazione
        tald_item (TALDItem): Item TALD completo per reference
        timestamp (datetime): Timestamp generazione report
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
    
    def to_dict(self) -> dict:
        """Converte il report in dizionario."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "mode": self.ground_truth.mode,
            "ground_truth": self.ground_truth.to_dict(),
            "user_evaluation": self.user_evaluation.to_dict(),
            "result": self.result.to_dict(),
            "clinical_explanation": self.clinical_explanation,
            "conversation_summary": self.conversation_summary,
            "tald_item": {
                "id": self.tald_item.id,
                "title": self.tald_item.title,
                "type": self.tald_item.type
            }
        }


class ReportGenerator:
    """
    Service per generazione report finali delle simulazioni.
    
    Responsabilità:
    - Generare report aggregando tutti i dati (RF_8)
    - Invocare LLM per spiegazioni cliniche (RF_8)
    - Formattare report per visualizzazione
    - Esportare report in PDF (RF_9)
    
    Come da RAD 2.6.1 - ReportGenerator:
    "Genera il report finale della simulazione. Aggrega dati da ground truth,
    valutazione utente e risultato del confronto. Può invocare opzionalmente
    il Servizio LLM per generare spiegazioni cliniche contestualizzate basate
    sullo storico conversazionale."
    
    Attributes:
        llm_service (LLMService): Servizio LLM per generare spiegazioni
    
    Example:
        >>> generator = ReportGenerator(llm_service)
        >>> report = generator.generate_report(
        ...     ground_truth=gt,
        ...     user_evaluation=eval,
        ...     result=comparison_result,
        ...     conversation=history,
        ...     tald_item=item
        ... )
        >>> print(report.clinical_explanation)
    """
    
    def __init__(self, llm_service: LLMService):
        """
        Inizializza il ReportGenerator.
        
        Args:
            llm_service (LLMService): Servizio LLM configurato
        """
        self.llm_service = llm_service
    
    def generate_report(
        self,
        ground_truth: GroundTruth,
        user_evaluation: UserEvaluation,
        result: EvaluationResult,
        conversation: ConversationHistory,
        tald_item: TALDItem,
        include_llm_explanation: bool = True
    ) -> Report:
        """
        Genera il report finale della simulazione.
        
        Implementa RF_8: generazione e visualizzazione report.
        
        Args:
            ground_truth (GroundTruth): Ground truth simulazione
            user_evaluation (UserEvaluation): Valutazione utente
            result (EvaluationResult): Risultato confronto
            conversation (ConversationHistory): Storico conversazione
            tald_item (TALDItem): Item TALD completo
            include_llm_explanation (bool): Se True, genera spiegazione LLM
            
        Returns:
            Report: Report completo generato
            
        Example:
            >>> report = generator.generate_report(
            ...     ground_truth=gt,
            ...     user_evaluation=eval,
            ...     result=result,
            ...     conversation=history,
            ...     tald_item=item
            ... )
        """
        # 1. Genera spiegazione clinica (opzionale via LLM)
        if include_llm_explanation:
            clinical_explanation = self._generate_clinical_explanation(
                tald_item=tald_item,
                conversation=conversation,
                grade=ground_truth.grade
            )
        else:
            # Fallback: spiegazione base senza LLM
            clinical_explanation = self._generate_basic_explanation(
                tald_item=tald_item,
                grade=ground_truth.grade
            )
        
        # 2. Prepara summary conversazione
        conversation_summary = {
            "total_messages": conversation.get_message_count(),
            "duration_minutes": conversation.get_duration_minutes(),
            "total_words": conversation.get_total_words(),
            "user_messages": len(conversation.get_user_messages()),
            "assistant_messages": len(conversation.get_assistant_messages())
        }
        
        # 3. Crea oggetto Report
        report = Report(
            ground_truth=ground_truth,
            user_evaluation=user_evaluation,
            result=result,
            clinical_explanation=clinical_explanation,
            conversation_summary=conversation_summary,
            tald_item=tald_item
        )
        
        return report
    
    def _generate_clinical_explanation(
        self,
        tald_item: TALDItem,
        conversation: ConversationHistory,
        grade: int
    ) -> str:
        """
        Genera spiegazione clinica tramite LLM.
        
        Args:
            tald_item (TALDItem): Item simulato
            conversation (ConversationHistory): Storico conversazione
            grade (int): Grado simulato
            
        Returns:
            str: Spiegazione clinica dettagliata
        """
        try:
            explanation = self.llm_service.generate_clinical_explanation(
                tald_item=tald_item,
                conversation_history=conversation,
                grade=grade
            )
            return explanation
        
        except LLMConnectionError as e:
            # Fallback se LLM non disponibile
            return self._generate_basic_explanation(tald_item, grade) + \
                   f"\n\n(Nota: Spiegazione LLM non disponibile: {str(e)})"
    
    def _generate_basic_explanation(
        self,
        tald_item: TALDItem,
        grade: int
    ) -> str:
        """
        Genera spiegazione clinica base (senza LLM).
        
        Fallback quando LLM non è disponibile o non richiesto.
        
        Args:
            tald_item (TALDItem): Item simulato
            grade (int): Grado simulato
            
        Returns:
            str: Spiegazione base
        """
        grade_desc = tald_item.get_grade_description(grade)
        
        explanation = f"""**Item TALD simulato:** {tald_item.title}

**Descrizione del disturbo:**
{tald_item.description}

**Criteri diagnostici:**
{tald_item.criteria}

**Grado manifestato:** {grade}/4 - {grade_desc}

**Come identificare questo disturbo:**
Durante l'intervista clinica, questo disturbo si manifesta attraverso specifici 
pattern linguistici e comportamentali. L'esaminatore deve prestare attenzione 
alle caratteristiche descritte nei criteri diagnostici e confrontarle con 
le manifestazioni osservate nel paziente.

**Esempio tipico:**
{tald_item.example}
"""
        return explanation
    
    def format_report_text(self, report: Report) -> str:
        """
        Formatta il report come testo leggibile.
        
        Args:
            report (Report): Report da formattare
            
        Returns:
            str: Report formattato come testo
        """
        lines = []
        lines.append("="*70)
        lines.append("TALDLab - Report Simulazione")
        lines.append("="*70)
        lines.append(f"\nData: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Modalità: {report.ground_truth.mode.upper()}")
        
        lines.append("\n" + "-"*70)
        lines.append("GROUND TRUTH")
        lines.append("-"*70)
        lines.append(f"Item simulato: {report.tald_item.id}. {report.tald_item.title}")
        lines.append(f"Tipo: {report.tald_item.type}")
        lines.append(f"Grado: {report.ground_truth.grade}/4")
        
        lines.append("\n" + "-"*70)
        lines.append("VALUTAZIONE UTENTE")
        lines.append("-"*70)
        
        if report.ground_truth.is_exploratory_mode():
            lines.append(f"Item identificato: {report.user_evaluation.item_id}")
        
        lines.append(f"Grado attribuito: {report.user_evaluation.grade}/4")
        
        if report.user_evaluation.notes:
            lines.append(f"Note: {report.user_evaluation.notes}")
        
        lines.append("\n" + "-"*70)
        lines.append("RISULTATO VALUTAZIONE")
        lines.append("-"*70)
        
        if report.result.item_correct is not None:
            status = "✓ CORRETTO" if report.result.item_correct else "✗ ERRATO"
            lines.append(f"Item identificato: {status}")
        
        status = "✓ CORRETTO" if report.result.grade_correct else "✗ ERRATO"
        lines.append(f"Grado attribuito: {status}")
        lines.append(f"Differenza grado: {report.result.grade_difference}")
        lines.append(f"\nPunteggio: {report.result.score}/100")
        lines.append(f"Performance: {report.result.get_performance_level()}")
        
        lines.append("\n" + "-"*70)
        lines.append("FEEDBACK")
        lines.append("-"*70)
        lines.append(report.result.feedback_message)
        
        lines.append("\n" + "-"*70)
        lines.append("SPIEGAZIONE CLINICA")
        lines.append("-"*70)
        lines.append(report.clinical_explanation)
        
        lines.append("\n" + "-"*70)
        lines.append("STATISTICHE CONVERSAZIONE")
        lines.append("-"*70)
        lines.append(f"Messaggi totali: {report.conversation_summary['total_messages']}")
        lines.append(f"Durata: {report.conversation_summary['duration_minutes']} minuti")
        lines.append(f"Parole scambiate: {report.conversation_summary['total_words']}")
        
        lines.append("\n" + "="*70)
        lines.append("Fine report")
        lines.append("="*70)
        
        return "\n".join(lines)
    
    def export_pdf(self, report: Report, filename: Optional[str] = None) -> str:
        """
        Esporta il report in formato PDF.
        
        Implementa RF_9: esportazione report in PDF.
        
        Args:
            report (Report): Report da esportare
            filename (str, optional): Nome file PDF (auto-generato se None)
            
        Returns:
            str: Path del file PDF creato
            
        Note:
            Implementazione placeholder - richiede reportlab per PDF reale
        """
        # Genera nome file se non fornito
        if filename is None:
            timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"TALDLab_Report_{timestamp}.pdf"
        
        # TODO: Implementazione completa con reportlab
        # Per ora, salva come .txt come placeholder
        txt_filename = filename.replace('.pdf', '.txt')
        
        content = self.format_report_text(report)
        
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return txt_filename
    
    def get_report_summary(self, report: Report) -> dict:
        """
        Genera un summary compatto del report.
        
        Utile per visualizzazioni rapide o statistiche.
        
        Args:
            report (Report): Report da riassumere
            
        Returns:
            dict: Summary con info chiave
        """
        return {
            "timestamp": report.timestamp.isoformat(),
            "mode": report.ground_truth.mode,
            "item_id": report.tald_item.id,
            "item_title": report.tald_item.title,
            "score": report.result.score,
            "performance": report.result.get_performance_level(),
            "item_correct": report.result.item_correct,
            "grade_correct": report.result.grade_correct,
            "grade_difference": report.result.grade_difference,
            "messages_exchanged": report.conversation_summary['total_messages'],
            "duration_minutes": report.conversation_summary['duration_minutes']
        }