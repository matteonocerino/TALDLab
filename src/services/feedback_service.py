"""
FeedbackService - Servizio per gestione feedback utenti

Questo modulo gestisce la raccolta, la validazione e la persistenza dei feedback
qualitativi forniti dagli utenti al termine della simulazione.

Responsabilità principali:
- Validazione formale dei dati di input (range numerici 1-5, lunghezza testi)
- Costruzione dell'entità Feedback (Entity) con i 5 campi richiesti (S1-S4 + Commenti)
- Anonimizzazione dei dati (esclusione di identificativi personali)
- Persistenza su filesystem (JSON) con gestione della concorrenza

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
_file_lock = threading.Lock()


class Feedback:
    """
    Entity che rappresenta un singolo feedback utente.
    
    Implementa la struttura definita nel RAD (RF_10):
    4 metriche quantitative su scala 1-5 e un campo qualitativo.
    
    Attributes:
        score_accuracy (int): Accuratezza del punteggio TALD (1-5)
        explanation_quality (int): Qualità della spiegazione clinica (1-5)
        overall_satisfaction (int): Soddisfazione generale (1-5)
        simulation_realism (int): Realismo della simulazione (1-5)
        comments (str): Note qualitative libere
        metadata (Dict): Dati di contesto non identificativi (item, modalità)
        timestamp (datetime): Marca temporale di creazione
    """
    
    def __init__(
        self,
        score_accuracy: Optional[int],
        explanation_quality: Optional[int],
        overall_satisfaction: Optional[int],
        simulation_realism: Optional[int],
        comments: str,
        metadata: Dict[str, Any]
    ):
        self.score_accuracy = score_accuracy
        self.explanation_quality = explanation_quality
        self.overall_satisfaction = overall_satisfaction
        self.simulation_realism = simulation_realism
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
                "score_accuracy": self.score_accuracy,
                "explanation_quality": self.explanation_quality,
                "overall_satisfaction": self.overall_satisfaction,
                "simulation_realism": self.simulation_realism
            },
            "comments": self.comments,
            "metadata": self.metadata
        }


class FeedbackService:
    """
    Service (Control) per la gestione del ciclo di vita dei feedback.
    
    Questa classe funge da interfaccia tra la View (FeedbackForm) e il livello
    di persistenza dati (File System).
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
        
        Il metodo gestisce l'intero flusso di persistenza garantendo la thread-safety.
        
        Args:
            feedback_data (dict): Dizionario contenente i voti S1-S4 e i commenti.
            metadata (dict): Informazioni di contesto sulla sessione.
            
        Returns:
            bool: True se il salvataggio ha successo.
            
        Raises:
            ValueError: Se i dati non sono validi o il feedback è vuoto.
            IOError: Se si verificano errori di scrittura su disco.
        """
        
        # 1. Validazione Formale degli Input 
        s1 = FeedbackService._validate_rating(feedback_data.get("score_accuracy"), "Accuracy")
        s2 = FeedbackService._validate_rating(feedback_data.get("explanation_quality"), "Explanation")
        s3 = FeedbackService._validate_rating(feedback_data.get("overall_satisfaction"), "Satisfaction")
        s4 = FeedbackService._validate_rating(feedback_data.get("simulation_realism"), "Realism")
        
        comments = str(feedback_data.get("comments", "")).strip()
        
        # 2. Controllo di Rilevanza
        # Impediamo il salvataggio di feedback completamente vuoti
        if not any([s1, s2, s3, s4, comments]):
            raise ValueError("Impossibile salvare un feedback vuoto. Compilare almeno un campo.")

        # 3. Creazione dell'Entity
        clean_metadata = FeedbackService._validate_metadata(metadata)
        
        feedback_entity = Feedback(
            score_accuracy=s1,
            explanation_quality=s2,
            overall_satisfaction=s3,
            simulation_realism=s4,
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
                
                # C. Scrittura atomica sul file
                with open(FeedbackService.FEEDBACK_FILE, 'w', encoding='utf-8') as f:
                    json.dump(current_data, f, ensure_ascii=False, indent=2)
                    
                return True
                
            except Exception as e:
                print(f"[ERROR] Feedback persistence failed: {e}")
                raise IOError(f"Errore critico nel salvataggio del feedback: {str(e)}")

    @staticmethod
    def get_feedback_statistics() -> Dict[str, Any]:
        """
        Calcola statistiche aggregate sui feedback raccolti.
        
        Returns:
            Dict: Conteggi e medie per S1, S2, S3, S4.
        """
        stats = {
            "count": 0,
            "avg_s1": 0.0,
            "avg_s2": 0.0,
            "avg_s3": 0.0,
            "avg_s4": 0.0
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
            s1_list = [d['ratings']['score_accuracy'] for d in data if d['ratings'].get('score_accuracy')]
            s2_list = [d['ratings']['explanation_quality'] for d in data if d['ratings'].get('explanation_quality')]
            s3_list = [d['ratings']['overall_satisfaction'] for d in data if d['ratings'].get('overall_satisfaction')]
            s4_list = [d['ratings']['simulation_realism'] for d in data if d['ratings'].get('simulation_realism')]
            
            # Calcolo Medie
            stats["count"] = total_count
            stats["avg_s1"] = round(sum(s1_list) / len(s1_list), 1) if s1_list else 0
            stats["avg_s2"] = round(sum(s2_list) / len(s2_list), 1) if s2_list else 0
            stats["avg_s3"] = round(sum(s3_list) / len(s3_list), 1) if s3_list else 0
            stats["avg_s4"] = round(sum(s4_list) / len(s4_list), 1) if s4_list else 0
            
            return stats
            
        except Exception as e:
            print(f"[WARNING] Errore nel calcolo statistiche: {e}")
            return stats