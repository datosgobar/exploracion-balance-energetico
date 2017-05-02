
# coding: utf-8

# In[ ]:

from __future__ import print_function
from __future__ import unicode_literals
import yaml
import json
import io
import sys
import pickle
import pandas as pd
import openpyxl as pyxl


def get_nodos(formato="dict"):
    wb = pyxl.load_workbook("maestro-nodos.xlsx")
    ws = wb.active
    raw_data = ws.values

    cols = next(raw_data)
    rows = list(raw_data)
    if formato == "dict":
        return [dict(zip(cols, row)) for row in rows]
    elif formato == "df":
        return pd.DataFrame.from_records(rows, columns=cols)
    else:
        print("Formato no reconodico: {}".format(formato))


with open("grupos.yaml") as groups_file:
    GRUPOS = yaml.load(groups_file)

with open("alias.yaml") as alias_file:
    ALIAS = yaml.load(alias_file)

AGRUPACION_USOS_PROPIA = {
    "Otros Conceptos de Oferta": ['Variación de Stock', 'Búnker', 'No Aprovechado', 'Ajustes'],
    "Centrales Eléctricas": ['Servicio Público', 'Autoproducción'],
    "Otros Centros de Transformación": ['Aceiteras y Destilerías', 'Coquerías', 'Carboneras', 'Altos Hornos']
}

AGRUPACION_OFERTA_INTERNA = ["Producción", "Importación", "Exportación", "Pérdidas", 'Variación de Stock', 'Búnker', 'No Aprovechado', 'Ajustes']

AGRUPAMIENTOS_ENERGIAS_MINEM = {
    "Coque": ["Coque de Carbón", "Coque de Petróleo"],
    "Carbón de Leña": ["Carbón Vegetal"],
    "No Energéticos": ["No Energético", "No Energético de Carbón", "Etano"]
}

CENTROS_TRANSFORMACION_FINALES = ["Centrales Eléctricas", "Plantas de Tratamiento de Gas", "Refinerías", "Otros Centros de Transformación"]
CENTROS_TRANSFORMACION_BASE = ["Plantas de Tratamiento de Gas", "Refinerías", "Servicio Público", "Autoproducción", "Aceiteras y Destilerías", "Coquerías", "Carboneras", "Altos Hornos"]
CONSUMOS = ["Consumo Propio", "Residencial", "Consumo No Energético", "Transporte", "Comercial", "Industria", "Agropecuario"]


OFERTA = ["Producción", "Importación", "Exportación", "Otros Conceptos de Oferta", "Oferta Interna"]
NODOS_BASE = get_nodos("dict")
NODOS_IDX_A_NOMBRE = {nodo["id"]: nodo["nombre"] for nodo in NODOS_BASE}
NODOS_NOMBRE_A_IDX = {nodo["nombre"]: nodo["id"] for nodo in NODOS_BASE}


def calcular_perdidas(data):
    for uso in data.columns.get_values():
        if uso in CENTROS_TRANSFORMACION_BASE:
            data.loc["Pérdidas", uso] = -sum(data[uso].dropna())
        else:
            data.loc["Pérdidas", uso] = 0
    return data


def sumar_filas_df(df, nueva_fila, filas, borrar=True):
    """Suma todas las filas con índices en la lista `filas`,
    en una nueva fila con índice `nueva_fila`. Si `borrar`, no las incluye en el df retornado. Devuelve el df"""
    df.loc[nueva_fila] = reduce(pd.Series.add, [df.loc[f] for f in filas])
    if borrar:
        df = df.drop(filas, axis=0)
    return df


def adaptar_df_a_entidades_minem(df):
    for energia in AGRUPAMIENTOS_ENERGIAS_MINEM:
        df = sumar_filas_df(df, nueva_fila=energia, filas=AGRUPAMIENTOS_ENERGIAS_MINEM[energia])
    return df


def simplificar_usos(df):
    df_usos = df.transpose()
    df_usos = sumar_filas_df(df_usos, nueva_fila="Oferta Interna", filas=AGRUPACION_OFERTA_INTERNA, borrar=False)
    for uso in AGRUPACION_USOS_PROPIA:
        df_usos = sumar_filas_df(df_usos, nueva_fila=uso, filas=AGRUPACION_USOS_PROPIA[uso])
    df = df_usos.transpose()
    return df


def get_yr(panel, yr):
    """Devuelve la data correspondiente a un año del panel de microdatos con los nombres de energías y usos completos."""
    df = panel[yr].rename(columns=ALIAS, index=ALIAS)
    df = corregir_signo_consumo(df)
    df = calcular_perdidas(df)
    df = adaptar_df_a_entidades_minem(df)
    df = simplificar_usos(df)
    return df


def corregir_signo_consumo(df):
    # Corrijo signo de rubros de consumo para que "reciban" de las distintas formas de energía
    for consumo in ["Consumo No Energético", "Residencial", "Comercial", "Transporte", "Agropecuario", "Industria"]:
        df[consumo] = -df[consumo]
    return df


