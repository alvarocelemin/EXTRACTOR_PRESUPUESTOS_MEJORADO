# Core/cli.py
import typer
import pandas as pd
import json
from pathlib import Path
import sys
import logging
from typing import Optional, Dict, Any

try:
    from .extractor import ExtractorPDF
    from .nlp_model import AnalizadorNLP
except ImportError as import_err:
    print(f"❌ Error de importación: {str(import_err)}. Ejecuta como módulo: python -m Core.cli procesar ...")
    sys.exit(1)

app = typer.Typer(help="Herramienta CLI para extraer y analizar presupuestos.", rich_markup_mode="markdown")

def _configurar_logging() -> logging.Logger:
    """Configura logging unificado para la aplicación."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("ejecucion.log", mode='w', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def _mostrar_alertas(resultados_nlp: Dict[str, Any]) -> None:
    """Muestra alertas técnicas en formato legible."""
    if not isinstance(resultados_nlp, dict):
        return
        
    alertas = resultados_nlp.get('alertas_tecnicas', [])
    if not alertas:
        typer.secho("✔ No se encontraron alertas técnicas", fg=typer.colors.GREEN)
        return

    typer.secho("\n--- RESUMEN DEL ANÁLISIS ---", fg=typer.colors.YELLOW, bold=True)
    for alerta in alertas:
        codigo = alerta.get('código', 'N/A') if isinstance(alerta, dict) else 'N/A'
        mensaje = alerta.get('mensaje', str(alerta)) if isinstance(alerta, dict) else str(alerta)
        typer.echo(f" - [bold]Código {codigo}[/bold]: {mensaje}")

@app.command(name="procesar")
def procesar(
    archivo_pdf: Path = typer.Argument(..., exists=True, dir_okay=False, help="Ruta al archivo PDF."),
    inicio: int = typer.Option(1, "--inicio", "-i", help="Página inicial (1-based)."),
    fin: int = typer.Option(0, "--fin", "-f", help="Página final (0 para hasta el final)."),
    output_excel: Path = typer.Option("presupuesto_final.xlsx", "--excel", "-e", help="Archivo Excel de salida."),
    output_analisis: Path = typer.Option("analisis_final.json", "--analisis", "-a", help="Archivo JSON de salida.")
):
    logger = _configurar_logging()
    typer.secho(f"\n🚀 Iniciando proceso para: [bold cyan]{archivo_pdf.name}[/bold cyan]", bold=True)

    try:
        # Extracción de datos
        extractor = ExtractorPDF()
        paginas = (inicio, fin if fin > 0 else 9999)
        
        df_presupuesto, df_descripciones = extractor.extraer_datos_pdf(str(archivo_pdf), paginas)
        
        # Guardado en Excel
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            df_presupuesto.to_excel(writer, sheet_name='PRESUPUESTO', index=False)
            df_descripciones.to_excel(writer, sheet_name='DESCRIPCIONES_COMPLETAS', index=False)
        typer.secho(f"\n✅ Datos guardados en: [bold green]{output_excel.resolve()}[/bold green]")

        # Análisis NLP
        typer.echo("\n🔍 Analizando descripciones con NLP...")
        datos_nlp = {
            "partidas": [
                {
                    "codigo": str(item.get("codigo", "")),
                    "descripcion": str(item.get("descripcion", ""))
                }
                for item in df_descripciones.rename(
                    columns={'CÓDIGO': 'codigo', 'DESCRIPCIÓN_COMPLETA': 'descripcion'}
                ).to_dict('records')
            ]
        }
        
        analizador = AnalizadorNLP()
        resultados_nlp = analizador.analizar(datos_nlp)

        # Guardado JSON
        with open(output_analisis, 'w', encoding='utf-8') as f:
            json.dump(resultados_nlp, f, indent=2, ensure_ascii=False)
        typer.secho(f"✅ Análisis guardado en: [bold green]{output_analisis.resolve()}[/bold green]")

        # Mostrar resumen
        _mostrar_alertas(resultados_nlp)

    except Exception as e:
        logger.exception(f"Error durante el procesamiento: {str(e)}")
        typer.secho(
            f"\n💥 ERROR: {str(e)}. Revisa 'ejecucion.log' para detalles completos.",
            fg=typer.colors.BRIGHT_RED,
            bold=True
        )
        raise typer.Exit(code=1) from e

if __name__ == "__main__":
    app()
