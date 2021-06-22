import argparse
import json
import os
from binary_reader import BinaryReader

# write files


def write_rsrc(br, data, input_file):
    try:
        file = open(f'{input_file}/{data["Resource Name"]}', 'rb')
    except:
        print(f'Cannot find {input_file}/{data["Resource Name"]}.')
        os.system('pause')
        quit()
    ext = BinaryReader(file.read())
    file.close()
    br.extend(ext.buffer())
    br.seek(ext.size(), 1)
    return br

# write strings


def write_strs(attr_br, data, string_list):
    attr_br.write_uint32(len(string_list))  # string count
    attr_br.write_uint32(16)  # String pointer pointer, always same
    attr_br.write_uint32(data['String flag'])
    attr_br.write_uint32(0)  # Padding

    str_br = BinaryReader()
    table_size = (4 * len(string_list)) + 16

    for i in range(len(string_list)):
        attr_br.write_uint32(str_br.pos() + table_size)
        str_br.write_str(string_list[i], null=True)

    buf_xord = bytearray(
        map(lambda x: x ^ 0x8D, str_br.buffer()))  # xor the strings
    attr_br.extend(buf_xord)
    attr_br.seek(len(buf_xord), 1)
    return attr_br

# write attributes


def write_attr(attr_br, data, input_file, string_list):
    br_internal = BinaryReader()
    header_end = (len(data['Data']) + 1) * 32
    for i in range(len(data['Data'])):
        start_pos = br_internal.pos()
        attr_br.write_uint32(start_pos + header_end)
        if data['Data'][i]['Resource Name'] != None:
            string_list[data['Data'][i]['Resource ID']
                        ] = data['Data'][i]['Resource Name']
        if 'Resource' in data['Data'][i]:
            write_rmhg(br_internal, data['Data'][i]['Resource'],
                       f"{input_file}/{data['Data'][i]['Resource Name']}", string_list)
        elif data['Data'][i]['Resource Name'] != None:
                br_internal = write_rsrc(br_internal, data['Data'][i], input_file)

        attr_br.write_uint32(br_internal.size() - start_pos)
        attr_br.write_uint32(data['Data'][i]['Attribute'])
        attr_br.write_uint32(data['Data'][i]['Version'])
        attr_br.write_uint32(data['Data'][i]['Resource ID'])
        attr_br.write_uint64(0)  # Padding
        attr_br.write_uint32(0)  # Padding

    attr_br.extend(br_internal.buffer())
    attr_br.seek(br_internal.size(), 1)
    return attr_br, string_list

# write rmhg


def write_rmhg(rsl, data, input_file, string_list):
    if "String flag" in data:
        string_list = {}
    if data['Type'] == 'GHMR':  # big endian
        rsl.set_endian(True)
    rsl.write_str(data['Type'])  # Magic
    rsl.write_uint32(len(data['Data']))  # Resource count
    rsl.write_uint32(32)  # Attribute Offset
    rsl.write_uint32(data['Version'])  # Version
    attr_br = BinaryReader()
    attr_br, string_list = write_attr(attr_br, data, input_file, string_list)

    if "String flag" in data:
        rsl.write_uint32((attr_br.pos() + 32))
        attr_br = write_strs(attr_br, data, string_list)
    else:
        rsl.write_uint32(0)  # when there's no string table

    rsl.write_uint64(0)  # Padding
    rsl.write_uint32(0)  # Padding

    rsl.extend(attr_br.buffer())
    rsl.seek(attr_br.size(), 1)


def repack(input_file):
    try:
        with open(f'{input_file}/rsl_data.json') as f:
            data = json.loads(f.read())
    except:
        print(
            f'Could not find {input_file}/rsl_data.json. Please unpack the file again.')
        os.system('pause')
        return False

    rsl = BinaryReader()

    print(f'Repacking {input_file}...')
    write_rmhg(rsl, data, input_file, None)
    with open(f'{input_file}.rsl', 'wb') as f:
        f.write(rsl.buffer())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input",  help='Input file (.rsl)',
                        type=str, nargs='+')
    args = parser.parse_args()

    input_files = args.input
    file_count = 0
    for file in input_files:
        if repack(file) != False:
            file_count += 1
    print(f'{file_count} file(s) repacked.')
    os.system('pause')


if __name__ == "__main__":
    main()
