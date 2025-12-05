"""
SessionState Model - Modello per gestione stato sessione

Questo modulo contiene la classe SessionState che mantiene lo stato globale
della sessione corrente, coordinando tutte le fasi dell'interazione
(selezione modalità, intervista, valutazione, report).

Entity del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
"""

from dataclasses import dataclass, field
from typing import Optional, Dict
from datetime import datetime
from enum import Enum
import uuid

from .conversation import ConversationHistory
from .evaluation import GroundTruth, UserEvaluation, EvaluationResult


class SessionPhase(Enum):
    """
    Enumerazione delle fasi possibili della sessione.
    
    Rappresenta il workflow dell'applicazione:
    SELECTION -> ITEM_SELECTION -> INTERVIEW -> EVALUATION -> REPORT
    """
    SELECTION = "selection"              # Selezione modalità (guidata/esplorativa)
    ITEM_SELECTION = "item_selection"    # Selezione item (solo modalità guidata)
    INTERVIEW = "interview"              # Conduzione intervista
    EVALUATION = "evaluation"            # Valutazione finale
    REPORT = "report"                    # Visualizzazione report


@dataclass
class SessionState:
    """
    Rappresenta lo stato globale della sessione corrente.
    
    Mantiene tutte le informazioni necessarie per coordinare il flusso
    dell'applicazione attraverso le diverse fasi.
    
    Attributes:
        phase (SessionPhase): Fase corrente della sessione
        mode (Optional[str]): Modalità selezionata ("guided" o "exploratory")
        ground_truth (Optional[GroundTruth]): Configurazione clinica reale della simulazione
        conversation (ConversationHistory): Storico conversazionale completo
        user_evaluation (Optional[UserEvaluation]): Valutazione fornita dall'utente
        evaluation_result (Optional[EvaluationResult]): Risultato del confronto automatico
        session_id (str): Identificativo univoco della sessione (per log/debug)
        created_at (datetime): Timestamp di avvio della sessione
    
    Example:
        >>> session = SessionState()
        >>> print(session.phase)
        SessionPhase.SELECTION
    """
    
    phase: SessionPhase = SessionPhase.SELECTION
    mode: Optional[str] = None
    
    # Gestisce la complessità del quadro clinico (multi-item)
    ground_truth: Optional[GroundTruth] = None
    
    conversation: ConversationHistory = field(default_factory=ConversationHistory)
    user_evaluation: Optional[UserEvaluation] = None
    evaluation_result: Optional[EvaluationResult] = None
    
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: datetime = field(default_factory=datetime.now)
    
    # ======== Helper di Stato e Modalità ========

    def is_guided_mode(self) -> bool:
        """Verifica se la sessione è in modalità guidata."""
        return self.mode == "guided"
    
    def is_exploratory_mode(self) -> bool:
        """Verifica se la sessione è in modalità esplorativa."""
        return self.mode == "exploratory"
    
    def is_in_selection(self) -> bool:
        """Verifica se si è nella fase di selezione modalità."""
        return self.phase.value == SessionPhase.SELECTION.value
    
    def is_in_item_selection(self) -> bool:
        """Verifica se si è nella fase di selezione item (solo modalità guidata)."""
        return self.phase.value == SessionPhase.ITEM_SELECTION.value
    
    def is_in_interview(self) -> bool:
        """Verifica se si è nella fase di intervista."""
        return self.phase.value == SessionPhase.INTERVIEW.value
    
    def is_in_evaluation(self) -> bool:
        """Verifica se si è nella fase di valutazione."""
        return self.phase.value == SessionPhase.EVALUATION.value
    
    def is_in_report(self) -> bool:
        """Verifica se si è nella fase di visualizzazione report."""
        return self.phase.value == SessionPhase.REPORT.value

    # ======== Transizioni di Stato (Core Logic) ========

    def start_guided_mode(self):
        """
        Inizia la modalità guidata.
        Imposta la modalità su "guided" e passa alla fase di selezione item.
        """
        self.mode = "guided"
        self.phase = SessionPhase.ITEM_SELECTION
    
    def start_exploratory_mode(self, active_items: Dict[int, int]):
        """
        Inizia la modalità esplorativa con una configurazione complessa (comorbilità).
        
        Args:
            active_items (Dict[int, int]): Dizionario dei disturbi attivi {item_id: grado}.
                                           Esempio: {5: 3, 12: 2} indica Crosstalk grado 3
                                           e Paraphasia grado 2.
        """
        self.mode = "exploratory"
        
        # Crea il Ground Truth utilizzando la nuova struttura multi-item.
        # In questa fase non servono i titoli testuali per la logica interna.
        self.ground_truth = GroundTruth(
            active_items=active_items,
            mode="exploratory"
        )
        
        # In modalità esplorativa, saltiamo la selezione item e andiamo diretti all'intervista
        self.phase = SessionPhase.INTERVIEW
    
    def set_selected_item(self, item_id: int, grade: int):
        """
        Imposta l'item selezionato in modalità guidata e avvia l'intervista.
        
        In questa modalità, il paziente ha UN SOLO disturbo (quello scelto).
        Lo adattiamo alla struttura dati creando un dizionario con una sola voce.
        
        Args:
            item_id (int): ID dell'item scelto dall'utente.
            grade (int): Grado di severità simulato (generato casualmente 0-4).
        """
        if not self.is_guided_mode():
            raise ValueError("Metodo disponibile solo in modalità guidata")
        
        # Creazione configurazione "Singolo Disturbo" 
        active_items = {item_id: grade}
        
        self.ground_truth = GroundTruth(
            active_items=active_items,
            mode="guided"
        )
        
        self.phase = SessionPhase.INTERVIEW
    
    def terminate_interview(self):
        """
        Termina l'intervista e passa alla fase di valutazione.
        Verifica che la fase corrente sia corretta prima di procedere.
        """
        if not self.is_in_interview():
            raise ValueError("Impossibile terminare l'intervista se non si è in fase di intervista")
        
        self.phase = SessionPhase.EVALUATION
    
    def submit_evaluation(self, user_eval: UserEvaluation, result: EvaluationResult):
        """
        Sottomette la valutazione e passa alla visualizzazione report.
        
        Args:
            user_eval (UserEvaluation): Valutazione fornita dall'utente (scheda completa).
            result (EvaluationResult): Risultato del confronto calcolato dal motore.
        """
        if not self.is_in_evaluation():
            raise ValueError("Impossibile sottomettere valutazione se non si è in fase di valutazione")
        
        self.user_evaluation = user_eval
        self.evaluation_result = result
        self.phase = SessionPhase.REPORT

    # ======== Metriche e Riepilogo Sessione ========

    def get_session_duration_minutes(self) -> float:
        """
        Calcola la durata totale della sessione in minuti.
        
        Returns:
            float: Durata in minuti dall'inizio della sessione
        """
        duration = (datetime.now() - self.created_at).total_seconds()
        return round(duration / 60, 2)
    
    def get_conversation_summary(self) -> dict:
        """
        Restituisce un riepilogo statistico della conversazione.
        Utile per sidebar e reportistica.
        
        Returns:
            dict: Statistiche (messaggi totali, utente, assistente, durata, parole).
        """
        return {
            "message_count": self.conversation.get_message_count(),
            "user_messages": len(self.conversation.get_user_messages()),
            "assistant_messages": len(self.conversation.get_assistant_messages()),
            "duration_minutes": self.conversation.get_duration_minutes(),
            "total_words": self.conversation.get_total_words()
        }

    # ======== Gestione Ciclo di Vita (Reset) ========

    def reset(self):
        """
        Effettua un reset completo della sessione per iniziare una nuova simulazione.
        
        Mantiene solo il session_id (rigenerato se necessario per tracciabilità esterna)
        ma pulisce tutti i dati clinici, lo storico e i risultati.
        Utilizzato quando l'utente clicca "Avvia nuova simulazione" nel report.
        """
        self.phase = SessionPhase.SELECTION
        self.mode = None
        self.ground_truth = None
        self.conversation.clear()
        self.user_evaluation = None
        self.evaluation_result = None
        self.created_at = datetime.now()
    
    def to_dict(self) -> dict:
        """
        Converte lo stato della sessione in dizionario per debug/logging.
        
        Returns:
            dict: Rappresentazione completa dello stato interno.
        """
        return {
            "session_id": self.session_id,
            "phase": self.phase.value,
            "mode": self.mode,
            "session_duration_minutes": self.get_session_duration_minutes(),
            "conversation_summary": self.get_conversation_summary(),
            "has_ground_truth": self.ground_truth is not None,
            "has_evaluation": self.user_evaluation is not None,
            "has_result": self.evaluation_result is not None,
            "created_at": self.created_at.isoformat()
        }

    # ======== Integrazione Persistenza Streamlit ========

    @staticmethod
    def ensure_in_streamlit(st_session_state):
        """
        Inizializza l'oggetto SessionState all'interno dello stato globale di Streamlit
        se non è già presente. Garantisce che la sessione sopravviva ai re-run.
        
        Args:
            st_session_state (st.session_state): Oggetto di stato globale di Streamlit.
        
        Returns:
            SessionState: L'oggetto di sessione (nuovo o esistente).
        """
        if "tald_session" not in st_session_state:
            st_session_state["tald_session"] = SessionState()
        return st_session_state["tald_session"]

    def __str__(self) -> str:
        """Rappresentazione leggibile dello stato per debug."""
        return (
            f"SessionState(id={self.session_id}, phase={self.phase.value}, "
            f"mode={self.mode}, messages={self.conversation.get_message_count()})"
        )