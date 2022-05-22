import csv
import re
import uuid

from os import path
from pya2l import DB, model
from pya2l.api import inspect
from sys import argv
from xml.etree.ElementTree import Element, SubElement, Comment, ElementTree
import xml.etree.ElementTree as ET

import pprint

USE_CONSTANTS = False  # Should we use "constants" / "scalars" in the XML? They kind of aren't good at all...

db = DB()
session = (
    db.open_existing(argv[1]) if path.exists(f"{argv[1]}db") else db.import_a2l(argv[1])
)

BASE_OFFSET = (
    session.query(model.MemorySegment)
    .filter(model.MemorySegment.name == "_ROM")
    .first()
    .address
)

data_sizes = {
    "UWORD": 2,
    "UBYTE": 1,
    "SBYTE": 1,
    "SWORD": 2,
    "ULONG": 4,
    "SLONG": 4,
    "FLOAT32_IEEE": 4,
}

storage_types = {
    "UBYTE": 'uint8',
    "SBYTE": 'int8',
    "UWORD": 'uint16',
    "SWORD": 'int16',
    "ULONG": 'uint32',
    "SLONG": 'int32',
    "FLOAT32_IEEE": 'float',
}

tables_in_xml = {
    "name": False,
    }

# XML Serialization methods

categories = []


def xml_root_with_configuration(title):
    root = Element("ecus")

    xmlheader = SubElement(root, "ecu_struct")
    xmlheader.set('id',str(title).rstrip(".a2l").lstrip(".\\"))
    xmlheader.set('type',str(title).rstrip(".a2l").lstrip(".\\"))
    xmlheader.set('include',"")
    xmlheader.set('desc_size',"#7FC00")
    xmlheader.set('reverse_bytes',"False")
    xmlheader.set('ecu_type',"vag")
    xmlheader.set('flash_template',"")
    xmlheader.set('checksum',"")

    return [root, xmlheader]


def xml_table_with_root(root: Element, table_def):
    axis_count = 1
    if "x" in table_def:
        axis_count += 1
    if "y" in table_def:
        axis_count += 1
        
    table = SubElement(root, "map")
    table.set('name',table_def["title"])
    table.set("type",str(axis_count))
    table.set("help",table_def["description"])
    table.set("class","|".join(table_def["category"]))

    data = SubElement(table,"data")
    data.set("offset","#"+table_def['z']['address'].lstrip("0x"))
    data.set("storagetype",str(storage_types[table_def['z']["dataSize"]]))
    data.set("func_2val",table_def['z']['math'])
    data.set("func_val2",table_def['z']['math2'])
    data.set("format","%0.2f")
    data.set("metric",table_def['z']['units'])
    data.set("min",str(table_def['z']['min']))
    data.set("max",str(table_def['z']['max']))
    data.set("order", "rc")

    if "x" in table_def:
        rows = SubElement(table,"cols")
        rows.set("count",str(table_def['x']['length']))
        rows.set("offset","#"+table_def['x']['address'].lstrip("0x"))
        rows.set("storagetype",str(storage_types[table_def['x']["dataSize"]]))
        rows.set("func_2val",table_def['x']['math'])
        rows.set("func_val2",table_def['x']['math2'])
        rows.set("format","%0.2f")
        rows.set("metric",table_def['x']['units'])


    if "y" in table_def:
        cols = SubElement(table,"rows")
        cols.set("count",str(table_def['y']['length']))
        cols.set("offset","#"+table_def['y']['address'].lstrip("0x"))
        cols.set("storagetype",str(storage_types[table_def['y']["dataSize"]]))
        cols.set("func_2val",table_def['y']['math'])
        cols.set("func_val2",table_def['y']['math2'])
        cols.set("format","%0.2f")
        cols.set("metric",table_def['y']['units'])
  

    return table


def calc_map_size(characteristic: inspect.Characteristic):
    data_size = data_sizes[characteristic.deposit.fncValues["datatype"]]
    map_size = data_size
    for axis_ref in characteristic.axisDescriptions:
        map_size *= axis_ref.maxAxisPoints
    return map_size


def adjust_address(address):
    return address - BASE_OFFSET


# A2L to "normal" conversion methods


def fix_degree(bad_string):
    return re.sub(
        "\uFFFD", "\u00B0", bad_string
    )  # Replace Unicode "unknown" with degree sign


