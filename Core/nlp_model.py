from typing import Dict  # Para type hints
import spacy
from spacy.training.example import Example  # ¡Corregido!

class NLPProcessor:
    def __init__(self, model_name: str = "es_core_news_md"):
        self.nlp = spacy.load(model_name)
        # Configuración correcta de EntityRuler:
        ruler = self.nlp.add_pipe("entity_ruler")
        ruler.add_patterns([{"label": "MATERIAL", "pattern": [{"LOWER": "acero"}]}])  # Sintaxis fija
                
        """self.nlp.add_pipe("entity_ruler").add_patterns([
            {"label": "MATERIAL", "pattern": [{"LOWER": "acero"}]}
        ])"""

    def analyze_text(self, text: str) -> Dict:
        doc = self.nlp(text)
        return {
            "ents": [(ent.text, ent.label_) for ent in doc.ents],
            "cats": doc.cats
        }
