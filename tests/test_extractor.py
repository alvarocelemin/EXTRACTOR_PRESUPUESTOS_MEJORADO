import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from pathlib import Path
from Core.extractor import Configuracion, ExtractorPresupuestos

@pytest.fixture
def config_default():
    """Proporciona una configuración por defecto para las pruebas."""
    return Configuracion(paginas_mediciones=(1, 1), paginas_presupuesto=(2, 2))

def test_convertir_numero(config_default):
    """Prueba la conversión de números."""
    extractor = ExtractorPresupuestos(config_default)
    assert extractor._convertir_numero("1.234,56") == 1234.56
    assert extractor._convertir_numero("100,00") == 100.0
    assert extractor._convertir_numero("invalido") == 0.0

@patch('Core.extractor.fitz.open')
def test_procesar_pdf_con_mock(mock_fitz_open, config_default):
    """
    Prueba el flujo completo de procesar_pdf simulando la lectura del PDF.
    """
    # 1. Preparamos el texto que simulará cada sección del PDF
    texto_mediciones_simulado = """
    10.01.01 ud Descripción corta para el código 10.
    Más detalles que no se usan.

    10.01.02 m2 Descripción para el código 20.
    """
    
    texto_presupuesto_simulado = """
    10.01.01 DESC_RESUMEN_1   10,00   100,00   1.000,00
    10.01.02 DESC_RESUMEN_2   5,00    20,00    100,00
    """

    # 2. Configuramos el mock para que devuelva el texto correcto según el rango de página
    def mock_get_text_por_rango(doc_mock, rango):
        if rango == config_default.paginas_mediciones:
            return texto_mediciones_simulado
        elif rango == config_default.paginas_presupuesto:
            return texto_presupuesto_simulado
        return ""

    mock_doc = MagicMock()
    mock_fitz_open.return_value.__enter__.return_value = mock_doc
    
    # 3. Creamos el extractor y usamos patch para simular _extraer_texto_rango
    extractor = ExtractorPresupuestos(config_default)
    with patch.object(extractor, '_extraer_texto_rango', side_effect=mock_get_text_por_rango):
        # 4. Ejecutamos el método a probar
        df_resultado = extractor.procesar_pdf(Path("dummy.pdf"))

    # 5. Verificamos los resultados
    assert isinstance(df_resultado, pd.DataFrame)
    assert len(df_resultado) == 2
    
    # Verificar la primera fila (debería tener la descripción de las mediciones)
    fila_uno = df_resultado.iloc[0]
    assert fila_uno['CÓDIGO'] == '10.01.01'
    assert fila_uno['DESCRIPCIÓN'] == 'Descripción corta para el código 10.'
    assert fila_uno['UNIDAD'] == 'UD'
    assert fila_uno['CANTIDAD'] == 10.0
    assert fila_uno['IMPORTE TOTAL'] == 1000.0