"""
Conversation Models - Modelli per gestione storico conversazionale

Questo modulo contiene le classi per gestire i messaggi e lo storico
della conversazione tra utente e paziente virtuale durante l'intervista.

Entity del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
"""

from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime


@dataclass
class ConversationMessage:
    """
    Rappresenta un singolo messaggio nella conversazione.
    
    Attributes:
        role (str): Ruolo del mittente ("user" o "assistant")
        content (str): Contenuto testuale del messaggio
        timestamp (datetime): Momento di invio del messaggio
    
    Example:
        >>> msg = ConversationMessage(
        ...     role="user",
        ...     content="Come ti senti oggi?"
        ... )
        >>> print(msg.is_user_message())
        True
        >>> print(msg.get_formatted_time())
        '14:30:25'
    """
    
    role: str
    content: str
    timestamp: datetime = None
    
    def __post_init__(self):
        """Validazione e inizializzazione timestamp."""
        # Validazione role
        if self.role not in ["user", "assistant"]:
            raise ValueError(
                f"Role deve essere 'user' o 'assistant', ricevuto: {self.role}"
            )
        
        # Validazione content
        if not isinstance(self.content, str) or len(self.content.strip()) == 0:
            raise ValueError("Content non può essere vuoto")
        
        # Imposta timestamp se non fornito
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def is_user_message(self) -> bool:
        """
        Verifica se il messaggio è dell'utente.
        
        Returns:
            bool: True se role = "user"
        """
        return self.role == "user"
    
    def is_assistant_message(self) -> bool:
        """
        Verifica se il messaggio è del paziente virtuale (assistant).
        
        Returns:
            bool: True se role = "assistant"
        """
        return self.role == "assistant"
    
    def get_formatted_time(self, format_str: str = "%H:%M:%S") -> str:
        """
        Restituisce il timestamp formattato.
        
        Args:
            format_str (str): Formato strftime (default: "HH:MM:SS")
            
        Returns:
            str: Timestamp formattato
        """
        return self.timestamp.strftime(format_str)
    
    def get_word_count(self) -> int:
        """
        Conta le parole nel contenuto del messaggio.
        
        Returns:
            int: Numero di parole
        """
        return len(self.content.split())
    
    def to_dict(self) -> Dict:
        """
        Converte il messaggio in dizionario.
        
        Returns:
            dict: Rappresentazione dizionario
        """
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "word_count": self.get_word_count()
        }
    
    def __str__(self) -> str:
        """Rappresentazione leggibile del messaggio."""
        role_label = "Utente" if self.is_user_message() else "Paziente"
        time_str = self.get_formatted_time()
        return f"[{time_str}] {role_label}: {self.content[:50]}..."


