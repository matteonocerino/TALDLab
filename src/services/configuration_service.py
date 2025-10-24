"""
ConfigurationService - Servizio per caricamento e validazione configurazioni

Questo modulo gestisce il caricamento delle configurazioni dell'applicazione:
- Variabili d'ambiente (.env) per API keys e parametri LLM
- File tald_items.json con i 30 item della scala TALD
- Validazione di tutte le configurazioni critiche

Control del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
"""

import json
import os
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

import sys
sys.path.append(str(Path(__file__).parent.parent))

from models.tald_item import TALDItem


class ConfigurationError(Exception):
    """Eccezione personalizzata per errori di configurazione."""
    pass


class ConfigurationService:
    """
    Service per caricamento e validazione delle configurazioni di sistema.
    
    Responsabilità:
    - Caricare variabili d'ambiente da .env (RF_12)
    - Caricare e validare tald_items.json
    - Verificare integrità configurazione
    - Fornire valori di default sicuri
    
    Example:
        >>> config = ConfigurationService.load_env_config()
        >>> items = ConfigurationService.load_tald_items()
        >>> ConfigurationService.validate_configuration(config)
    """
    
    # Valori di default per configurazione LLM
    DEFAULT_MODEL = "gemini-1.5-pro"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 2048
    
    # Path relativi
    TALD_ITEMS_PATH = "tald_items.json"
    ENV_FILE_PATH = ".env"
    
    @staticmethod
    def load_env_config() -> Dict[str, any]:
        """
        Carica la configurazione dalle variabili d'ambiente.
        
        Legge il file .env e estrae:
        - GEMINI_API_KEY: Chiave API per Google Gemini
        - GEMINI_MODEL: Modello da utilizzare (default: gemini-1.5-pro)
        - GEMINI_TEMPERATURE: Temperatura per generazione (default: 0.7)
        - GEMINI_MAX_TOKENS: Token massimi per risposta (default: 2048)
        
        Returns:
            dict: Configurazione con chiavi api_key, model, temperature, max_tokens
            
        Raises:
            ConfigurationError: Se ci sono problemi critici nella configurazione
            
        Note:
            Se l'API key non è presente, viene restituita None con un warning.
            L'applicazione può comunque avviarsi per testare altre funzionalità.
        """
        # Carica variabili d'ambiente dal file .env se esiste
        env_path = Path(ConfigurationService.ENV_FILE_PATH)
        
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # File .env non trovato, usa solo variabili di sistema
            load_dotenv()  # Carica da variabili di sistema se presenti
        
        # Estrai API key
        api_key = os.getenv('GEMINI_API_KEY')
        
        # Estrai parametri con valori di default
        model = os.getenv('GEMINI_MODEL', ConfigurationService.DEFAULT_MODEL)
        
        try:
            temperature = float(os.getenv('GEMINI_TEMPERATURE', ConfigurationService.DEFAULT_TEMPERATURE))
        except ValueError:
            temperature = ConfigurationService.DEFAULT_TEMPERATURE
        
        try:
            max_tokens = int(os.getenv('GEMINI_MAX_TOKENS', ConfigurationService.DEFAULT_MAX_TOKENS))
        except ValueError:
            max_tokens = ConfigurationService.DEFAULT_MAX_TOKENS
        
        # Validazione parametri
        if temperature < 0 or temperature > 2:
            raise ConfigurationError(
                f"GEMINI_TEMPERATURE deve essere tra 0 e 2, ricevuto: {temperature}"
            )
        
        if max_tokens < 100 or max_tokens > 8192:
            raise ConfigurationError(
                f"GEMINI_MAX_TOKENS deve essere tra 100 e 8192, ricevuto: {max_tokens}"
            )
        
        config = {
            'api_key': api_key,
            'model': model,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        # Warning se API key mancante (non bloccante)
        if not api_key:
            print("\nWARNING: GEMINI_API_KEY non trovata!")
            print("   L'applicazione può avviarsi ma l'LLM non funzionerà.")
            print("   Per ottenere una API key:")
            print("   1. Vai su: https://aistudio.google.com/app/apikey")
            print("   2. Crea una nuova API key")
            print("   3. Copia il file .env.example in .env")
            print("   4. Inserisci la tua API key nel file .env")
            print()
        
        return config
    
    @staticmethod
    def load_tald_items() -> List[TALDItem]:
        """
        Carica i 30 item TALD dal file JSON.
        
        Legge tald_items.json, valida la struttura e crea gli oggetti TALDItem.
        Verifica che ci siano esattamente 30 item come da manuale TALD.
        
        Returns:
            List[TALDItem]: Lista dei 30 item TALD ordinati per ID
            
        Raises:
            ConfigurationError: Se il file manca, è malformato o non contiene 30 item
            
        Example:
            >>> items = ConfigurationService.load_tald_items()
            >>> len(items)
            30
            >>> items[0].title
            'Circumstantiality'
        """
        json_path = Path(ConfigurationService.TALD_ITEMS_PATH)
        
        # Verifica esistenza file
        if not json_path.exists():
            raise ConfigurationError(
                f"File {ConfigurationService.TALD_ITEMS_PATH} non trovato!\n"
                f"Assicurati che il file sia nella directory root del progetto."
            )
        
        # Carica e valida JSON
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Errore nel parsing di {ConfigurationService.TALD_ITEMS_PATH}: {e}\n"
                f"Il file JSON è malformato."
            )
        except Exception as e:
            raise ConfigurationError(
                f"Errore nella lettura di {ConfigurationService.TALD_ITEMS_PATH}: {e}"
            )
        
        # Valida struttura JSON
        if 'items' not in data:
            raise ConfigurationError(
                f"Struttura JSON non valida: chiave 'items' mancante in {ConfigurationService.TALD_ITEMS_PATH}"
            )
        
        items_data = data['items']
        
        if not isinstance(items_data, list):
            raise ConfigurationError(
                f"Struttura JSON non valida: 'items' deve essere una lista"
            )
        
        # Verifica numero di item
        if len(items_data) != 30:
            raise ConfigurationError(
                f"Numero di item non valido: trovati {len(items_data)}, richiesti 30.\n"
                f"Il manuale TALD definisce esattamente 30 item."
            )
        
        # Crea oggetti TALDItem
        tald_items = []
        errors = []
        
        for idx, item_data in enumerate(items_data, 1):
            try:
                item = TALDItem.from_dict(item_data)
                tald_items.append(item)
            except Exception as e:
                errors.append(f"Item {idx}: {str(e)}")
        
        # Se ci sono errori di validazione, solleva eccezione
        if errors:
            error_msg = "Errori di validazione negli item TALD:\n" + "\n".join(errors)
            raise ConfigurationError(error_msg)
        
        # Ordina per ID per sicurezza
        tald_items.sort(key=lambda x: x.id)
        
        # Verifica che gli ID siano consecutivi 1-30
        expected_ids = set(range(1, 31))
        actual_ids = {item.id for item in tald_items}
        
        if expected_ids != actual_ids:
            missing = expected_ids - actual_ids
            extra = actual_ids - expected_ids
            raise ConfigurationError(
                f"ID degli item non validi.\n"
                f"ID mancanti: {sorted(missing) if missing else 'nessuno'}\n"
                f"ID duplicati/extra: {sorted(extra) if extra else 'nessuno'}"
            )
        
        return tald_items
    
    @staticmethod
    def validate_configuration(config: Dict[str, any]) -> bool:
        """
        Valida la completezza della configurazione.
        
        Verifica che tutti i campi necessari siano presenti e validi.
        Viene chiamato dopo load_env_config() per controllo finale.
        
        Args:
            config (dict): Dizionario configurazione da validare
            
        Returns:
            bool: True se configurazione valida
            
        Raises:
            ConfigurationError: Se la configurazione non è valida
        """
        required_keys = ['api_key', 'model', 'temperature', 'max_tokens']
        
        # Verifica presenza chiavi
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ConfigurationError(
                f"Configurazione incompleta. Chiavi mancanti: {', '.join(missing_keys)}"
            )
        
        # Verifica model non vuoto
        if not config['model'] or not isinstance(config['model'], str):
            raise ConfigurationError("Il campo 'model' deve essere una stringa non vuota")
        
        # Verifica temperature range
        if not isinstance(config['temperature'], (int, float)):
            raise ConfigurationError("Il campo 'temperature' deve essere numerico")
        
        if config['temperature'] < 0 or config['temperature'] > 2:
            raise ConfigurationError(
                f"'temperature' deve essere tra 0 e 2, valore: {config['temperature']}"
            )
        
        # Verifica max_tokens range
        if not isinstance(config['max_tokens'], int):
            raise ConfigurationError("Il campo 'max_tokens' deve essere un intero")
        
        if config['max_tokens'] < 100 or config['max_tokens'] > 8192:
            raise ConfigurationError(
                f"'max_tokens' deve essere tra 100 e 8192, valore: {config['max_tokens']}"
            )
        
        # API key può essere None (warning già mostrato in load_env_config)
        # Non blocchiamo la validazione se manca
        
        return True
    
    @staticmethod
    def get_item_by_id(items: List[TALDItem], item_id: int) -> Optional[TALDItem]:
        """
        Trova un item TALD per ID.
        
        Args:
            items (List[TALDItem]): Lista completa degli item
            item_id (int): ID dell'item da cercare (1-30)
            
        Returns:
            TALDItem: Item trovato, None se non esiste
            
        Example:
            >>> items = ConfigurationService.load_tald_items()
            >>> item = ConfigurationService.get_item_by_id(items, 5)
            >>> item.title
            'Crosstalk'
        """
        for item in items:
            if item.id == item_id:
                return item
        return None
    
    @staticmethod
    def get_items_by_type(items: List[TALDItem], item_type: str) -> List[TALDItem]:
        """
        Filtra gli item per tipo (objective o subjective).
        
        Args:
            items (List[TALDItem]): Lista completa degli item
            item_type (str): "objective" o "subjective"
            
        Returns:
            List[TALDItem]: Item del tipo specificato
            
        Example:
            >>> items = ConfigurationService.load_tald_items()
            >>> objective_items = ConfigurationService.get_items_by_type(items, "objective")
            >>> len(objective_items)
            21
        """
        if item_type not in ["objective", "subjective"]:
            raise ValueError(f"Tipo deve essere 'objective' o 'subjective', ricevuto: {item_type}")
        
        return [item for item in items if item.type == item_type]
    
    @staticmethod
    def print_configuration_summary(config: Dict[str, any], items: List[TALDItem]):
        """
        Stampa un riepilogo della configurazione caricata.
        
        Utile per debugging e verifica durante lo sviluppo.
        
        Args:
            config (dict): Configurazione LLM
            items (List[TALDItem]): Item TALD caricati
        """
        print("\n" + "="*60)
        print("CONFIGURAZIONE TALDLab")
        print("="*60)
        
        print("\nConfigurazione LLM:")
        print(f"   Modello: {config['model']}")
        print(f"   Temperature: {config['temperature']}")
        print(f"   Max Tokens: {config['max_tokens']}")
        print(f"   API Key: {'Configurata' if config['api_key'] else 'Mancante'}")
        
        print(f"\nItem TALD caricati: {len(items)}")
        objective = [i for i in items if i.is_objective()]
        subjective = [i for i in items if i.is_subjective()]
        print(f"   - Objective: {len(objective)}")
        print(f"   - Subjective: {len(subjective)}")
        
        print("\n" + "="*60 + "\n")