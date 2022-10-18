from pya2l import DB, model
from pya2l.api import inspect
from sys import argv

db = DB()
db2 = DB()
# session = db.import_a2l(argv[1])

# CLI arguments: a2lbincompare.py [first_a2l] [first_bin] [second_a2l] [second_bin] [search_term?]

# First A2L & bin
session = db.open_existing(argv[1])
data1 = open(argv[2], "rb").read()

# Second A2L & bin
session2 = db2.open_existing(argv[3])
data2 = open(argv[4], "rb").read()

search_term = (
    argv[5] if len(argv) > 5 else None
)

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
    if search_term and (search_term not in (c.name+c.longIdentifier)):
        # Characteristic does not meet search term, continue
        continue

    # Get characteristic from both A2Ls, using the name from the first one
    characteristic_data = inspect.Characteristic(session, c.name)
    try:
        characteristic_data2 = inspect.Characteristic(session2, c.name)
    except:
        continue
        # print(c.name + " does not exist in: "+argv[3])

    # Get the map size (should be the same but best to double check)
    map_size = calc_map_size(characteristic_data)
    map_size2 = calc_map_size(characteristic_data2)

    # Get offset
    offset = characteristic_data.address - 0xA0800000
    offset2 = characteristic_data2.address - 0xA0800000

    # Get data from bin
    data1_map = data1[offset : offset + map_size]
    data2_map = data2[offset2 : offset2 + map_size2]

    # Check match
    is_match = data1_map == data2_map

    if not is_match:
        print(
            characteristic_data.name + " : " + characteristic_data.longIdentifier
        )  #  " @ " + hex(offset) + ":" + hex(offset+map_size) +
