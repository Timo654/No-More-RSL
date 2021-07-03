import argparse
import json
import os
from binary_reader import BinaryReader
import time


def write_rsrc(br, data, input_file):
    try:
        file = open(f'{input_file}/{data["Resource Name"]}', 'rb')
    except:
        print(f'Cannot find {input_file}/{data["Resource Name"]}.')
    ext = BinaryReader(file.read())
    file.close()
    br.extend(ext.buffer())
    br.seek(ext.size(), 1)
    return br

# write strings


def write_strs(attr_br, data, string_list, version):
    attr_br.write_uint32(len(string_list))  # string count
    attr_br.write_uint32(16)  # String pointer pointer, always same
    attr_br.write_uint32(data['String flag'])
    attr_br.write_uint32(0)  # Padding

    str_br = BinaryReader()
    table_size = (4 * len(string_list)) + 16

    for i in range(len(string_list)):
        attr_br.write_uint32(str_br.pos() + table_size)
        str_br.write_str(string_list[i], null=True)

    if version > 1040:
        buf = bytearray(
            map(lambda x: x ^ 0x8D, str_br.buffer()))  # xor the strings
    else:
        buf = str_br.buffer()
    attr_br.extend(buf)
    attr_br.seek(len(buf), 1)
    return attr_br


def write_attr(attr_br, data, input_file, string_list):
    br_internal = BinaryReader()
    header_end = (len(data['Data']) + 1) * 32
    for i in range(len(data['Data'])):
        start_pos = br_internal.pos()
        attr_br.write_uint32(start_pos + header_end)
        if data['Data'][i]['Resource ID'] > -1:
            string_list[data['Data'][i]['Resource ID']
                        ] = data['Data'][i]['Resource Name']
        if 'No file' not in data['Data'][i]:
            if 'Resource' in data['Data'][i]:
                write_rmhg(br_internal, data['Data'][i]['Resource'],
                           f"{input_file}/{data['Data'][i]['Resource Name']}", string_list)
            else:
                br_internal = write_rsrc(
                    br_internal, data['Data'][i], input_file)

            attr_br.write_uint32(br_internal.size() - start_pos)
        else:
            attr_br.write_uint32(0)  # Pointer is 0
        attr_br.write_uint32(data['Data'][i]['Flags'])
        attr_br.write_uint32(data['Data'][i]['Version'])
        attr_br.write_int32(data['Data'][i]['Resource ID'])
        attr_br.write_uint64(0)  # Padding
        attr_br.write_uint32(0)  # Padding

    attr_br.extend(br_internal.buffer())
    attr_br.seek(br_internal.size(), 1)
    return attr_br, string_list


def write_rmhg(rsl, data, input_file, string_list):
    if "String flag" in data:
        string_list = {}
    rsl.write_str('RMHG')  # Magic
    rsl.write_uint32(len(data['Data']))  # Resource count
    rsl.write_uint32(32)  # Attribute Offset
    rsl.write_uint32(data['Version'])  # Version
    attr_br = BinaryReader()
    attr_br, string_list = write_attr(attr_br, data, input_file, string_list)

    if "String flag" in data:
        rsl.write_uint32((attr_br.pos() + 32))
        attr_br = write_strs(attr_br, data, string_list, data['Version'])
    else:
        rsl.write_uint32(0)  # when there's no string table

    rsl.write_uint64(0)  # Padding
    rsl.write_uint32(0)  # Padding

    rsl.extend(attr_br.buffer())
    rsl.seek(attr_br.size(), 1)


def repack(input_file, overwrite):
    try:
        with open(f'{input_file}/rsl_data.json') as f:
            data = json.loads(f.read())
    except:
        print(
            f'Could not find {input_file}/rsl_data.json. Please unpack the file again.')
        return False

    rsl = BinaryReader()

    print(f'Repacking {input_file}...')
    write_rmhg(rsl, data, input_file, None)

    if os.path.isfile(f'{input_file}.rsl') and not overwrite:
        answered = False
        while not answered:
            ask_user = input('Are you sure you want to replace the original file? Y/N\n').lower()
            if ask_user in ['yes', 'y']:
                answered = True
            elif ask_user in ['no', 'n']:
                input_file = f'{input_file}_new'
                answered = True

    with open(f'{input_file}.rsl', 'wb') as f:
        f.write(rsl.buffer())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input",  help='input file (.rsl)',
                        type=str, nargs='+')
    parser.add_argument('--overwrite',  help='overwrite the original .rsl file if it exists', dest='overwrite', action='store_true')

    parser.set_defaults(overwrite=False)
    args = parser.parse_args()

    input_files = args.input
    file_count = 0
    for file in input_files:
        try:
            if repack(file, args.overwrite) != False:
                file_count += 1
        except:
            print(f'Failed to repack {file}.')
    print(f'{file_count} file(s) repacked.')
    time.sleep(2)


if __name__ == "__main__":
    main()
