import argparse
import json
import os
from pathlib import Path
from binary_reader import BinaryReader

# extract the file


def extract_file(rsl, extract_folder, filename, end_pointer):
    global res_count
    Path(extract_folder).mkdir(parents=True, exist_ok=True)
    with open(f'{extract_folder}/{filename}', 'wb') as f:
        f.write(rsl.buffer()[rsl.pos():end_pointer])
    res_count += 1


def extract_strings(br, str_count):
    # strings are xor-ed
    br = BinaryReader(bytearray(map(lambda x: x ^ 0x8D, br.buffer())))
    string_list = []
    for _ in range(str_count):
        string_list.append(br.read_str())
    return string_list


def read_string_table(rsl):
    global res_count
    strings = {}
    header_pos = rsl.pos()
    string_count = rsl.read_uint32()
    rsl.seek(4, 1)  # string pointer pointer
    strings['Flag'] = rsl.read_uint32()
    rsl.seek(4, 1)  # padding
    string_pointers = []
    for _ in range(string_count):
        string_pointers.append(rsl.read_uint32())
    str_start = string_pointers[0] + header_pos
    br = BinaryReader(rsl.buffer()[str_start:rsl.size()])
    strings['Strings'] = extract_strings(br, string_count)

    return strings

# read resources from RMHG


def read_resources(rsl, header_pos, extract_folder, str_list):
    res_data = {}
    resource_pointer = rsl.read_uint32()
    size = rsl.read_uint32()
    # is attribute? true/false/disabled?
    res_data['Attribute'] = rsl.read_uint32()
    if res_data['Attribute']:
        res_data['Type'] = 'Attribute'
    else:
        res_data['Type'] = 'File'
    res_data['Version'] = rsl.read_uint32()
    res_data['Resource ID'] = rsl.read_uint32()
    try:
        res_data['Resource Name'] = str_list[res_data['Resource ID']]
    except(IndexError):
        res_data['Resource Name'] = None
    rsl.seek(12, 1)  # padding
    resource_offset = resource_pointer + header_pos
    if res_data['Attribute'] < 2:
        with rsl.seek_to(resource_offset):
            with rsl.seek_to(0, 1):  # read magic
                try:
                    resource_magic = rsl.read_str(4)
                except(UnicodeDecodeError): #in case the file has no magic
                    resource_magic = 'Unk'

            if resource_magic == 'RMHG':
                res_data['Resource'] = rmhg(
                    rsl, f"{extract_folder}/{res_data['Resource Name']}", str_list)

            else:
                end_pointer = size + header_pos + resource_pointer
                extract_file(rsl, extract_folder,
                             res_data['Resource Name'], end_pointer)

    return res_data


# load the RMHG


def rmhg(rsl, extract_folder, str_list):
    header_pos = rsl.pos()
    rmhg_data = {}
    rmhg_data['Type'] = rsl.read_str(4)  # RMHG or GHMR
    if rmhg_data['Type'] == 'GHMR':  # big endian
        rsl.set_endian(True)
    resource_num = rsl.read_uint32()
    attr_ptr = rsl.read_uint32()
    rmhg_data['Version'] = rsl.read_uint32()
    str_table_ptr = rsl.read_uint32()

    if str_table_ptr > 0:  # extract strings
        str_table_ptr += header_pos
        with rsl.seek_to(str_table_ptr):
            str_info = read_string_table(rsl)
            str_list = str_info['Strings']
            rmhg_data['String flag'] = str_info['Flag']

    # go to attributes
    rmhg_data['Data'] = []
    attribute_pos = attr_ptr + header_pos
    rsl.seek(attribute_pos)
    for i in range(resource_num):
        rmhg_data['Data'].append(read_resources(
            rsl, header_pos, extract_folder, str_list))

    return rmhg_data


def extract(input_file):
    global res_count
    res_count = 0

    file = open(input_file, 'rb')
    rsl = BinaryReader(file.read())
    file.close()
    extract_folder = input_file[:-4]

    print(f'Extracting {input_file}...')
    data = rmhg(rsl, extract_folder, None)

    with open((f'{extract_folder}/rsl_data.json'), 'w') as fp:
        json.dump(data, fp, indent=2)


def main():
    global res_count
    parser = argparse.ArgumentParser()
    parser.add_argument("input",  help='Input file (.rsl)',
                        type=str, nargs='+')
    args = parser.parse_args()

    input_files = args.input
    file_count = 0
    for file in input_files:
        extract(file)
        file_count += 1
    print(f'{file_count} file(s) unpacked.')
    os.system('pause')


if __name__ == "__main__":
    main()
