# Core/nlp_model.py
import re
from collections import defaultdict
from typing import Dict, List, Union, Optional, Set
import spacy
from spacy.language import Language
from spacy.pipeline import EntityRuler
import logging

class AnalizadorNLP:
    """
    Analizador de presupuestos que utiliza spaCy para extraer entidades
    y validar contenido técnico de forma robusta.
    """
    def __init__(self, nlp: Optional[Language] = None):
        self.logger = logging.getLogger(__name__)
        try:
            self.nlp = nlp if nlp else spacy.load("es_core_news_sm")
            self._configurar_entity_ruler()
            self.logger.info("Pipeline NLP inicializado correctamente")
        except IOError as e:
            self.logger.critical("Modelo spaCy no encontrado")
            raise RuntimeError("Modelo 'es_core_news_sm' no encontrado. Ejecuta: python -m spacy download es_core_news_sm") from e
        except Exception as e:
            self.logger.critical(f"Error crítico en inicialización: {str(e)}", exc_info=True)
            raise RuntimeError(f"Error al inicializar el pipeline de NLP: {e}") from e

    def _configurar_entity_ruler(self) -> None:
        """Configura el EntityRuler con patrones técnicos para presupuestos."""
        patrones = [
            {"label": "MATERIAL", "pattern": term} for term in ["cable", "bornas", "contactor", "protección"]
        ] + [
            {"label": "NORMATIVA", "pattern": term} for term in ["REBT", "IEC", "UNE-EN"]
        ] + [
            {"label": "PARAMETRO", "pattern": [{"TEXT": {"REGEX": r"\d+x\d+[aA]"}}]}
        ]
        
        ruler_name = "presupuestos_ruler"
        if ruler_name not in self.nlp.pipe_names:
            ruler = self.nlp.add_pipe("entity_ruler", name=ruler_name, config={"overwrite_ents": True})
            ruler.add_patterns(patrones)  # type: ignore
        else:
            existing_ruler = self.nlp.get_pipe(ruler_name)
            existing_ruler.add_patterns(patrones)  # type: ignore

    def analizar(self, datos: Dict[str, List[Dict[str, str]]]) -> Dict[str, Union[Dict[str, int], List[str], List[Dict[str, str]]]]:
        """
        Analiza partidas de presupuesto detectando:
        - Materiales mencionados
        - Normativas técnicas
        - Alertas por especificaciones faltantes
        
        Args:
            datos: Diccionario con clave 'partidas' que contiene listas de diccionarios
                   con 'codigo' y 'descripcion'
                   
        Returns:
            Dict con estructura:
            {
                "conteo_materiales": Dict[str, int],
                "normativas_encontradas": List[str],
                "alertas_tecnicas": List[Dict[str, str]]
            }
            
        Raises:
            ValueError: Cuando el formato de entrada es incorrecto
            RuntimeError: En errores de procesamiento NLP
        """
        if not isinstance(datos, dict) or "partidas" not in datos or not isinstance(datos["partidas"], list):
            self.logger.error("Estructura de entrada inválida")
            raise ValueError("Formato de entrada inválido: la clave 'partidas' debe ser una lista.")

        resultados = {
            "conteo_materiales": defaultdict(int),
            "normativas_encontradas": set(),  # type: Set[str]
            "alertas_tecnicas": []
        }
        
        for partida in datos["partidas"]:
            if not isinstance(partida, dict):
                self.logger.warning(f"Partida ignorada: formato incorrecto {partida}")
                continue
                
            descripcion = partida.get("descripcion", "")
            codigo = partida.get("codigo", "N/A")
            
            if not descripcion:
                self.logger.debug(f"Partida {codigo} sin descripción")
                continue
                
            try:
                doc = self.nlp(descripcion)
                self._procesar_entidades(doc, resultados, codigo, descripcion)
                
            except Exception as e:
                self.logger.error(f"Error procesando partida {codigo}: {str(e)}", exc_info=True)
                continue

        return {
            "conteo_materiales": dict(resultados["conteo_materiales"]),
            "normativas_encontradas": sorted(resultados["normativas_encontradas"]),
            "alertas_tecnicas": resultados["alertas_tecnicas"]
        }

    def _procesar_entidades(self, doc, resultados: Dict, codigo: str, descripcion: str) -> None:
        """Procesamiento centralizado de entidades NLP"""
        for ent in doc.ents:
            if ent.label_ == "MATERIAL":
                resultados["conteo_materiales"][ent.text.lower()] += 1
            elif ent.label_ == "NORMATIVA":
                resultados["normativas_encontradas"].add(ent.text.upper())
        
        # Detección específica para contactores sin parámetros
        if "contactor" in descripcion.lower() and not any(ent.label_ == "PARAMETRO" for ent in doc.ents):
            resultados["alertas_tecnicas"].append({
                "código": codigo,
                "mensaje": "Se menciona 'contactor' sin parámetro técnico (ej: 4x25A)."
            })
