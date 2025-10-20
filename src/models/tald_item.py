"""
TALDItem Model - Rappresenta un item della scala TALD

Questo modulo contiene la classe TALDItem che rappresenta uno dei 30 fenomeni
di disfunzione del pensiero e del linguaggio descritti nella Thought and Language
Dysfunction Scale (TALD).

Entity del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class TALDItem:
    """
    Rappresenta un singolo item della scala TALD.
    
    Attributes:
        id (int): Identificativo univoco dell'item (1-30)
        title (str): Titolo del disturbo (es. "Circumstantiality")
        type (str): Tipo di fenomeno ("objective" o "subjective")
        description (str): Descrizione clinica dettagliata del disturbo
        criteria (str): Criteri diagnostici per identificare il disturbo
        example (str): Esempio pratico di manifestazione del disturbo
        questions (List[str]): Domande suggerite per l'intervista clinica
        graduation (Dict[str, str]): Scala di graduazione 0-4 con descrizioni
        default_grade (int): Grado predefinito per la simulazione (0-4)
    
    Example:
        >>> item = TALDItem(
        ...     id=1,
        ...     title="Circumstantiality",
        ...     type="objective",
        ...     description="Thinking is circuitous...",
        ...     criteria="Insufficient capacity to process...",
        ...     example="When asked 'Was it easy to get here?'...",
        ...     questions=[],
        ...     graduation={
        ...         "0": "not present",
        ...         "1": "doubtful",
        ...         "2": "mild: ...",
        ...         "3": "moderate: ...",
        ...         "4": "severe: ..."
        ...     },
        ...     default_grade=2
        ... )
        >>> print(item.title)
        Circumstantiality
        >>> print(item.is_objective())
        True
    """
    
    id: int
    title: str
    type: str
    description: str
    criteria: str
    example: str
    questions: List[str]
    graduation: Dict[str, str]
    default_grade: int
    
    def __post_init__(self):
        """
        Validazione dei dati dopo l'inizializzazione.
        
        Raises:
            ValueError: Se i dati non rispettano i vincoli
        """
        # Validazione ID
        if not (1 <= self.id <= 30):
            raise ValueError(f"Item ID deve essere tra 1 e 30, ricevuto: {self.id}")
        
        # Validazione type
        if self.type not in ["objective", "subjective"]:
            raise ValueError(
                f"Item type deve essere 'objective' o 'subjective', ricevuto: {self.type}"
            )
        
        # Validazione default_grade
        if not (0 <= self.default_grade <= 4):
            raise ValueError(
                f"Default grade deve essere tra 0 e 4, ricevuto: {self.default_grade}"
            )
        
        # Validazione graduation (deve contenere le chiavi 0-4)
        expected_keys = {"0", "1", "2", "3", "4"}
        if set(self.graduation.keys()) != expected_keys:
            raise ValueError(
                f"Graduation deve contenere le chiavi 0-4, ricevuto: {self.graduation.keys()}"
            )
    
    def is_objective(self) -> bool:
        """
        Verifica se l'item è di tipo oggettivo (osservabile dall'esaminatore).
        
        Returns:
            bool: True se objective, False se subjective
        """
        return self.type == "objective"
    
    def is_subjective(self) -> bool:
        """
        Verifica se l'item è di tipo soggettivo (riportato dal paziente).
        
        Returns:
            bool: True se subjective, False se objective
        """
        return self.type == "subjective"
    
    def get_grade_description(self, grade: int) -> str:
        """
        Restituisce la descrizione testuale per un dato grado.
        
        Args:
            grade (int): Grado da 0 a 4
            
        Returns:
            str: Descrizione del grado
            
        Raises:
            ValueError: Se il grado non è tra 0 e 4
        """
        if not (0 <= grade <= 4):
            raise ValueError(f"Grade deve essere tra 0 e 4, ricevuto: {grade}")
        
        return self.graduation[str(grade)]
    
    def get_display_name(self) -> str:
        """
        Restituisce il nome completo per visualizzazione nell'interfaccia.
        
        Returns:
            str: Nome formattato come "ID. Title (type)"
        """
        return f"{self.id}. {self.title} ({self.type})"
    
    def to_dict(self) -> Dict:
        """
        Converte l'oggetto in dizionario (utile per serializzazione JSON).
        
        Returns:
            Dict: Rappresentazione dizionario dell'item
        """
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "description": self.description,
            "criteria": self.criteria,
            "example": self.example,
            "questions": self.questions,
            "graduation": self.graduation,
            "default_grade": self.default_grade
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TALDItem':
        """
        Crea un'istanza TALDItem da un dizionario (utile per deserializzazione JSON).
        
        Args:
            data (Dict): Dizionario con i dati dell'item
            
        Returns:
            TALDItem: Nuova istanza dell'item
            
        Example:
            >>> data = {
            ...     "id": 1,
            ...     "title": "Circumstantiality",
            ...     "type": "objective",
            ...     ...
            ... }
            >>> item = TALDItem.from_dict(data)
        """
        return cls(**data)
    
    def __str__(self) -> str:
        """
        Rappresentazione stringa leggibile dell'item.
        
        Returns:
            str: Stringa formattata
        """
        return f"TALDItem({self.id}: {self.title})"
    
    def __repr__(self) -> str:
        """
        Rappresentazione tecnica dell'item per debugging.
        
        Returns:
            str: Rappresentazione completa
        """
        return (
            f"TALDItem(id={self.id}, title='{self.title}', type='{self.type}', "
            f"default_grade={self.default_grade})"
        )