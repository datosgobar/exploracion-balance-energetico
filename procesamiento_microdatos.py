#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function
from __future__ import unicode_literals

import pandas as pd
import numpy as np
import openpyxl as pyxl
import os
import sys

MICRODATOS = "datos/Datos Abiertos Series V2a Original.xlsx"

# A partir de la planilla de microdatos de Balance Energético, se genera un Panel de datos con los siguientes ejes:
# * Items axis (**0**, DataFrames por año): 1960 to 2015
# * Major_axis axis (**1**, Índice por Energía): ACEITES VEGETALES to SOLAR
# * Minor_axis axis (**2**, Columnas por Uso): PROD to INDUS

def sheet_to_df(ws):
    raw_data = ws.values
    # La celda A1 tiene el nombre de la energía de la planilla
    name = next(raw_data)[0]
    cols = next(raw_data)
    rows = list(raw_data)[:56] # Luego de 56 filas de años, algunas sheets tienen aclaraciones
    df = pd.DataFrame.from_records(rows, columns=cols)
    # Asigno índice y corrijo el nombre
    df = df.set_index("KTEP")
    df.index = df.index.rename("anio")
    # Elimino las columnas vacías
    df = df.drop(None, axis=1)
    # Relleno None y NaN con ceros
    df = df.fillna(0)
    return df, name


def generate_panel(input_file=MICRODATOS):
    wb = pyxl.load_workbook(input_file, data_only=True)

    dataframes = {}
    for ws in wb.worksheets:
        df, energy = sheet_to_df(ws)
        dataframes[energy] = df

    raw_panel = pd.Panel(dataframes)
    panel = raw_panel.transpose(1, 0, 2)

    return panel

def main():
    if len(sys.argv) != 3:
        msg = """
Se esperaban exactamente dos argumentos:
$ python procesamiento_microdatos.py <INPUT_FILE> <EXPORT PATH>
"""
        print(msg)
    else:
        microdatos = sys.argv[1]
        output_file = sys.argv[2]
        panel = generate_panel(microdatos)
        panel.to_pickle(output_file)

if __name__ == "__main__":
    main()
