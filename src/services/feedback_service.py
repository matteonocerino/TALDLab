"""
FeedbackService - Servizio per gestione feedback utenti

Questo modulo gestisce la raccolta, la validazione e la persistenza dei feedback
qualitativi forniti dagli utenti al termine della simulazione.

Responsabilità principali:
- Validazione formale dei dati di input (range numerici, lunghezza testi)
- Costruzione dell'entità Feedback (Entity)
- Anonimizzazione dei dati (esclusione di identificativi personali)
- Persistenza su filesystem (JSON) con gestione della concorrenza
- Calcolo statistiche aggregate per monitoraggio qualità

Pattern Architetturale: Control (Componente della logica di business)
Riferimento RAD: Sezione 2.6.1 (Dizionario dei dati - FeedbackService)
Implementa Requisito Funzionale: RF_10
"""

import json
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

# Lock per gestire l'accesso concorrente al file JSON (Thread-Safety)
# Necessario se più utenti (o thread) provano a scrivere contemporaneamente.
_file_lock = threading.Lock()


class Feedback:
    """
    Entity che rappresenta un singolo feedback utente.
    
    Incapsula i dati valutativi e i metadati della sessione, garantendo
    che la struttura dati sia coerente prima della serializzazione.
    
    Attributes:
        overall_rating (Optional[int]): Valutazione generale (scala 1-5)
        realism_rating (Optional[int]): Realismo percepito (scala 1-5)
        usefulness_rating (Optional[int]): Utilità didattica (scala 1-5)
        comments (str): Commenti qualitativi liberi
        metadata (Dict): Dati di contesto non identificativi (item, modalità)
        timestamp (datetime): Marca temporale di creazione
    """
    
    def __init__(
        self,
        overall_rating: Optional[int],
        realism_rating: Optional[int],
        usefulness_rating: Optional[int],
        comments: str,
        metadata: Dict[str, Any]
    ):
        self.overall_rating = overall_rating
        self.realism_rating = realism_rating
        self.usefulness_rating = usefulness_rating
        self.comments = comments
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serializza l'entità in un dizionario compatibile con JSON.
        
        Returns:
            Dict: Rappresentazione strutturata del feedback.
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "ratings": {
                "overall": self.overall_rating,
                "realism": self.realism_rating,
                "usefulness": self.usefulness_rating
            },
            "comments": self.comments,
            "metadata": self.metadata
        }


