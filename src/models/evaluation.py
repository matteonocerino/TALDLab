"""
Evaluation Models - Modelli per valutazioni e confronti

Questo modulo contiene le classi per gestire:
- La valutazione fornita dall'utente (Scheda completa o singolo voto)
- Il ground truth della simulazione (Uno o più disturbi in comorbilità)
- Il risultato del confronto vettoriale (Matrice di confusione TP/FP/FN)

Entity del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
"""

from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime


@dataclass
class UserEvaluation:
    """
    Rappresenta la valutazione fornita dall'utente al termine dell'intervista.
    
    Implementa le specifiche del RAD per la raccolta dati (RF_6).
    
    In modalità Esplorativa: rappresenta l'intera 'Scheda di Valutazione TALD',
    dove l'utente assegna un grado (0-4) a ciascuno dei 30 item.
    
    In modalità Guidata: contiene principalmente il voto per l'item target,
    
    Attributes:
        evaluation_sheet (Dict[int, int]): Mappa {item_id: grade}. 
                                           Es: {1: 0, 5: 3, 12: 2...}
                                           Rappresenta il vettore dei voti assegnati.
        notes (str): Note cliniche opzionali inserite dall'utente per 
                     giustificare la diagnosi.
        timestamp (datetime): Momento esatto della conferma della valutazione.
    
    Example:
        >>> # Utente identifica Crosstalk (5) moderato e Paraphasia (12) lieve
        >>> eval = UserEvaluation(
        ...     evaluation_sheet={5: 3, 12: 2}, 
        ...     notes="Eloquio difficile da seguire, nessi allentati."
        ... )
    """
    
    evaluation_sheet: Dict[int, int]
    notes: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        """
        Validazione dei dati e inizializzazione timestamp.
        
        Raises:
            ValueError: Se i dati non rispettano i vincoli strutturali o 
                        i range della scala TALD (0-4).
        """
        # Validazione tipo struttura dati
        if not isinstance(self.evaluation_sheet, dict):
            raise ValueError("Evaluation sheet deve essere un dizionario {id: grado}")
        
        # Validazione range voti (0-4 come da manuale TALD)
        for item_id, grade in self.evaluation_sheet.items():
            if not isinstance(grade, int) or not (0 <= grade <= 4):
                raise ValueError(f"Grado non valido per item {item_id}: {grade}. Deve essere int 0-4.")

        # Protezione note eccessivamente lunghe per compatibilità UI/DB
        if len(self.notes) > 5000:
            raise ValueError("Le note superano la lunghezza massima consentita (5000 caratteri).")
        
        # Imposta timestamp se non fornito
        if self.timestamp is None:
            self.timestamp = datetime.now()
            
    def get_grade_for_item(self, item_id: int) -> int:
        """
        Restituisce il voto assegnato dall'utente a uno specifico item.
        
        Args:
            item_id (int): L'ID dell'item TALD.
            
        Returns:
            int: Il grado assegnato (0 se l'item non è stato valutato esplicitamente).
        """
        return self.evaluation_sheet.get(item_id, 0)
    
    def to_dict(self) -> dict:
        """Converte l'oggetto in dizionario per serializzazione/log."""
        return {
            "evaluation_sheet": self.evaluation_sheet,
            "notes": self.notes,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class GroundTruth:
    """
    Rappresenta la configurazione reale della simulazione (la "verità").
    
    Supporta la comorbilità: può contenere più item attivi contemporaneamente con diversi gradi.
    
    Attributes:
        active_items (Dict[int, int]): Mappa dei disturbi attivi {item_id: grado}.
                                       Es: {5: 3, 12: 2} (Crosstalk grave + Paraphasia lieve).
                                       Tutti gli item non presenti in questa lista sono 
                                       implicitamente a grado 0 (assenti).
        mode (str): Modalità utilizzata ("guided" o "exploratory").
        timestamp (datetime): Momento di creazione della configurazione.
        
    Example:
        >>> # Simulazione complessa con due disturbi
        >>> gt = GroundTruth(
        ...     active_items={5: 3, 22: 2},
        ...     mode="exploratory"
        ... )
    """
    
    active_items: Dict[int, int]
    mode: str
    timestamp: datetime = None
    
    def __post_init__(self):
        """Validazione integrità configurazione simulazione."""
        # Validazione active_items
        if not isinstance(self.active_items, dict):
             raise ValueError("active_items deve essere un dizionario {id: grado}")

        # Validazione range gradi
        for item_id, grade in self.active_items.items():
            if not (0 <= grade <= 4):
                raise ValueError(f"Grado ground truth non valido per {item_id}. {grade}")

        # Validazione modalità
        if self.mode not in ["guided", "exploratory"]:
            raise ValueError(f"Mode non valido: {self.mode}")
            
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def is_guided_mode(self) -> bool:
        """Helper per verificare se la sessione è guidata."""
        return self.mode == "guided"
    
    def is_exploratory_mode(self) -> bool:
        """Helper per verificare se la sessione è esplorativa."""
        return self.mode == "exploratory"
        
    def get_primary_item(self) -> tuple[int, int]:
        """
        Restituisce l'item "principale" (utile per titoli o logica guidata).
        
        Se ci sono più item, ne restituisce uno arbitrario (il primo delle chiavi).
        Se non ci sono item (paziente sano), restituisce (0, 0).
        
        Returns:
            tuple: (item_id, grado)
        """
        if not self.active_items:
            return (0, 0)
        # Ordina per grado decrescente e prendi il primo
        primary_item = max(self.active_items.items(), key=lambda x: x[1])
        return primary_item

    def to_dict(self) -> dict:
        """Serializzazione."""
        return {
            "active_items": self.active_items,
            "mode": self.mode,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class EvaluationResult:
    """
    Rappresenta l'esito del confronto vettoriale (Scheda Utente vs Ground Truth).
    
    Implementa le metriche richieste dal RAD (RF_7) per la valutazione clinica:
    - True Positives (TP): Disturbi presenti e correttamente individuati.
    - False Positives (FP): "Allucinazioni diagnostiche" (visti ma non presenti).
    - False Negatives (FN): Omissioni (presenti ma non visti).
    
    Attributes:
        true_positives (List[int]): Lista ID item correttamente individuati (Grado > 0 in entrambi).
        false_positives (List[int]): Lista ID item segnalati dall'utente ma assenti nel GT.
        false_negatives (List[int]): Lista ID item presenti nel GT ma mancati dall'utente.
        grade_diffs (Dict[int, int]): Differenza di grado per gli item corretti {id: differenza}.
        score (int): Punteggio calcolato (0-100) basato su pesi configurabili.
        feedback_message (str): Messaggio descrittivo generato dal motore di confronto.
        timestamp (datetime): Data/ora del calcolo.
    """
    
    true_positives: List[int] = field(default_factory=list)
    false_positives: List[int] = field(default_factory=list)
    false_negatives: List[int] = field(default_factory=list)
    grade_diffs: Dict[int, int] = field(default_factory=dict)
    
    score: int = 0
    feedback_message: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        """Validazione range punteggio."""
        if not (0 <= self.score <= 100):
            # Clamp del punteggio per sicurezza
            self.score = max(0, min(100, self.score))
            
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def get_performance_level(self) -> str:
        """
        Determina il livello qualitativo della performance basato sul punteggio.
        
        Returns:
            str: Etichetta testuale (Eccellente, Buono, Sufficiente, ecc.)
        """
        if self.score >= 90: return "Eccellente"
        if self.score >= 75: return "Buono"
        if self.score >= 60: return "Sufficiente"
        if self.score >= 40: return "Migliorabile"
        return "Insufficiente"
        
    def is_passing_score(self) -> bool:
        """Verifica se la soglia di sufficienza (60/100) è raggiunta."""
        return self.score >= 60

    def to_dict(self) -> dict:
        """Serializzazione completa per report e log."""
        return {
            "metrics": {
                "TP": self.true_positives,
                "FP": self.false_positives,
                "FN": self.false_negatives
            },
            "grade_diffs": self.grade_diffs,
            "score": self.score,
            "feedback": self.feedback_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }