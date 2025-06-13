import click
from pathlib import Path
from .extractor import Configuracion, ExtractorPresupuestos  # Cambiado a ExtractorPresupuestos

@click.group()
def cli():
    """Extrae partidas de presupuestos PDF."""
    pass

@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, path_type=Path))
@click.option('--debug', is_flag=True, help='Modo verbose para diagnóstico')
def extraer(pdf_path, debug):
    """Ejemplo: python -m Core.cli extraer 'presupuesto.pdf' --debug"""
    try:
        config = Configuracion()
        extractor = ExtractorPresupuestos(config)
        resultados = extractor.procesar_pdf(pdf_path)
        
        click.secho(f"✓ {len(resultados)} partidas extraídas", fg='green')
        if debug:
            for idx, r in enumerate(resultados[:3], 1):
                # Verificación de tipo y estructura
                if isinstance(r, dict):
                    codigo = r.get('codigo', 'N/A')
                    unidad = r.get('unidad', 'N/A')
                    texto = r.get('texto_completo', '')[0:50]
                    click.echo(f"{idx}. {codigo} ({unidad}): {texto}...")
                else:
                    click.echo(f"{idx}. [Objeto no es diccionario: {type(r)}]")
                
    except Exception as e:
        click.secho(f"✗ Error: {e}", fg='red', bold=True)
if __name__ == '__main__':
    cli()