def axis_ref_to_dict(axis_ref: inspect.AxisDescr):
    axis_value = {
        "name": axis_ref.axisPtsRef.name,
        "units": fix_degree(axis_ref.axisPtsRef.compuMethod.unit),
        "min": axis_ref.lowerLimit,
        "max": axis_ref.upperLimit,
        "address": hex(
            adjust_address(axis_ref.axisPtsRef.address)
            + data_sizes[axis_ref.axisPtsRef.depositAttr.axisPts["x"]["datatype"]]
        ),  # We need to offset the axis by 1 value, the first value is another length
        "length": axis_ref.maxAxisPoints,
        "dataSize": axis_ref.axisPtsRef.depositAttr.axisPts["x"]["datatype"],
    }
    if len(axis_ref.compuMethod.coeffs) > 0:
        axis_value["math"] = coefficients_to_equation(axis_ref.compuMethod.coeffs, False)
    else:
        axis_value["math"] = "X"

    if len(axis_ref.compuMethod.coeffs) > 0:
        axis_value["math2"] = coefficients_to_equation(axis_ref.compuMethod.coeffs, True)
    else:
        axis_value["math2"] = "X"
        
    return axis_value


def coefficients_to_equation(coefficients, inverse):
    a, b, c, d, e, f = (
        str(coefficients["a"]),
        str(coefficients["b"]),
        str(coefficients["c"]),
        str(coefficients["d"]),
        str(coefficients["e"]),
        str(coefficients["f"]),
    )

    operation = ""
    if inverse is True:
        operation = f"({b} * ([x] / {f})) + {c}"
    else:
        operation = f"(({f} * [x]) - {c}) / {b}"
        
    if a == "0.0" and d == "0.0" and e=="0.0" and f!="0.0":  # Polynomial is of order 1, ie linear original: f"(({f} * [x]) - {c} ) / ({b} - ({e} * [x]))"
        return operation
    else:
        return "Cannot handle polynomial ratfunc because we do not know how to invert!"


# Begin

root, xmlheader = xml_root_with_configuration(argv[1])

with open(argv[2], encoding="utf-8-sig") as csvfile:
    print("Enhance...")
    csvreader = csv.DictReader(csvfile)
    for row in csvreader:
        tablename = row["Table Name"]
        category = row["Category 1"]
        category2 = row["Category 2"]
        category3 = row["Category 3"]
        custom_name = row["Custom Name"]
        characteristics = (
            session.query(model.Characteristic)
            .order_by(model.Characteristic.name)
            .filter(model.Characteristic.name == tablename)
            .first()
        )
        if characteristics is None:
            print("******** Could not find ! ", tablename)
            continue
        c_data = inspect.Characteristic(session, tablename)
        table_offset = adjust_address(c_data.address)
        table_length = calc_map_size(c_data)
        axisDescriptions = c_data.axisDescriptions


        table_def = {
            "title": c_data.longIdentifier,
            "description": c_data.displayIdentifier,
            "category": [category],
            "z": {
                "min": c_data.lowerLimit,
                "max": c_data.upperLimit,
                "address": hex(adjust_address(c_data.address)),
                "dataSize": c_data.deposit.fncValues["datatype"],
                "units": fix_degree(c_data.compuMethod.unit),
            },
        }

        if custom_name is not None and len(custom_name) > 0:
            table_def["description"] += f'|Original Name: {table_def["title"]}'
            table_def["title"] = custom_name

        duplicate = 0
        check_title = table_def["title"]
        while check_title in tables_in_xml:
            duplicate += 1
            check_title += " "

        tables_in_xml[check_title] = True
        if check_title != table_def["title"]:
            id_name = table_def["description"]
            table_def["title"] += f" [{id_name}]" #f" {duplicate}"
            #print(table_def["title"])
        
        tables_in_xml[table_def["title"]] = True
        

        if category2 is not None and len(category2) > 0:
            table_def["category"].append(category2)
            
        if category3 is not None and len(category3) > 0:
            table_def["category"].append(category3)

        if len(c_data.compuMethod.coeffs) > 0:
            table_def["z"]["math"] = coefficients_to_equation(c_data.compuMethod.coeffs, False)
        else:
            table_def["z"]["math"] = "X"

        if len(c_data.compuMethod.coeffs) > 0:
            table_def["z"]["math2"] = coefficients_to_equation(c_data.compuMethod.coeffs, True)
        else:
            table_def["z"]["math2"] = "X"

        if len(axisDescriptions) == 0 and USE_CONSTANTS is True:
            table_def["constant"] = True
        if len(axisDescriptions) > 0:
            table_def["x"] = axis_ref_to_dict(axisDescriptions[0])
            table_def["z"]["length"] = table_def["x"]["length"]
            table_def["description"] += f'|X: {table_def["x"]["name"]}'
        if len(axisDescriptions) > 1:
            table_def["y"] = axis_ref_to_dict(axisDescriptions[1])
            table_def["description"] += f'|Y: {table_def["y"]["name"]}'
            table_def["z"]["rows"] = table_def["y"]["length"]

        table = xml_table_with_root(xmlheader, table_def)

ElementTree(root).write(f"{argv[1]}.xml")
