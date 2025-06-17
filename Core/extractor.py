# Core/extractor.py
import re
import pandas as pd
from typing import Tuple, Dict, Optional
from pathlib import Path
import pdfplumber
import locale
import logging


class ExtractorPDF:
    def __init__(self):
        # Configurar locale para interpretación numérica
        locale.setlocale(locale.LC_ALL, "es_ES.UTF-8")
        self.logger = logging.getLogger(__name__)

    def _limpiar_y_convertir_numeros(self, valor: str) -> float:
        """Limpia y convierte strings numéricos con formato español"""
        try:
            if not valor or not isinstance(valor, str):
                return 0.0

            # Eliminar puntos de miles y cambiar comas por puntos
            valor_limpio = valor.replace(".", "").replace(",", ".")
            return locale.atof(valor_limpio)
        except (ValueError, AttributeError) as e:
            self.logger.warning(
                f"No se pudo convertir el valor numérico: {valor}. Error: {str(e)}"
            )
            return 0.0

    def _procesar_linea(self, linea: str) -> Optional[Dict[str, object]]:
        """
        Procesa una línea de texto del PDF y extrae los campos
        Retorna None si la línea no coincide con el patrón esperado

        Args:
            linea (str): Línea de texto del PDF

        Returns:
            Optional[Dict[str, object]]: Diccionario con los campos extraídos o None
        """
        # Expresión regular mejorada con manejo de espacios variables
        patron = r"^(\d{2,3}\.\d{2}\.\d{2})\s+(.+?)\s+([A-Z]{2,4})\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)$"
        match = re.search(patron, linea.strip())

        if not match:
            return None

        try:
            return {
                "CÓDIGO": match.group(1),
                "DESCRIPCIÓN": match.group(2).strip(),
                "UNIDAD": match.group(3),
                "CANTIDAD": self._limpiar_y_convertir_numeros(match.group(4)),
                "PRECIO_UNITARIO": self._limpiar_y_convertir_numeros(match.group(5)),
                "IMPORTE_TOTAL": self._limpiar_y_convertir_numeros(match.group(6)),
            }
        except Exception as e:
            self.logger.error(f"Error procesando línea: {linea}. Error: {str(e)}")
            return None

    def _validar_datos(self, df: pd.DataFrame) -> pd.DataFrame:
        """Valida y ajusta los tipos de datos numéricos"""
        if df.empty:
            return df

        # Asegurar que cantidades sean enteros cuando corresponda
        df["CANTIDAD"] = df["CANTIDAD"].apply(lambda x: int(x) if x.is_integer() else x)

        # Redondear a 2 decimales para precios e importes
        for col in ["PRECIO_UNITARIO", "IMPORTE_TOTAL"]:
            df[col] = df[col].round(2)

        return df

    def extraer_datos_pdf(
        self, pdf_path: str, paginas: Tuple[int, int]
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Método principal de extracción mejorado"""
        datos_presupuesto = []
        datos_descripciones = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                start, end = paginas
                paginas_a_procesar = (
                    pdf.pages[start - 1 : end] if end > 0 else pdf.pages[start - 1 :]
                )

                for pagina in paginas_a_procesar:
                    texto = pagina.extract_text()
                    if not texto:
                        continue

                    for linea in texto.split("\n"):
                        datos = self._procesar_linea(linea)
                        if datos:
                            datos_presupuesto.append(datos)

                            # Crear registro para NLP
                            datos_descripciones.append(
                                {
                                    "CÓDIGO": datos["CÓDIGO"],
                                    "DESCRIPCIÓN_COMPLETA": f"{datos['CÓDIGO']} {datos['DESCRIPCIÓN']}",
                                    "UNIDAD": datos["UNIDAD"],
                                }
                            )
        except Exception as e:
            self.logger.error(f"Error al procesar PDF: {str(e)}")
            raise

        # Crear DataFrames y validar datos
        df_presupuesto = (
            pd.DataFrame(datos_presupuesto) if datos_presupuesto else pd.DataFrame()
        )
        df_descripciones = (
            pd.DataFrame(datos_descripciones) if datos_descripciones else pd.DataFrame()
        )

        if not df_presupuesto.empty:
            df_presupuesto = self._validar_datos(df_presupuesto)

            # Verificar cálculos
            df_presupuesto["IMPORTE_CALCULADO"] = (
                df_presupuesto["CANTIDAD"] * df_presupuesto["PRECIO_UNITARIO"]
            ).round(2)
            inconsistencias = df_presupuesto[
                abs(
                    df_presupuesto["IMPORTE_TOTAL"]
                    - df_presupuesto["IMPORTE_CALCULADO"]
                )
                > 0.1
            ]

            if not inconsistencias.empty:
                self.logger.warning(
                    f"Se encontraron {len(inconsistencias)} inconsistencias en importes"
                )

        return df_presupuesto, df_descripciones
