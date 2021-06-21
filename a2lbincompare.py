from pya2l import DB, model
from pya2l.api import inspect
from sys import argv

db = DB()
# session = db.import_a2l(argv[1])
session = db.open_existing(argv[1])
data1 = open(argv[2], "rb").read()
data2 = open(argv[3], "rb").read()


def calc_map_size(characteristic):
    data_sizes = {
        "UWORD": 2,
        "UBYTE": 1,
        "SBYTE": 1,
        "SWORD": 2,
        "ULONG": 4,
        "SLONG": 4,
        "FLOAT32_IEEE": 4,
    }
    data_size = data_sizes[characteristic.deposit.fncValues["datatype"]]
    map_size = data_size
    for axis_ref in characteristic.axisDescriptions:
        map_size *= axis_ref.maxAxisPoints
    return map_size


characteristics = (
    session.query(model.Characteristic).order_by(model.Characteristic.name).all()
)
for c in characteristics:
    # print(inspect.Characteristic(session, c.name))
    characteristic_data = inspect.Characteristic(session, c.name)
    map_size = calc_map_size(characteristic_data)
    offset = characteristic_data.address - 0xA0800000
    data1_map = data1[offset : offset + map_size]
    data2_map = data2[offset : offset + map_size]
    is_match = data1_map == data2_map
    if not is_match:
        print(
            characteristic_data.name + " : " + characteristic_data.longIdentifier
        )  #  " @ " + hex(offset) + ":" + hex(offset+map_size) +

# measurements = session.query(model.Measurement).order_by(model.Measurement.name).all()
# for m in measurements:
#    print(inspect.Measurement(session, m.name))
#    print(inspect.CompuMethod(session, m.conversion))
