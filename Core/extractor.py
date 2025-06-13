"""
Módulo principal de extracción - Versión 9.0 (Solución definitiva con mapeo de metadatos)
"""
import re
import fitz
import sys
import time
import logging
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class Configuracion:
    """Configuración para el extractor de dos pasadas."""
    paginas_mediciones: Tuple[int, int] = (1576, 2547)
    paginas_presupuesto: Tuple[int, int] = (1576, 2547)
    
    columnas_finales: List[str] = field(default_factory=lambda: [
        'CÓDIGO', 'DESCRIPCIÓN', 'UNIDAD', 'CANTIDAD', 'PRECIO UNITARIO', 'IMPORTE TOTAL'
    ])
    patrones: Dict = field(default_factory=lambda: {
        # Patrón para encontrar un bloque completo en la sección de mediciones
        'bloque_medicion': r'^\s*(?P<codigo>\d{2,3}\.\d{2}\.\d{2,3})\s+(?P<unidad>ud|m2|m3|kg|ml|m|l|uds)\s+(?P<texto>.*?)(?=\s*\d{2,3}\.\d{2}\.\d{2,3}\s+(?:ud|m2|m3|kg|ml|m|l|uds)|$)',
        # Patrón para una fila de la tabla de resumen final
        'fila_presupuesto': r'^\s*(?P<codigo>\d{2,3}\.\d{2}\.\d{2,3})\s+(?P<desc_corta>.+?)\s+(?P<cantidad>[\d.,]+)\s+(?P<precio>[\d.,]+)\s+(?P<importe>[\d.,]+)\s*$'
    })

class ExtractorPresupuestos:
    def __init__(self, config: Configuracion):
        self.config = config
        self.logger = logging.getLogger('ExtractorPresupuestos')
        self.patrones_compilados = {k: re.compile(v, re.IGNORECASE | re.DOTALL | re.MULTILINE) for k, v in config.patrones.items()}

    def _convertir_numero(self, texto_numero: str) -> float:
        """Convierte un string como '1.234,56' a un float como 1234.56"""
        try:
            return float(str(texto_numero).replace('.', '').replace(',', '.'))
        except (ValueError, AttributeError):
            return 0.0

    def _extraer_texto_rango(self, doc: fitz.Document, rango: Tuple[int, int]) -> str:
        """Extrae texto de un rango de páginas específico."""
        texto_parts = []
        start, end = rango
        for page_num in range(start - 1, min(end, len(doc))):
            texto_parts.append(doc[page_num].get_text("text")) #type: ignore
        return "\n".join(texto_parts)

    def procesar_pdf(self, ruta_pdf: Path) -> pd.DataFrame:
        """Flujo principal de dos pasadas: mapeo de metadatos y extracción de datos."""
        if not ruta_pdf.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {ruta_pdf}")

        with fitz.open(str(ruta_pdf)) as doc:
            # --- PASO 1: MAPEAR METADATOS (DESCRIPCIÓN Y UNIDAD) ---
            self.logger.info(f"Paso 1: Mapeando metadatos desde págs {self.config.paginas_mediciones[0]}-{self.config.paginas_mediciones[1]}...")
            texto_mediciones = self._extraer_texto_rango(doc, self.config.paginas_mediciones)
            mapa_metadatos = {}
            for match in self.patrones_compilados['bloque_medicion'].finditer(texto_mediciones):
                datos = match.groupdict()
                codigo = datos['codigo']
                # Guardamos la descripción y la unidad extraída directamente del encabezado de la partida
                mapa_metadatos[codigo] = {
                    'DESCRIPCIÓN': datos['texto'].strip().split('\n')[0],
                    'UNIDAD': datos['unidad'].upper()
                }
            self.logger.info(f"Se mapearon {len(mapa_metadatos)} metadatos.")

            # --- PASO 2: EXTRAER DATOS NUMÉRICOS Y FUSIONAR ---
            self.logger.info(f"Paso 2: Extrayendo datos finales desde págs {self.config.paginas_presupuesto[0]}-{self.config.paginas_presupuesto[1]}...")
            texto_presupuesto = self._extraer_texto_rango(doc, self.config.paginas_presupuesto)
            partidas_finales = []
            for match in self.patrones_compilados['fila_presupuesto'].finditer(texto_presupuesto):
                datos = match.groupdict()
                codigo = datos['codigo']
                
                # Obtenemos los metadatos del mapa. Si no existen, usamos valores por defecto.
                info_partida = mapa_metadatos.get(codigo, {'DESCRIPCIÓN': datos['desc_corta'], 'UNIDAD': 'UD'})

                partida = {
                    'CÓDIGO': codigo,
                    'DESCRIPCIÓN': info_partida['DESCRIPCIÓN'],
                    'UNIDAD': info_partida['UNIDAD'],
                    'CANTIDAD': self._convertir_numero(datos['cantidad']),
                    'PRECIO UNITARIO': self._convertir_numero(datos['precio']),
                    'IMPORTE TOTAL': self._convertir_numero(datos['importe'])
                }
                partidas_finales.append(partida)
            self.logger.info(f"Se extrajeron {len(partidas_finales)} partidas de la tabla de resumen.")

        if not partidas_finales:
            raise ValueError("No se encontraron datos en la tabla de resumen. Revisa el rango de páginas y los patrones.")

        # --- PASO 3: CREAR Y ORDENAR EL DATAFRAME FINAL ---
        df = pd.DataFrame(partidas_finales)
        
        # Lógica de ordenación natural
        temp_cols = df['CÓDIGO'].str.split('.', expand=True).fillna('0')
        df['c1'] = pd.to_numeric(temp_cols[0], errors='coerce')
        df['c2'] = pd.to_numeric(temp_cols[1], errors='coerce')
        df['c3'] = pd.to_numeric(temp_cols[2], errors='coerce')
        df = df.sort_values(by=['c1', 'c2', 'c3']).drop(columns=['c1', 'c2', 'c3'])
        
        for col in self.config.columnas_finales:
            if col not in df.columns: df[col] = None
        
        return df[self.config.columnas_finales].reset_index(drop=True)

def main():
    # ... La función main permanece igual ...
    if len(sys.argv) < 2:
        print("Uso: python extractor.py <ruta_pdf>")
        sys.exit(1)
        
    pdf_path = Path(sys.argv[1])
    try:
        config = Configuracion()
        extractor = ExtractorPresupuestos(config)
        df_final = extractor.procesar_pdf(pdf_path)
        
        output_path = pdf_path.with_suffix('.xlsx')
        df_final.to_excel(output_path, index=False, sheet_name='PRESUPUESTO')
        
        print(f"\n✅ Extracción completada con éxito.")
        print(f"📊 Archivo generado: {output_path}")
        print(f"📝 Total de partidas: {len(df_final)}")
        if 'IMPORTE TOTAL' in df_final.columns:
            importe_total = pd.to_numeric(df_final['IMPORTE TOTAL'], errors='coerce').sum()
            print(f"💰 Importe total: {importe_total:,.2f} €")
            
    except Exception as e:
        logging.error(f"Error en ejecución: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()