@dataclass
class ConversationHistory:
    """
    Rappresenta l'intero storico della conversazione.
    
    Gestisce la lista ordinata di tutti i messaggi scambiati durante
    la sessione corrente di intervista.
    
    Attributes:
        messages (List[ConversationMessage]): Lista ordinata cronologicamente
        session_start (datetime): Inizio della sessione
    
    Example:
        >>> history = ConversationHistory()
        >>> history.add_message("user", "Ciao, come stai?")
        >>> history.add_message("assistant", "Bene, grazie per aver chiesto.")
        >>> print(history.get_message_count())
        2
        >>> print(history.get_duration_minutes())
        0.5
    """
    
    messages: List[ConversationMessage] = field(default_factory=list)
    session_start: datetime = None
    
    def __post_init__(self):
        """Inizializzazione timestamp sessione."""
        if self.session_start is None:
            self.session_start = datetime.now()
    
    def add_message(self, role: str, content: str) -> ConversationMessage:
        """
        Aggiunge un nuovo messaggio allo storico.
        
        Args:
            role (str): "user" o "assistant"
            content (str): Contenuto del messaggio
            
        Returns:
            ConversationMessage: Il messaggio creato e aggiunto
            
        Example:
            >>> history = ConversationHistory()
            >>> msg = history.add_message("user", "Dimmi di più")
        """
        message = ConversationMessage(role=role, content=content)
        self.messages.append(message)
        return message
    
    def get_message_count(self) -> int:
        """
        Restituisce il numero totale di messaggi.
        
        Returns:
            int: Numero di messaggi nello storico
        """
        return len(self.messages)
    
    def get_user_messages(self) -> List[ConversationMessage]:
        """
        Restituisce solo i messaggi dell'utente.
        
        Returns:
            List[ConversationMessage]: Lista messaggi utente
        """
        return [msg for msg in self.messages if msg.is_user_message()]
    
    def get_assistant_messages(self) -> List[ConversationMessage]:
        """
        Restituisce solo i messaggi del paziente virtuale.
        
        Returns:
            List[ConversationMessage]: Lista messaggi assistant
        """
        return [msg for msg in self.messages if msg.is_assistant_message()]
    
    def get_last_message(self) -> ConversationMessage:
        """
        Restituisce l'ultimo messaggio della conversazione.
        
        Returns:
            ConversationMessage: Ultimo messaggio (None se vuoto)
        """
        return self.messages[-1] if self.messages else None
    
    def get_duration_minutes(self) -> float:
        """
        Calcola la durata della conversazione in minuti.
        
        Returns:
            float: Durata in minuti
        """
        if not self.messages:
            return 0.0
        
        last_message = self.messages[-1]
        duration = (last_message.timestamp - self.session_start).total_seconds()
        return round(duration / 60, 2)
    
    def get_total_words(self) -> int:
        """
        Conta il totale delle parole scambiate nella conversazione.
        
        Returns:
            int: Numero totale di parole
        """
        return sum(msg.get_word_count() for msg in self.messages)
    
    def clear(self):
        """
        Resetta lo storico conversazionale.
        
        Cancella tutti i messaggi e reimposta il timestamp di inizio sessione.
        Utilizzato quando si avvia una nuova simulazione.
        """
        self.messages.clear()
        self.session_start = datetime.now()
    
    def to_text_transcript(self) -> str:
        """
        Genera una trascrizione testuale della conversazione.
        
        Returns:
            str: Trascrizione formattata
            
        Example:
            >>> transcript = history.to_text_transcript()
            >>> # Output:
            >>> # [14:30] Utente: Come ti senti?
            >>> # [14:31] Paziente: Mi sento bene...
        """
        lines = []
        for msg in self.messages:
            role_label = "Utente" if msg.is_user_message() else "Paziente"
            time_str = msg.get_formatted_time("%H:%M")
            lines.append(f"[{time_str}] {role_label}: {msg.content}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """
        Converte lo storico in dizionario.
        
        Returns:
            dict: Rappresentazione dizionario completa
        """
        return {
            "session_start": self.session_start.isoformat(),
            "message_count": self.get_message_count(),
            "duration_minutes": self.get_duration_minutes(),
            "total_words": self.get_total_words(),
            "messages": [msg.to_dict() for msg in self.messages]
        }
    
    def export_to_file(self, filename: str):
        """
        Esporta la trascrizione in un file .txt.
        
        Utilizzato per salvare lo storico in caso di timeout o interruzioni.
        
        Args:
            filename (str): Nome del file di output (es. "transcript.txt")
            
        Example:
            >>> history.export_to_file("interview_transcript_2024-10-21.txt")
        """
        transcript = self.to_text_transcript()
        
        # Aggiungi metadati in testa
        header = f"""
TALDLab - Trascrizione Intervista
Data: {self.session_start.strftime("%Y-%m-%d %H:%M:%S")}
Durata: {self.get_duration_minutes()} minuti
Messaggi totali: {self.get_message_count()}
Parole totali: {self.get_total_words()}
{'='*60}

"""
        
        full_content = header + transcript
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(full_content)
    
    def __len__(self) -> int:
        """Supporto per len(history)."""
        return len(self.messages)
    
    def __str__(self) -> str:
        """Rappresentazione leggibile dello storico."""
        return f"ConversationHistory({self.get_message_count()} messages, {self.get_duration_minutes()} min)"