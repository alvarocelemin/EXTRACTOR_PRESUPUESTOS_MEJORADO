import click
from .extractor import Configuracion

@click.group()
def cli():
    """Interfaz CLI para gestión de presupuestos"""

@cli.command()
@click.argument('archivo_pdf', type=click.Path(exists=True))
def extraer(archivo_pdf):
    """Extrae datos de un PDF"""
    config = Configuracion()
    extractor = Extractor(config)
    resultados = extractor.procesar_pdf(archivo_pdf)
    click.echo(f"✅ Partidas extraídas: {len(resultados)}")

if __name__ == '__main__':
    cli()