class FeedbackService:
    """
    Service (Control) per la gestione del ciclo di vita dei feedback.
    
    Questa classe funge da interfaccia tra la View (FeedbackForm) e il livello
    di persistenza dati (File System). Implementa controlli di integrità
    e logiche di aggregazione.
    """
    
    # Percorso del file di persistenza
    FEEDBACK_FILE = Path("feedback_log.json")
    
    @staticmethod
    def _validate_rating(value: Any, field_name: str) -> Optional[int]:
        """
        Validazione interna per i valori numerici di rating.
        
        Args:
            value: Il valore da controllare (può essere None, int, str).
            field_name: Nome del campo per messaggi di errore.
            
        Returns:
            Optional[int]: Il valore intero validato o None.
            
        Raises:
            ValueError: Se il valore non è un intero valido tra 1 e 5.
        """
        if value is None:
            return None
            
        try:
            int_val = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Il campo '{field_name}' deve essere un numero.")
            
        if not (1 <= int_val <= 5):
            raise ValueError(f"Il campo '{field_name}' deve essere compreso tra 1 e 5.")
            
        return int_val

    @staticmethod
    def _validate_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitizza i metadati per assicurare che non contengano dati sensibili
        imprevisti e abbiano la struttura minima richiesta.
        """
        if not metadata:
            return {}
            
        # Garantiamo che vengano salvati solo i campi attesi per la ricerca
        return {
            "item_id": metadata.get("item_id"),
            "item_title": str(metadata.get("item_title", "Unknown")),
            "mode": str(metadata.get("mode", "Unknown")),
            "score": metadata.get("score")
        }

    @staticmethod
    def save_feedback(feedback_data: Dict[str, Any], metadata: Dict[str, Any]) -> bool:
        """
        Elabora, valida e salva un nuovo feedback utente.
        
        Il metodo gestisce l'intero flusso di persistenza garantendo la thread-safety
        tramite un meccanismo di Lock, prevenendo la corruzione del file JSON
        in caso di accessi concorrenti.
        
        Args:
            feedback_data (dict): Dizionario contenente i voti e i commenti.
            metadata (dict): Informazioni di contesto sulla sessione.
            
        Returns:
            bool: True se il salvataggio ha successo.
            
        Raises:
            ValueError: Se i dati non sono validi o il feedback è vuoto.
            IOError: Se si verificano errori di scrittura su disco.
        """
        
        # 1. Validazione Formale degli Input
        # Verifichiamo che i rating siano nel range corretto (1-5)
        overall = FeedbackService._validate_rating(feedback_data.get("overall_rating"), "Overall")
        realism = FeedbackService._validate_rating(feedback_data.get("realism_rating"), "Realism")
        usefulness = FeedbackService._validate_rating(feedback_data.get("usefulness_rating"), "Usefulness")
        
        comments = str(feedback_data.get("comments", "")).strip()
        
        # 2. Controllo di Rilevanza
        # Impediamo il salvataggio di feedback completamente vuoti
        if not any([overall, realism, usefulness, comments]):
            raise ValueError("Impossibile salvare un feedback vuoto.")

        # 3. Creazione dell'Entity
        clean_metadata = FeedbackService._validate_metadata(metadata)
        
        feedback_entity = Feedback(
            overall_rating=overall,
            realism_rating=realism,
            usefulness_rating=usefulness,
            comments=comments,
            metadata=clean_metadata
        )
        
        entry_to_save = feedback_entity.to_dict()

        # 4. Persistenza Thread-Safe (Sezione Critica)
        with _file_lock:
            try:
                current_data: List[Dict] = []
                
                # A. Lettura dati esistenti (se il file esiste)
                if FeedbackService.FEEDBACK_FILE.exists():
                    with open(FeedbackService.FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                        try:
                            file_content = json.load(f)
                            if isinstance(file_content, list):
                                current_data = file_content
                        except json.JSONDecodeError:
                            # Se il file è corrotto, lo sovrascriviamo reinizializzando la lista
                            current_data = []
                
                # B. Append del nuovo dato
                current_data.append(entry_to_save)
                
                # C. Scrittura atomica (si spera) sul file
                with open(FeedbackService.FEEDBACK_FILE, 'w', encoding='utf-8') as f:
                    json.dump(current_data, f, ensure_ascii=False, indent=2)
                    
                return True
                
            except Exception as e:
                # Log dell'errore (in produzione andrebbe su un file di log vero)
                print(f"[ERROR] Feedback persistence failed: {e}")
                raise IOError(f"Errore critico nel salvataggio del feedback: {str(e)}")

    @staticmethod
    def get_feedback_statistics() -> Dict[str, Any]:
        """
        Calcola statistiche aggregate sui feedback raccolti.
        
        Utile per fornire un riscontro immediato all'utente ("Media voti: 4.5").
        Legge il file JSON e calcola le medie aritmetiche dei rating.
        
        Returns:
            Dict: Dizionario contenente conteggi e medie.
                  Es: {'count': 10, 'avg_overall': 4.2}
        """
        stats = {
            "count": 0,
            "avg_overall": 0.0,
            "avg_realism": 0.0
        }
        
        if not FeedbackService.FEEDBACK_FILE.exists():
            return stats

        try:
            with open(FeedbackService.FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if not data or not isinstance(data, list):
                return stats
            
            total_count = len(data)
            
            # Estrazione liste di voti (filtrando i None)
            overalls = [d['ratings']['overall'] for d in data if d['ratings'].get('overall')]
            realisms = [d['ratings']['realism'] for d in data if d['ratings'].get('realism')]
            
            # Calcolo Medie
            avg_overall = sum(overalls) / len(overalls) if overalls else 0
            avg_realism = sum(realisms) / len(realisms) if realisms else 0
            
            return {
                "count": total_count,
                "avg_overall": round(avg_overall, 1),
                "avg_realism": round(avg_realism, 1)
            }
            
        except Exception as e:
            print(f"[WARNING] Errore nel calcolo statistiche: {e}")
            return stats