"""
LLMService - Servizio per integrazione Google Gemini API

Questo modulo gestisce l'interfaccia con Google Gemini API per:
- Simulare pazienti virtuali con disturbi TALD
- Generare risposte clinicamente coerenti
- Produrre spiegazioni cliniche per i report
- Gestire timeout ed errori di connessione

Control del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_3, RF_4, RF_11 del RAD
"""

import time
import random
from typing import Dict, Optional
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from models.tald_item import TALDItem
from models.conversation import ConversationHistory


class LLMTimeoutError(Exception):
    """Eccezione per timeout nelle chiamate LLM (>30 secondi)."""
    pass


class LLMConnectionError(Exception):
    """Eccezione per errori di connessione all'API."""
    pass


class LLMService:
    """
    Service per gestione delle interazioni con Google Gemini API.
    
    Responsabilità:
    - Configurare e inizializzare Gemini API
    - Costruire prompt clinicamente accurati per simulazione pazienti
    - Generare risposte coerenti con i disturbi TALD
    - Gestire timeout (30s) ed errori come da RAD RF_11
    - Generare spiegazioni cliniche per i report
    
    Attributes:
        config (dict): Configurazione LLM (api_key, model, temperature, max_tokens)
        model: Istanza del modello Gemini
        timeout (int): Timeout in secondi per le richieste (default: 30)
    
    Example:
        >>> config = {"api_key": "...", "model": "gemini-1.5-pro", ...}
        >>> llm = LLMService(config)
        >>> response = llm.generate_response(
        ...     user_message="Come ti senti?",
        ...     conversation_history=history,
        ...     tald_item=item,
        ...     grade=2
        ... )
    """
    
    # Timeout per richieste API (come da RAD RF_11)
    REQUEST_TIMEOUT = 30  # secondi
    
    def __init__(self, config: Dict[str, any]):
        """
        Inizializza il servizio LLM con la configurazione fornita.
        
        Args:
            config (dict): Configurazione contenente api_key, model, temperature, max_tokens
            
        Raises:
            ValueError: Se l'API key non è presente nella configurazione
            LLMConnectionError: Se la configurazione dell'API fallisce
        """
        self.config = config
        self.timeout = self.REQUEST_TIMEOUT
        
        # Verifica presenza API key
        if not config.get('api_key'):
            raise ValueError(
                "API key non presente nella configurazione. "
                "Impossibile inizializzare LLMService."
            )
        
        try:
            # Configura Gemini API
            genai.configure(api_key=config['api_key'])
            
            # Inizializza il modello con configurazione di sicurezza
            # Disabilitiamo i filtri di sicurezza per contenuti clinici/medici
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            self.model = genai.GenerativeModel(
                model_name=config['model'],
                safety_settings=safety_settings
            )
            
        except Exception as e:
            raise LLMConnectionError(f"Errore nella configurazione di Gemini API: {e}")
    
    def _generate_patient_background(self) -> str:
        """
        Genera un background paziente randomizzato.
        
        Crea profili fittizi con nome, età e professione casuali
        per dare naturalezza e varietà alle simulazioni.
        
        Returns:
            str: Background paziente (es. "Ti chiami Marco, hai 32 anni, lavori come impiegato")
        """
        # Pool di nomi italiani comuni
        nomi_m = ["Marco", "Luca", "Giuseppe", "Andrea", "Matteo", "Alessandro", 
                  "Davide", "Stefano", "Paolo", "Riccardo"]
        nomi_f = ["Laura", "Sofia", "Francesca", "Chiara", "Giulia", "Elena", 
                  "Sara", "Valentina", "Martina", "Alessia"]
        
        # Genera genere e nome
        genere = random.choice(["M", "F"])
        nome = random.choice(nomi_m if genere == "M" else nomi_f)
        
        # Genera età casuale (25-55 anni)
        eta = random.randint(25, 55)
        
        # Pool di professioni comuni
        lavori = [
            "impiegato in un'azienda",
            "insegnante di scuola media",
            "tecnico informatico",
            "infermiere",
            "cameriere in un ristorante",
            "commesso in un negozio",
            "operaio",
            "segretaria",
            "cuoco",
            "meccanico",
            "studente universitario",
            "impiegato comunale",
            "addetto alle vendite",
            "receptionist"
        ]
        
        lavoro = random.choice(lavori)
        
        return f"Ti chiami {nome}, hai {eta} anni, lavori come {lavoro}"
    
    def _get_grade_instructions(self, grade: int, tald_item: TALDItem) -> str:
        """
        Genera istruzioni specifiche basate sul grado di severità dell'item.
        
        IMPORTANTE: Usa le descrizioni SPECIFICHE dal JSON dell'item TALD,
        non descrizioni generiche. Ogni item ha termini propri per i gradi.
        
        Args:
            grade (int): Grado TALD (0-4)
            tald_item (TALDItem): Item TALD con le sue descrizioni specifiche
            
        Returns:
            str: Istruzioni per il prompt
        """
        if grade == 0:
            return "Il disturbo non è presente. Rispondi in modo normale e coerente."
        
        # Prende la descrizione SPECIFICA dal JSON dell'item
        # Es. per Dissociation: "incoherence", "disjointed speech", "scattered speech"
        # Es. per Derailment: grade 4 è "extreme" non "severe"
        grade_description = tald_item.get_grade_description(grade)
        
        # Costruisce istruzioni usando la terminologia specifica dell'item
        return f"""GRADO {grade}/4 - {grade_description}

Manifesta il disturbo "{tald_item.title}" con questa specifica intensità.
La descrizione del grado è quella ufficiale dal manuale TALD per questo item."""
    
    def _get_awareness_instructions(self, item_type: str) -> str:
        """
        Genera istruzioni sulla consapevolezza del disturbo.
        
        Args:
            item_type (str): "objective" o "subjective"
            
        Returns:
            str: Istruzioni sulla consapevolezza
        """
        if item_type == "objective":
            return (
                "IMPORTANTE - DISTURBO OGGETTIVO:\n"
                "- NON sei consapevole di avere questo disturbo\n"
                "- Rispondi in modo naturale senza renderti conto del problema\n"
                "- Se ti viene chiesto del disturbo, non riconoscerlo direttamente\n"
                "- Il disturbo emerge spontaneamente nel tuo modo di parlare"
            )
        else:  # subjective
            return (
                "IMPORTANTE - DISTURBO SOGGETTIVO:\n"
                "- SEI consapevole di questo disturbo\n"
                "- Puoi descrivere come ti senti quando richiesto\n"
                "- Puoi riportare il tuo disagio soggettivo\n"
                "- Tuttavia NON menzionare mai il nome tecnico del disturbo"
            )
    
    def build_system_prompt(
        self, 
        tald_item: TALDItem, 
        grade: int,
        patient_background: Optional[str] = None
    ) -> str:
        """
        Costruisce il prompt di sistema per simulare il paziente virtuale.
        
        Questo è il metodo più critico: determina la qualità della simulazione.
        Il prompt è strutturato per:
        - Definire il ruolo (paziente psichiatrico)
        - Specificare il disturbo da manifestare
        - Dare istruzioni comportamentali precise
        - Fornire esempi clinici
        - Adattare severità al grado SPECIFICO dell'item
        
        Args:
            tald_item (TALDItem): Item TALD da simulare
            grade (int): Grado di severità (0-4)
            patient_background (str, optional): Background fittizio del paziente
            
        Returns:
            str: Prompt completo per il sistema
        """
        # Genera background casuale se non fornito
        if patient_background is None:
            patient_background = self._generate_patient_background()
        
        # Costruisce il prompt strutturato
        prompt = f"""# RUOLO E CONTESTO
Sei un paziente durante un colloquio clinico con uno psicologo/psichiatra.

{patient_background}

Sei qui per un colloquio di valutazione. Rispondi alle domande in modo naturale e autentico.

---

# DISTURBO DA SIMULARE

**Disturbo:** {tald_item.title}
**Tipo:** {tald_item.type.upper()} ({"osservabile dall'esaminatore" if tald_item.type == "objective" else "riportato soggettivamente"})

**Descrizione Clinica:**
{tald_item.description}

**Criteri Manifestazione:**
{tald_item.criteria}

**Esempio Tipico di questo Disturbo:**
{tald_item.example}

---

# SEVERITÀ DELLA MANIFESTAZIONE

{self._get_grade_instructions(grade, tald_item)}

---

# ISTRUZIONI COMPORTAMENTALI CRITICHE

{self._get_awareness_instructions(tald_item.type)}

## Regole Fondamentali:
1. NON menzionare MAI il nome del disturbo ("{tald_item.title}")
2. NON dire frasi come "Ho {tald_item.title}" o "Manifesto questo sintomo"
3. Manifesta il disturbo NATURALMENTE nel tuo modo di parlare/pensare
4. NON descrivere azioni fisiche (es. "mi sistema sulla sedia", "gesticola")
5. Questo è un colloquio VERBALE: rispondi solo con le PAROLE che diresti
6. Mantieni ASSOLUTA coerenza con il disturbo per tutta la conversazione
7. Rispondi in modo autentico, come un vero paziente
8. Se non capisci una domanda per via del disturbo, rispondi coerentemente con la tua condizione

## Stile delle Risposte:
- Linguaggio naturale e colloquiale (italiano corrente)
- Lunghezza appropriata al tipo di disturbo
  * Se il disturbo implica verbosità (es. Logorrhoea, Circumstantiality): risposte lunghe
  * Se il disturbo implica laconicità (es. Poverty of Speech): risposte brevi
  * Altrimenti: risposte di lunghezza normale
- Emozioni appropriate al contesto della domanda
- Coerenza con il background personale

## Contesto Clinico:
- Sei in un ambiente sicuro e professionale
- L'esaminatore è un professionista che vuole aiutarti
- Puoi essere aperto nelle risposte
- Non devi fingere o nascondere nulla (il disturbo emerge naturalmente)

---

# INIZIA LA SIMULAZIONE

Ora rispondi alle domande dell'esaminatore manifestando naturalmente il disturbo descritto.
Ricorda: il tuo compito è ESSERE il paziente, non DESCRIVERE il paziente.
"""
        
        return prompt
    
    def generate_response(
        self,
        user_message: str,
        conversation_history: ConversationHistory,
        tald_item: TALDItem,
        grade: int,
        patient_background: Optional[str] = None
    ) -> str:
        """
        Genera la risposta del paziente virtuale.
        
        Questo metodo:
        1. Costruisce il prompt di sistema
        2. Prepara lo storico conversazionale
        3. Invia la richiesta a Gemini con timeout
        4. Gestisce errori e timeout come da RAD RF_11
        
        Args:
            user_message (str): Messaggio/domanda dell'utente
            conversation_history (ConversationHistory): Storico della conversazione
            tald_item (TALDItem): Item TALD da simulare
            grade (int): Grado di severità
            patient_background (str, optional): Background del paziente
            
        Returns:
            str: Risposta generata dal paziente virtuale
            
        Raises:
            LLMTimeoutError: Se la richiesta supera i 30 secondi
            LLMConnectionError: Se ci sono errori di connessione
        """
        try:
            # Costruisce il prompt di sistema
            system_prompt = self.build_system_prompt(tald_item, grade, patient_background)
            
            # Prepara lo storico per Gemini
            # Gemini vuole formato: [{"role": "user/model", "parts": ["testo"]}]
            history_for_gemini = []
            
            for msg in conversation_history.messages:
                history_for_gemini.append({
                    "role": "user" if msg.is_user_message() else "model",
                    "parts": [msg.content]
                })
            
            # Inizia la chat con storico
            chat = self.model.start_chat(history=history_for_gemini)
            
            # Prepara la richiesta completa
            full_prompt = f"{system_prompt}\n\n---\n\nDomanda dell'esaminatore: {user_message}\n\nRisposta del paziente:"
            
            # Chiamata API con timeout tracking
            start_time = time.time()
            
            response = chat.send_message(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.config['temperature'],
                    max_output_tokens=self.config['max_tokens'],
                )
            )
            
            elapsed_time = time.time() - start_time
            
            # Verifica timeout (30 secondi come da RAD)
            if elapsed_time > self.timeout:
                raise LLMTimeoutError(
                    f"La richiesta ha superato il timeout di {self.timeout} secondi "
                    f"(tempo effettivo: {elapsed_time:.1f}s)"
                )
            
            # Estrai il testo della risposta
            return response.text.strip()
        
        except LLMTimeoutError:
            # Propaga il timeout error (gestito dal ConversationManager)
            raise
        
        except Exception as e:
            # Qualsiasi altro errore diventa LLMConnectionError
            raise LLMConnectionError(
                f"Errore durante la generazione della risposta: {str(e)}"
            )
    
    def generate_clinical_explanation(
        self,
        tald_item: TALDItem,
        conversation_history: ConversationHistory,
        grade: int
    ) -> str:
        """
        Genera una spiegazione clinica dei fenomeni osservati nella conversazione.
        
        Utilizzato per il report finale. Analizza la conversazione e spiega
        quali segnali linguistici erano presenti e come identificarli.
        
        Args:
            tald_item (TALDItem): Item TALD simulato
            conversation_history (ConversationHistory): Storico della conversazione
            grade (int): Grado di severità
            
        Returns:
            str: Spiegazione clinica dettagliata
            
        Raises:
            LLMConnectionError: Se ci sono errori nella generazione
        """
        try:
            # Prepara la trascrizione della conversazione
            transcript = conversation_history.to_text_transcript()
            
            # Ottiene la descrizione specifica del grado per questo item
            grade_description = tald_item.get_grade_description(grade)
            
            # Costruisce il prompt per l'analisi clinica
            analysis_prompt = f"""# COMPITO: Analisi Clinica di un Colloquio

Sei un clinico esperto che deve analizzare un colloquio psichiatrico.

## DISTURBO SIMULATO
**Item TALD:** {tald_item.title}
**Tipo:** {tald_item.type}
**Grado:** {grade}/4 - {grade_description}

**Descrizione Clinica:**
{tald_item.description}

**Criteri Diagnostici:**
{tald_item.criteria}

---

## TRASCRIZIONE DEL COLLOQUIO

{transcript}

---

## RICHIESTA

Fornisci un'analisi clinica dettagliata (circa 150-200 parole) che spieghi:

1. **Segnali linguistici osservati**: Quali manifestazioni specifiche del disturbo "{tald_item.title}" sono presenti nella conversazione?

2. **Come identificarli**: Quali aspetti del linguaggio/pensiero permettono di riconoscere questo disturbo?

3. **Coerenza con il grado {grade}**: In che modo la manifestazione corrisponde a "{grade_description}"?

4. **Indicazioni didattiche**: Cosa dovrebbe notare uno studente per identificare correttamente questo fenomeno?

Scrivi in italiano, in modo chiaro e professionale, come se stessi spiegando a uno studente di psicologia/psichiatria.
"""
            
            # Genera l'analisi
            response = self.model.generate_content(
                analysis_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Temperatura bassa per analisi più precisa
                    max_output_tokens=800,
                )
            )
            
            return response.text.strip()
        
        except Exception as e:
            raise LLMConnectionError(
                f"Errore durante la generazione della spiegazione clinica: {str(e)}"
            )
    
    def test_connection(self) -> bool:
        """
        Testa la connessione all'API Gemini.
        
        Metodo di utilità per verificare che l'API key sia valida.
        Non è un requisito funzionale del RAD.
        
        Returns:
            bool: True se la connessione funziona
            
        Raises:
            LLMConnectionError: Se il test fallisce
        """
        try:
            # Prova una generazione semplice
            self.model.generate_content(
                "Test",
                generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    max_output_tokens=5,
                )
            )
            # Se non solleva eccezioni, la connessione funziona
            return True
        
        except Exception as e:
            raise LLMConnectionError(f"Test di connessione fallito: {e}")