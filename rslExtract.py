import argparse
import json
import os
from pathlib import Path
from binary_reader import BinaryReader
import time


def extract_file(rsl, extract_folder, filename, end_pointer):
    try:
        Path(extract_folder).mkdir(parents=True, exist_ok=True)
    except(FileExistsError):
        print(
            f'File {extract_folder}/{filename} already exists, unable to create.')

    with open(f'{extract_folder}/{filename}', 'wb') as f:
        f.write(rsl.buffer()[rsl.pos():end_pointer])


def extract_strings(br, str_count, version):
    if version > 1040:  # strings are xor-ed in newer versions
        br = BinaryReader(bytearray(map(lambda x: x ^ 0x8D, br.buffer())))
    string_list = []
    for _ in range(str_count):
        string_list.append(br.read_str())
    return string_list


def read_string_table(rsl, version):
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
    strings['Strings'] = extract_strings(br, string_count, version)

    return strings


def read_resources(rsl, header_pos, extract_folder, str_list, recurse_mode):
    res_data = {}
    resource_pointer = rsl.read_uint32()
    size = rsl.read_uint32()
    res_data['Flags'] = rsl.read_uint32()

    res_data['Version'] = rsl.read_uint32()
    res_data['Resource ID'] = rsl.read_int32()
    rsl.seek(12, 1)  # padding
    if res_data['Resource ID'] > -1:
        res_data['Resource Name'] = str_list[res_data['Resource ID']]
    else:
        res_data['Resource Name'] = ""  # no folder

    if size > 0:
        resource_offset = resource_pointer + header_pos
        with rsl.seek_to(resource_offset):
            if res_data['Flags'] > 0:
                with rsl.seek_to(0, 1):  # read magic
                    resource_magic = rsl.read_str(4)
                if resource_magic == 'RMHG':
                    res_data['Resource'] = rmhg(
                        rsl, f"{extract_folder}/{res_data['Resource Name']}", str_list, recurse_mode)
                else:
                    print(
                        "This message shouldn't have appeared,\nplease report it to the tool's creator\nalong with the file you tried to extract.")

            # recursively unpack RSLs
            elif recurse_mode and res_data['Resource Name'].lower().endswith('.rsl'):
                res_data['Resource'] = rmhg(
                    rsl, f"{extract_folder}/{res_data['Resource Name']}", str_list, recurse_mode)
            else:
                end_pointer = size + header_pos + resource_pointer
                extract_file(rsl, extract_folder,
                             res_data['Resource Name'], end_pointer)
    else:
        # just to separate this from actual missing files in repacker
        res_data['No file'] = True

    return res_data


def rmhg(rsl, extract_folder, str_list, recurse_mode):
    header_pos = rsl.pos()
    rmhg_data = {}
    rmhg_data['Type'] = rsl.read_str(4)  # RMHG
    resource_num = rsl.read_uint32()
    attr_ptr = rsl.read_uint32()
    rmhg_data['Version'] = rsl.read_uint32()
    str_table_ptr = rsl.read_uint32()

    if str_table_ptr > 0:  # extract strings
        str_table_ptr += header_pos
        with rsl.seek_to(str_table_ptr):
            str_info = read_string_table(rsl, rmhg_data['Version'])
            str_list = str_info['Strings']
            rmhg_data['String flag'] = str_info['Flag']

    # go to attributes
    rmhg_data['Data'] = []
    attribute_pos = attr_ptr + header_pos
    rsl.seek(attribute_pos)
    for _ in range(resource_num):
        rmhg_data['Data'].append(read_resources(
            rsl, header_pos, extract_folder, str_list, recurse_mode))

    return rmhg_data


def extract(input_file, recurse_mode):
    file = open(input_file, 'rb')
    rsl = BinaryReader(file.read())
    file.close()
    extract_folder = input_file[:-4]

    print(f'Extracting {input_file}...')
    data = rmhg(rsl, extract_folder, None, recurse_mode)

    Path(extract_folder).mkdir(parents=True, exist_ok=True)
    with open((f'{extract_folder}/rsl_data.json'), 'w') as fp:
        json.dump(data, fp, indent=2)


def check_file(input_file, recurse_mode):
    file = open(input_file, 'rb')
    br = BinaryReader(file.read())
    file.close()
    try:
        magic = br.read_str(4)
        if magic == 'RMHG':
            extract(input_file, recurse_mode)
        else:
            print(
                "Invalid file, skipping. If this is an .rsl file, please report this to the tool's creator.")
            return False
    except:
        print("Failed to unpack file, skipping. If this is an .rsl file, please report this to the tool's creator.")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input",  help='input file (.rsl)',
                        type=str, nargs='+')
    parser.add_argument('--no-recurse',  help='disable recursive extraction of RSL files', dest='recurse', action='store_false')
    parser.set_defaults(recurse=True)
    args = parser.parse_args()

    input_files = args.input
    file_count = 0
    for file in input_files:
        if check_file(file, args.recurse) != False:
            file_count += 1
    print(f'{file_count} file(s) unpacked.')
    time.sleep(2)


if __name__ == "__main__":
    main()
