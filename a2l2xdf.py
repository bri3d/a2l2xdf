import csv
from pya2l import DB, model
from pya2l.api import inspect
from sys import argv

BASE_OFFSET = 0xA0800000

db = DB()
#session = db.import_a2l(argv[1])
session = db.open_existing(argv[1])

def calc_map_size(characteristic: inspect.Characteristic):
    data_sizes = {
        'UWORD' : 2,
        'UBYTE' : 1,
        'SBYTE' : 1,
        'SWORD' : 2,
        'ULONG': 4,
        'SLONG': 4,
        'FLOAT32_IEEE': 4
    }
    data_size = data_sizes[characteristic.deposit.fncValues['datatype']]
    map_size = data_size
    for axis_ref in characteristic.axisDescriptions:
        map_size *= axis_ref.maxAxisPoints
    return map_size
def adjust_address(address):
    return address - BASE_OFFSET

def axis_ref_to_points(axis_ref: inspect.AxisDescr):
    return {
        'units': axis_ref.axisPtsRef.compuMethod.unit,
        'min': axis_ref.lowerLimit,
        'max': axis_ref.upperLimit,
        'address': hex(adjust_address(axis_ref.axisPtsRef.address)),
        'length': axis_ref.maxAxisPoints
    }


with open(argv[2]) as csvfile:
     csvreader = csv.reader(csvfile)
     for row in csvreader:
        tablename = row[1]
        if tablename == "Table Name":
            continue
        characteristics = session.query(model.Characteristic).order_by(model.Characteristic.name).filter(model.Characteristic.name == tablename).first()
        if(characteristics is None):
            print("******** Could not find ! ", tablename)
            continue
        c_data = inspect.Characteristic(session, tablename)
        table_offset = adjust_address(c_data.address)
        table_length = calc_map_size(c_data)
        axisDescriptions = c_data.axisDescriptions

        print(tablename, ":", c_data.longIdentifier, "@", hex(table_offset), c_data.lowerLimit, "-", c_data.upperLimit, c_data.deposit.fncValues['datatype'])
        for axis_ref in axisDescriptions:
          print("\t", axis_ref.axisPtsRef.name, ":", axis_ref.maxAxisPoints, "x",  axis_ref.axisPtsRef.compuMethod.unit, "@", hex(adjust_address(axis_ref.axisPtsRef.address)))

        table_def = {
            'title': c_data.longIdentifier,
            'description': c_data.name, 
            'category': row[0],
            'z': {
                'min': c_data.lowerLimit,
                'max': c_data.upperLimit,
                'address': hex(adjust_address(c_data.address)),
                'dataSize': c_data.deposit.fncValues['datatype']
            }
        }
        if len(axisDescriptions) > 0:
            table_def['x'] = axis_ref_to_points(axisDescriptions[0])
        if len(axisDescriptions) > 1:
            table_def['y'] = axis_ref_to_points(axisDescriptions[1])

        print(table_def)