def generar_links(df):
    df = df.drop(OFERTA, axis=1)
    links = list()
    # Genero links directamente desde los microdatos cuando es posible
    for energia in df.index:
        for uso in df.columns:
            value = df.loc[unicode(energia), uso]
            if round(value, 2) < -0.01:
                links.append({"source": energia, "target": uso, "value": round(abs(value), 2)})
            elif round(value, 2) > 0.01:
                links.append({"source": uso, "target": energia, "value": round(abs(value), 2)})

    return links


def convertir_nombres_link_a_ids(link):
    return {
        "source": NODOS_NOMBRE_A_IDX[link["source"]],
        "target": NODOS_NOMBRE_A_IDX[link["target"]],
        "value": link["value"]
    }


def convertir_nombres_lista_links_a_ids(lista_links):
    return [convertir_nombres_link_a_ids(l) for l in lista_links]


def tooltip_energia(df, nombre_energia):
    energia = df.loc[nombre_energia]
    tooltip = {
        "produccion": round(energia["Producción"], 2),
        "importacion": round(energia["Importación"], 2),
        "exportacion": round(energia["Exportación"], 2),
        "perdidas": round(energia["Pérdidas"], 2),
        "otros": round(energia["Otros Conceptos de Oferta"], 2),
        "oferta_interna": round(energia["Oferta Interna"], 2)
    }
    return tooltip


def generar_tooltips_energias(df):
    tooltips = {energia: tooltip_energia(df, energia)
                for energia in df.index
                if energia != "Pérdidas"}
    return tooltips


def tooltip_centro(df, nombre_centro):
    centro = df.loc[nombre_centro]
    perdida = round(centro["Pérdidas"], 2)
    centro = centro.drop("Pérdidas")
    tooltip = {
        "consumo": round(sum([abs(i) for i in centro if i < 0], 2)),
        "produccion": round(sum([i for i in centro if i > 0]), 2),
        "perdida": perdida
    }
    return tooltip


def generar_tooltips_centros(df):
    df_centros = df.transpose()
    tooltips = {
        centro: tooltip_centro(df_centros, centro)
        for centro in CENTROS_TRANSFORMACION_FINALES}
    return tooltips


def tooltip_consumo(df, nombre_consumo):
    consumo = df.loc[nombre_consumo]
    return {"consumo": round(sum([abs(i) for i in consumo]), 2)}


def generar_tooltips_consumos(df):
    df_consumos = df.transpose()
    tooltips = {
        consumo: tooltip_consumo(df_consumos, consumo)
        for consumo in CONSUMOS}
    return tooltips


def componer_nodos(nodos_base, tooltips):
    nodos_compuestos = list()
    for nodo_base in nodos_base:
        nodo_compuesto = nodo_base.copy()
        nombre_nodo = nodo_compuesto["nombre"]
        if nombre_nodo in tooltips:
            nodo_compuesto.update(tooltips[nombre_nodo])

        nodos_compuestos.append(nodo_compuesto)
    return nodos_compuestos


def write_json(obj, path):
    """Escribo un objeto a un archivo JSON con codificación UTF-8."""
    obj_str = json.dumps(obj, indent=4, separators=(",", ": "),
                         ensure_ascii=False)
    with io.open(path, "w", encoding='utf-8') as target:
        target.write(obj_str)


def generar_tooltips(df):
    tooltips_energias = generar_tooltips_energias(df)
    tooltips_centros = generar_tooltips_centros(df)
    tooltips_consumos = generar_tooltips_consumos(df)
    tooltips = dict()
    tooltips.update(tooltips_energias)
    tooltips.update(tooltips_centros)
    tooltips.update(tooltips_consumos)

    return tooltips


def ajustar_nodos(nodos, df):
    for nodo in nodos:
        if nodo["posicionY"] is None:
            if "consumo" in nodo:
                nodo["posicionY"] = nodo["consumo"]
            elif "oferta_interna" in nodo:
                nodo["posicionY"] = nodo["oferta_interna"]

        if nodo["nombre"] == "Pérdidas":
            nodo["consumo"] = round(
                (sum([abs(i) for i in df.loc["Pérdidas"]]) +
                 sum([abs(i) for i in df.loc[:, "Pérdidas"]])),
                2)

        if nodo["nombre"] == "borrar":
            nodo["oferta_interna"] = 1

    return nodos


def generar_datos_anio(panel, yr):
    df = get_yr(panel, yr)

    tooltips = generar_tooltips(df)

    nodos = componer_nodos(NODOS_BASE, tooltips)

    nodos = ajustar_nodos(nodos, df)

    links = generar_links(df)
    links_con_id = convertir_nombres_lista_links_a_ids(links)

    datos = {"nodes": nodos, "links": links_con_id}

    return datos


def escribir_datos(panel):
    for yr in panel.items:
        datos = generar_datos_anio(panel, yr)
        write_json(datos, "output/data_{}.json".format(yr))


if __name__ == "__main__":
    with open(sys.argv[1]) as panel_pickle:
        panel = pickle.load(panel_pickle)

    escribir_datos(panel)
