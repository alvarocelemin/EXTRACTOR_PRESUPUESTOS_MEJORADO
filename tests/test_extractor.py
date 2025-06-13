import pytest
from pathlib import Path
from Core.extractor import Configuracion, ExtractorPresupuestos  # Cambiado a importación absoluta

@pytest.fixture
def extractor():
    """Fixture que proporciona una instancia configurada de ExtractorPresupuestos"""
    return ExtractorPresupuestos(Configuracion())

def test_patron_combinado(extractor):
    """Prueba el procesamiento de texto con patrones combinados"""
    texto = "1.01.01 ud Cableado\n1.01.02 m2 Pintura"
    resultados = extractor.procesar_texto(texto)  # Cambiado a procesar_texto
    
    assert len(resultados) == 2
    assert resultados[0]['codigo'] == '1.01.01'
    assert resultados[0]['unidad'].lower() == 'ud'
    assert resultados[1]['unidad'].lower() == 'm2'
    assert "Pintura" in resultados[1]['texto_completo']

def test_config_invalida():
    """Prueba que se lance ValueError con configuración inválida"""
    with pytest.raises(ValueError):
        Configuracion(patrones={'codigo': '...'})  # Configuración incompleta
