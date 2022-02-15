import csv
from pathlib import Path
from sys import argv
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

ecm_odx = list(Path(argv[1]).glob("EV_*"))[0].read_text(encoding='utf8')
ecm_layer = ET.fromstring(ecm_odx)

controlmodule_file = list(Path(argv[1]).glob("BL_LIBEnginContrModulUDS_*.odx"))
if len(controlmodule_file) > 0:
    controlmoduleuds_odx = list(Path(argv[1]).glob("BL_LIBEnginContrModulUDS_*.odx"))[0].read_text(encoding='utf8')
else:
    controlmoduleuds_odx = list(Path(argv[1]).glob("BV_Engin*.odx"))[0].read_text(encoding='utf8')

control_module_layer = ET.fromstring(controlmoduleuds_odx)

layers = [control_module_layer, ecm_layer]

layers_by_name = {}

def load_layer_by_name(layer_name):
    if layer_name in layers_by_name:
        return layers_by_name[layer_name]
    filepath = list(Path(argv[1]).glob(layer_name + "*.odx"))[0]
    layers_by_name[layer_name] = ET.fromstring(filepath.read_text(encoding='utf-8'))
    return layers_by_name[layer_name]

def layer_ref(layer, element):
    doc_name = element.get("DOCREF")
    if doc_name:
        layer = load_layer_by_name(doc_name)
    return layer

def table_row_to_conversion(layer: Element, table_row: Element):
    structure_ref = table_row.find("STRUCTURE-REF")
    structure_id = structure_ref.get("ID-REF")
    layer = layer_ref(layer, structure_ref)
    structure = layer.find(f".//STRUCTURE[@ID='{structure_id}']")
    dop_ref = structure.find('.//PARAM/DOP-REF')
    if dop_ref is None:
        dop_ref = structure.find('.//PARAM/DOP-SNREF')
        dop_shortname = dop_ref.get("SHORT-NAME")
        layer = layer_ref(layer, dop_ref)
        data_format = layer.find(f".//DATA-OBJECT-PROP[@ID='{dop_shortname}']")
    else: 
        dop_id = dop_ref.get("ID-REF")
        layer = layer_ref(layer, dop_ref)
        data_format = layer.find(f".//DATA-OBJECT-PROP[@ID='{dop_id}']")
    equation = ""
    byte_length = 0
    diag_type = ""
    unit_display_name = ""
    if data_format:
        unit_ref = data_format.find("UNIT-REF")
        if unit_ref is not None:
            unit_id = unit_ref.get("ID-REF")
            layer = layer_ref(layer, unit_ref)
            unit = layer.find(f".//UNIT[@ID='{unit_id}']")
            unit_display_name = unit.find("DISPLAY-NAME").text
        diag_type = data_format.find("DIAG-CODED-TYPE").get("BASE-DATA-TYPE")
        byte_length_val = data_format.find("DIAG-CODED-TYPE/BIT-LENGTH")
        if byte_length_val is not None: 
            byte_length = int(byte_length_val.text) / 8
        numer_factors = data_format.findall(".//COMPU-RATIONAL-COEFFS//COMPU-NUMERATOR//V")
        denom_factors = data_format.findall(".//COMPU-RATIONAL-COEFFS//COMPU-DENOMINATOR//V")
        if len(numer_factors) > 0 and len(denom_factors) > 0:
            equation = f"( {numer_factors[1].text} * X + {numer_factors[0].text} ) / {denom_factors[0].text}"
    return (diag_type, byte_length, equation, unit_display_name)

dtcs = []

for dtc in ecm_layer.findall(".//DTC"):
    dtc_code = dtc.find("TROUBLE-CODE").text
    dtc_pcode = dtc.find("DISPLAY-TROUBLE-CODE").text
    dtc_name = dtc.find("TEXT").text
    dtc_symbol = dtc.get("OID")
    dtcs.append(
        {
            'code': dtc_code,
            'pcode': dtc_pcode,
            'name': dtc_name,
            'symbol': dtc_symbol
        }
    )

diag_info = []


with open("dtc.csv", "w", newline="") as csvfile:
    fieldnames = [
        "code", "pcode", "name", "symbol"
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for info in dtcs:
        writer.writerow(info)   

for ident_table in ecm_layer.findall(".//DATA-OBJECT-PROP[@ID='DOP_TEXTTABLERecorDataIdentMeasuValue']"):
    for measurement_value in ident_table.findall(".//COMPU-SCALE"):
        identifier = int(measurement_value.find(".//LOWER-LIMIT").text).to_bytes(2, 'big').hex()
        key = measurement_value.find(".//VT").text
        for layer in layers:
            table_row_ref = layer.find(f".//TABLE[@ID='TAB_RecorDataIdentMeasuValue']/TABLE-ROW/KEY[. = '{key}']/..")
            if table_row_ref is not None:
                row_layer = layer
                break
        if table_row_ref:
            name = table_row_ref.find("LONG-NAME").text
            description = table_row_ref.find("DESC")
            if description:
                description_text = ''.join(description.itertext()).replace("\n","").strip()
            else:
                description_text = name
            (diag_type, byte_length, equation, unit_display_name) = table_row_to_conversion(row_layer, table_row_ref)
            diag_info.append(
                {
                    'identifier': identifier,
                    'name': name,
                    'description': description_text,
                    'unit': unit_display_name,
                    'type': diag_type,
                    'bytes': int(byte_length),
                    'equation': equation
                }
            )
        else:
            name = key
            description_text = key
            diag_info.append(
                {
                    'identifier': identifier,
                    'name': key,
                    'description': key,
                    'unit': "",
                    'type': "",
                    'bytes': "",
                    'equation': ""
                }
            )

with open("diag.csv", "w", newline="") as csvfile:
    fieldnames = [
        "identifier","name","unit","description","type","bytes","equation"
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for info in diag_info:
        writer.writerow(info)   