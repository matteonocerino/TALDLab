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
from typing import List, Dict, Optional, Any
from pathlib import Path
from dotenv import load_dotenv

from ..models.tald_item import TALDItem


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
    
    DEFAULT_MODEL = "gemini-2.5-pro"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 2048

    TALD_ITEMS_PATH = Path("tald_items.json")
    ENV_FILE_PATH = Path(".env")

    @staticmethod
    def load_env_config() -> Dict[str, Any]:
        """
        Carica la configurazione dalle variabili d'ambiente.
        
        Legge il file .env e estrae:
        - GEMINI_API_KEY
        - GEMINI_MODEL
        - GEMINI_TEMPERATURE
        - GEMINI_MAX_TOKENS
        """
        env_path = ConfigurationService.ENV_FILE_PATH
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", ConfigurationService.DEFAULT_MODEL)

        try:
            temperature = float(os.getenv("GEMINI_TEMPERATURE", ConfigurationService.DEFAULT_TEMPERATURE))
        except ValueError:
            temperature = ConfigurationService.DEFAULT_TEMPERATURE

        try:
            max_tokens = int(os.getenv("GEMINI_MAX_TOKENS", ConfigurationService.DEFAULT_MAX_TOKENS))
        except ValueError:
            max_tokens = ConfigurationService.DEFAULT_MAX_TOKENS

        if not (0 <= temperature <= 2):
            raise ConfigurationError(f"GEMINI_TEMPERATURE deve essere tra 0 e 2, ricevuto: {temperature}")

        if not (100 <= max_tokens <= 8192):
            raise ConfigurationError(f"GEMINI_MAX_TOKENS deve essere tra 100 e 8192, ricevuto: {max_tokens}")

        config = {
            "api_key": api_key,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if not api_key:
            print("\nWARNING: GEMINI_API_KEY non trovata!")
            print("   L'applicazione può avviarsi ma l'LLM non funzionerà.")
            print("   Per ottenere una API key:")
            print("   1. Vai su: https://aistudio.google.com/app/apikey")
            print("   2. Crea una nuova API key")
            print("   3. Copia il file .env.example in .env")
            print("   4. Inserisci la tua API key nel file .env\n")

        return config

    @staticmethod
    def load_tald_items() -> List[TALDItem]:
        """
        Carica i 30 item TALD dal file JSON.
        """
        json_path = ConfigurationService.TALD_ITEMS_PATH
        if not json_path.exists():
            raise ConfigurationError(
                f"File {json_path} non trovato! Assicurati che sia nella root del progetto."
            )

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Errore nel parsing di {json_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Errore nella lettura di {json_path}: {e}")

        if "items" not in data or not isinstance(data["items"], list):
            raise ConfigurationError("Struttura JSON non valida: chiave 'items' mancante o non lista")

        items_data = data["items"]
        if len(items_data) != 30:
            raise ConfigurationError(
                f"Numero di item non valido: trovati {len(items_data)}, richiesti 30."
            )

        tald_items: List[TALDItem] = []
        errors: List[str] = []

        for idx, item_data in enumerate(items_data, 1):
            try:
                tald_items.append(TALDItem.from_dict(item_data))
            except Exception as e:
                errors.append(f"Item {idx}: {e}")

        if errors:
            raise ConfigurationError("Errori di validazione negli item TALD:\n" + "\n".join(errors))

        tald_items.sort(key=lambda x: x.id)
        expected_ids = set(range(1, 31))
        actual_ids = {item.id for item in tald_items}

        if expected_ids != actual_ids:
            missing = expected_ids - actual_ids
            extra = actual_ids - expected_ids
            raise ConfigurationError(
                f"ID degli item non validi.\n"
                f"ID mancanti: {sorted(missing) if missing else 'nessuno'}\n"
                f"ID extra: {sorted(extra) if extra else 'nessuno'}"
            )

        return tald_items

    @staticmethod
    def validate_configuration(config: Dict[str, Any]) -> bool:
        """
        Valida la completezza della configurazione.
        """
        required = ["api_key", "model", "temperature", "max_tokens"]
        missing = [k for k in required if k not in config]
        if missing:
            raise ConfigurationError(f"Configurazione incompleta: chiavi mancanti {missing}")

        if not isinstance(config["model"], str) or not config["model"].strip():
            raise ConfigurationError("Il campo 'model' deve essere una stringa non vuota")

        if not isinstance(config["temperature"], (int, float)) or not (0 <= config["temperature"] <= 2):
            raise ConfigurationError("Il campo 'temperature' deve essere numerico tra 0 e 2")

        if not isinstance(config["max_tokens"], int) or not (100 <= config["max_tokens"] <= 8192):
            raise ConfigurationError("Il campo 'max_tokens' deve essere un intero tra 100 e 8192")

        return True

    @staticmethod
    def get_item_by_id(items: List[TALDItem], item_id: int) -> Optional[TALDItem]:
        """
        Trova un item TALD per ID.
        """
        return next((item for item in items if item.id == item_id), None)

    @staticmethod
    def get_items_by_type(items: List[TALDItem], item_type: str) -> List[TALDItem]:
        """
        Filtra gli item per tipo (objective o subjective).
        """
        if item_type not in ("objective", "subjective"):
            raise ValueError(f"Tipo non valido: {item_type}")
        return [item for item in items if item.type == item_type]

    @staticmethod
    def print_configuration_summary(config: Dict[str, Any], items: List[TALDItem]):
        """
        Stampa un riepilogo della configurazione caricata.
        """
        print("\n" + "=" * 60)
        print("CONFIGURAZIONE TALDLab")
        print("=" * 60)

        print("\nConfigurazione LLM:")
        print(f"   Modello: {config['model']}")
        print(f"   Temperature: {config['temperature']}")
        print(f"   Max Tokens: {config['max_tokens']}")
        print(f"   API Key: {'Configurata' if config['api_key'] else 'Mancante'}")

        print(f"\nItem TALD caricati: {len(items)}")
        objective = sum(1 for i in items if i.is_objective())
        subjective = sum(1 for i in items if i.is_subjective())
        print(f"   - Objective: {objective}")
        print(f"   - Subjective: {subjective}")

        print("\n" + "=" * 60 + "\n")