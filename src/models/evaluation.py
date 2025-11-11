"""
Evaluation Models - Modelli per valutazioni e confronti

Questo modulo contiene le classi per gestire:
- La valutazione fornita dall'utente
- Il ground truth della simulazione
- Il risultato del confronto tra valutazione e ground truth

Entity del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class UserEvaluation:
    """
    Rappresenta la valutazione fornita dall'utente al termine dell'intervista.
    
    Attributes:
        grade (int): Grado attribuito dall'utente sulla scala TALD (0-4)
        item_id (Optional[int]): ID dell'item identificato (solo modalità esplorativa)
        notes (str): Note opzionali dell'utente
        timestamp (datetime): Momento della valutazione
    
    Example:
        >>> # Modalità guidata (item già noto)
        >>> eval_guided = UserEvaluation(
        ...     grade=3,
        ...     item_id=None,
        ...     notes="Il paziente mostrava segni chiari"
        ... )
        >>> 
        >>> # Modalità esplorativa (utente identifica l'item)
        >>> eval_exploratory = UserEvaluation(
        ...     grade=2,
        ...     item_id=5,
        ...     notes="Crosstalk evidente nelle risposte"
        ... )
    """
    
    grade: int
    item_id: Optional[int] = None
    notes: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        """Validazione e inizializzazione timestamp."""
        # Validazione grade
        if not isinstance(self.grade, int) or not (0 <= self.grade <= 4):
            raise ValueError(f"Grade deve essere un intero tra 0 e 4, ricevuto: {self.grade}")
        
        # Validazione item_id (se presente)
        if self.item_id is not None and not (1 <= self.item_id <= 30):
            raise ValueError(f"Item ID deve essere tra 1 e 30, ricevuto: {self.item_id}")
        
        # Protezione da note eccessivamente lunghe per compatibilità UI Streamlit
        if len(self.notes) > 2000:
            raise ValueError("Notes eccede la lunghezza massima consentita (2000 caratteri).")
        
        # Imposta timestamp se non fornito
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def is_exploratory_mode(self) -> bool:
        """
        Determina se la valutazione è in modalità esplorativa.
        
        Returns:
            bool: True se item_id è specificato (modalità esplorativa)
        """
        return self.item_id is not None
    
    def to_dict(self) -> dict:
        """
        Converte la valutazione in dizionario.
        
        Returns:
            dict: Rappresentazione dizionario
        """
        return {
            "grade": self.grade,
            "item_id": self.item_id,
            "notes": self.notes,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class GroundTruth:
    """
    Rappresenta la configurazione effettiva utilizzata nella simulazione.
    
    Attributes:
        item_id (int): ID dell'item TALD effettivamente simulato
        item_title (str): Titolo dell'item per reference veloce
        grade (int): Grado impostato per la simulazione (0-4)
        mode (str): Modalità utilizzata ("guided" o "exploratory")
        timestamp (datetime): Momento di creazione del ground truth
    
    Example:
        >>> gt = GroundTruth(
        ...     item_id=5,
        ...     item_title="Crosstalk",
        ...     grade=2,
        ...     mode="exploratory"
        ... )
        >>> print(gt.is_guided_mode())
        False
    """
    
    item_id: int
    item_title: str
    grade: int
    mode: str
    timestamp: datetime = None
    
    def __post_init__(self):
        """Validazione dati."""
        # Validazione item_id
        if not (1 <= self.item_id <= 30):
            raise ValueError(f"Item ID deve essere tra 1 e 30, ricevuto: {self.item_id}")
        
        # Validazione grade
        if not (0 <= self.grade <= 4):
            raise ValueError(f"Grade deve essere tra 0 e 4, ricevuto: {self.grade}")
        
        # Validazione mode
        if self.mode not in ["guided", "exploratory"]:
            raise ValueError(
                f"Mode deve essere 'guided' o 'exploratory', ricevuto: {self.mode}"
            )
        
        # Protezione da titolo vuoto o errato
        if not self.item_title or not isinstance(self.item_title, str):
            raise ValueError("Item title non può essere vuoto o non testuale.")
        
        # Imposta timestamp se non fornito
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def is_guided_mode(self) -> bool:
        """
        Verifica se la simulazione era in modalità guidata.
        
        Returns:
            bool: True se modalità guidata
        """
        return self.mode == "guided"
    
    def is_exploratory_mode(self) -> bool:
        """
        Verifica se la simulazione era in modalità esplorativa.
        
        Returns:
            bool: True se modalità esplorativa
        """
        return self.mode == "exploratory"
    
    def to_dict(self) -> dict:
        """
        Converte il ground truth in dizionario.
        
        Returns:
            dict: Rappresentazione dizionario
        """
        return {
            "item_id": self.item_id,
            "item_title": self.item_title,
            "grade": self.grade,
            "mode": self.mode,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class EvaluationResult:
    """
    Rappresenta l'esito del confronto tra valutazione utente e ground truth.
    
    Attributes:
        item_correct (Optional[bool]): True se item identificato correttamente 
                                       (None in modalità guidata)
        grade_correct (bool): True se grado attribuito correttamente
        grade_difference (int): Differenza assoluta tra grado utente e ground truth
        score (int): Punteggio complessivo (0-100)
        feedback_message (str): Messaggio di feedback generato
        timestamp (datetime): Momento della valutazione
    
    Example:
        >>> result = EvaluationResult(
        ...     item_correct=True,
        ...     grade_correct=False,
        ...     grade_difference=1,
        ...     score=75,
        ...     feedback_message="Item corretto, grado leggermente impreciso"
        ... )
        >>> print(result.is_perfect_score())
        False
    """
    
    item_correct: Optional[bool]
    grade_correct: bool
    grade_difference: int
    score: int
    feedback_message: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        """Validazione e inizializzazione."""
        # Validazione grade_difference
        if not (0 <= self.grade_difference <= 4):
            raise ValueError(
                f"Grade difference deve essere tra 0 e 4, ricevuto: {self.grade_difference}"
            )
        
        # Validazione score
        if not (0 <= self.score <= 100):
            raise ValueError(f"Score deve essere tra 0 e 100, ricevuto: {self.score}")

        # Pulizia messaggio per compatibilità visuale
        self.feedback_message = (self.feedback_message or "").strip()
        if len(self.feedback_message) > 2000:
            self.feedback_message = self.feedback_message[:2000]
        
        # Imposta timestamp se non fornito
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def is_perfect_score(self) -> bool:
        """
        Verifica se la valutazione è perfetta (punteggio massimo).
        
        Returns:
            bool: True se score = 100
        """
        return self.score == 100
    
    def is_passing_score(self, threshold: int = 60) -> bool:
        """
        Verifica se il punteggio supera una soglia minima.
        
        Args:
            threshold (int): Soglia minima (default: 60)
            
        Returns:
            bool: True se score >= threshold
        """
        return self.score >= threshold
    
    def get_performance_level(self) -> str:
        """
        Determina il livello di performance basato sul punteggio.
        
        Returns:
            str: Livello di performance ("Eccellente", "Buono", "Sufficiente", "Insufficiente")
        """
        if self.score >= 90:
            return "Eccellente"
        elif self.score >= 75:
            return "Buono"
        elif self.score >= 60:
            return "Sufficiente"
        else:
            return "Insufficiente"
    
    def to_dict(self) -> dict:
        """
        Converte il risultato in dizionario.
        
        Returns:
            dict: Rappresentazione dizionario
        """
        return {
            "item_correct": self.item_correct,
            "grade_correct": self.grade_correct,
            "grade_difference": self.grade_difference,
            "score": self.score,
            "feedback_message": self.feedback_message,
            "performance_level": self.get_performance_level(),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }