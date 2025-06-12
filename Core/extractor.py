"""
Módulo principal de extracción - Versión 2.1 (2025-06-12)
"""
import re
import fitz
from dataclasses import dataclass
from typing import Dict, List, Tuple
from pathlib import Path

@dataclass
class Configuracion:
    rango_mediciones: Tuple[int, int] = (4, 50)
    patrones: Dict = field(default_factory=lambda: {
        'partida': r'(?P<codigo>\d+\.\d+\.\d+)',
        'unidad': r'\b(ud|m2|m3|kg|ml)\b'
    })

class Extractor:
    def __init__(self, config: Configuracion):
        self.config = config
        self._compile_regex()

    def _compile_regex(self):
        """Precompila todos los patrones regex"""
        self.patrones = {
            key: re.compile(pattern, re.IGNORECASE | re.DOTALL)
            for key, pattern in self.config.patrones.items()
        }

    def procesar_pdf(self, ruta_pdf: Path) -> Dict:
        texto = self._extraer_texto(ruta_pdf)
        return self._procesar_mediciones(texto)

    def _extraer_texto(self, ruta_pdf: Path) -> str:
        with fitz.open(ruta_pdf) as doc:
            return "\n".join(
                page.get_text() 
                for page in doc.pages[
                    self.config.rango_mediciones[0]:self.config.rango_mediciones[1]
                ]
            )

    def _procesar_mediciones(self, texto: str) -> Dict:
        partidas = {}
        for match in self.patrones['partida'].finditer(texto):
            partidas[match.group('codigo')] = {
                'unidad': match.group('unidad'),
                'texto': match.group()
            }
        return partidas
