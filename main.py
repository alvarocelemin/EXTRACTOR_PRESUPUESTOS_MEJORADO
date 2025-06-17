# main.py
"""
Punto de entrada principal y orquestador del proyecto.
Resuelve problemas de importación y coordina la extracción y análisis.
"""
import sys
from pathlib import Path
import argparse
import json
import pandas as pd
import logging
from typing import Dict, List, Any, cast

# --- CONFIGURACIÓN DE RUTA PROFESIONAL ---
try:
    project_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(project_root))
    
    from Core.extractor import ExtractorPDF
    from Core.nlp_model import AnalizadorNLP
except ImportError as e:
    print(f"❌ Error de importación. Asegúrate de que la estructura es correcta: main.py y la carpeta Core/ al mismo nivel.")
    print(f"Error original: {e}")
    sys.exit(1)

# --- CONFIGURACIÓN DE LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ejecucion_main.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def convertir_a_formato_nlp(df: pd.DataFrame) -> Dict[str, List[Dict[str, str]]]:
    """Convierte el DataFrame al formato estricto que espera el AnalizadorNLP."""
    registros = df.rename(
        columns={'CÓDIGO': 'codigo', 'DESCRIPCIÓN_COMPLETA': 'descripcion'}
    ).to_dict('records')
    
    # Conversión de tipos explícita
    partidas = [
        {
            'codigo': str(item.get('codigo', '')),
            'descripcion': str(item.get('descripcion', ''))
        }
        for item in registros
    ]
    
    return {'partidas': partidas}

def run(args):
    """Función principal que orquesta el proceso."""
    logger.info(f"Iniciando proceso para el archivo: {args.archivo_pdf}")

    try:
        # --- PASO 1: EXTRACCIÓN ---
        extractor = ExtractorPDF()
        paginas = (args.inicio, args.fin if args.fin != 0 else 9999)
        logger.info(f"Extrayendo datos de páginas {args.inicio} a {'final' if args.fin == 0 else args.fin}...")

        df_presupuesto, df_descripciones = extractor.extraer_datos_pdf(str(args.archivo_pdf), paginas)

        if df_presupuesto.empty:
            logger.warning("No se extrajeron partidas del presupuesto. Finalizando.")
            return

        excel_path = args.salida_excel or Path(args.archivo_pdf).with_suffix('.xlsx')
        with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
            df_presupuesto.to_excel(writer, sheet_name='PRESUPUESTO', index=False)
            df_descripciones.to_excel(writer, sheet_name='DESCRIPCIONES_COMPLETAS', index=False)
        logger.info(f"✅ Datos guardados en: {excel_path}")

        # --- PASO 2: ANÁLISIS NLP ---
        analizador = AnalizadorNLP()
        logger.info("Analizando descripciones con NLP...")
        
        # Usamos la función de conversión de tipos
        datos_nlp = convertir_a_formato_nlp(df_descripciones)
        resultados_nlp = analizador.analizar(datos_nlp)

        json_path = args.salida_analisis or Path(args.archivo_pdf).with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(resultados_nlp, f, indent=4, ensure_ascii=False)
        logger.info(f"✅ Análisis NLP guardado en: {json_path}")
        
        print(f"\nProceso completado. Revisa los archivos de salida.")

    except Exception as e:
        logger.error(f"Ocurrió un error crítico durante la ejecución: {e}", exc_info=True)
        print(f"\n❌ Ocurrió un error. Revisa el archivo 'ejecucion_main.log' para más detalles.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrae y analiza datos de presupuestos en PDF.")
    parser.add_argument("archivo_pdf", type=Path, help="Ruta al archivo PDF del presupuesto.")
    parser.add_argument("-i", "--inicio", type=int, default=1, help="Página inicial para la extracción.")
    parser.add_argument("-f", "--fin", type=int, default=0, help="Página final (0 para leer hasta el final).")
    parser.add_argument("-e", "--salida-excel", type=Path, help="Ruta para el archivo Excel de salida.")
    parser.add_argument("-a", "--salida-analisis", type=Path, help="Ruta para el archivo JSON del análisis.")

    args = parser.parse_args()

    if not args.archivo_pdf.exists():
        print(f"Error: El archivo especificado no existe: {args.archivo_pdf}")
        sys.exit(1)
        
    run(args)
