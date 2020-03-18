#!/usr/bin/env python3
import argcomplete, argparse
import csv
import re
from pathlib import Path
import logging
import os
import sys
import itertools

try:
    import pandas as pd
except:
    sys.stderr.write("Missing python3 package pandas!")
    sys.stderr.write("Please install requirements using 'python3 install -r requirements.txt")
    sys.exit(1)

app_name = "bob"
app_version = "0.8"

# Configuration files
# ===================
# Configuration files can be placed into a folder named ".bob". Either inside the application- or
# inside the home-directory.
app_path = os.path.dirname(os.path.realpath(__file__))
app_config_path = os.path.join(app_path, ".bob")
app_config_command_format_file_path = os.path.join(app_config_path, "templates")
app_config_profile = os.path.join(app_config_path, "profile.py")
home_config_path = os.path.join(str(Path.home()), ".bob")
home_config_profile = os.path.join(home_config_path, "profile.py")
home_config_command_format_file_path = os.path.join(home_config_path, "templates")


def init_logger(app_id, log_format="%(module)s: %(lineno)d: %(msg)s"):
    logger = logging.getLogger(app_id)
    logging.root.setLevel(logging.DEBUG)
    hdlr = logging.StreamHandler(sys.stderr)
    hdlr.setFormatter(logging.Formatter(log_format))
    logger.addHandler(hdlr)
    return logger


def add_placeholder_value(data_frame, placeholder, values):
    def _add_placeholder_value(data_frame, placeholder, value):
        if placeholder in data_frame:
            data_frame[placeholder].append(value)
        else:
            data_frame[placeholder] = [value]
    if isinstance(values, list):
        for value in values:
            _add_placeholder_value(data_frame, placeholder.lower(), value)
    else:
        _add_placeholder_value(data_frame, placeholder.lower(), values)


def transform_data(command_format_string, placeholders, data_keys):
    """
    Transforms the data from a map of placeholders with value lists into a data frame.
    """
    if command_format_string:
        # Remove unused data
        for data_key in data_keys:
            if data_key not in placeholders:
                data.pop(data_key, None)

        # Remove duplicates
        for key in data:
            data[key] = set(data[key])

        # Create matrix from data e.g. (('a','d'), ('b','d'), ('c','d'))
        data_matrix = list(itertools.product(*[data[key] for key in data.keys()]))

        # Create table data from matrix e.g. { 'placeholder-1': ('a','b','c'), 'placeholder-2': ('d','d','d') }
        data_keys = list(data.keys())
        table_data = {}
        for i in range(0, len(data_matrix)):
            for j in range(0, len(data_keys)):
                add_placeholder_value(table_data, data_keys[j], data_matrix[i][j])
    else:
        # Create table data with equally sized lists by filling them with empty strings
        # e.g. { 'placeholder-1': ('a','b','c'), 'placeholder-2': ('d','','') }
        table_data = {}
        max_length = max([len(data[key]) for key in data.keys()])
        for placeholder in data.keys():
            for item in data[placeholder]:
                add_placeholder_value(table_data, placeholder, item)
            for i in range(0, max_length - len(data[placeholder])):
                add_placeholder_value(table_data, placeholder, "")

    # Create data frame from table data
    data_frame = pd.DataFrame(table_data)

    # Handle everything as string which requires that the user needs to put quotes around every value in the filter.
    # This makes it easier to write such filter-queries in the long run since no one needs to think about whether
    # to put quotes around a value or not.
    return data_frame.astype(str)


def get_profile_path():
    profile_path = ""
    if os.path.isfile(app_config_profile):
        profile_path = app_config_path
    elif os.path.isfile(home_config_profile):
        profile_path = home_config_path
    else:
        logger.warning("WARNING: Loading profile failed! File not found!")
    return profile_path


def load_profile(file_path):
    # Since the path may contain special characters which can not be processed by the __import__ function
    # we change the working directory to the path in which the profile.py is located.
    if file_path:
        try:
            current_working_directory = os.getcwd()
            os.chdir(file_path)
            profile = __import__("profile").Profile()
            os.chdir(current_working_directory)
            return profile
        except:
            pass
    return None


def get_command_template_paths():
    command_format_file_paths = []
    if os.path.exists(os.path.join(home_config_command_format_file_path)):
        command_format_file_paths.append(os.path.join(home_config_command_format_file_path))
    if os.path.exists(os.path.join(app_config_command_format_file_path)):
        command_format_file_paths.append(os.path.join(app_config_command_format_file_path))
    return command_format_file_paths


def get_reserved_placeholder_values(profile):
    reserved_placeholders = {}
    for placeholder_value in profile.placeholder_values:
        placeholder_name = placeholder_value.name
        add_placeholder_value(reserved_placeholders, placeholder_name.lower(), placeholder_value.element())
    return reserved_placeholders


def import_data_file(import_file_path, data, delimiter):
    with open(import_file_path, 'r') as f:
        reader = csv.DictReader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)
        for line in reader:
            for placeholder in line.keys():
                add_placeholder_value(data, placeholder.lower(), line[placeholder])


def get_command_template_path(command_template_paths, command_template_name):
    for command_template_path in command_template_paths:
        command_template_file = os.path.join(command_template_path, command_template_name)
        if os.path.exists(command_template_file):
           return command_template_path
    return None


def get_command_template_names(command_template_paths):
    command_format_files = []
    for command_format_file_path in command_template_paths:
        for r, d, f in os.walk(command_format_file_path):
            relpath = r[len(command_format_file_path) + 1:]
            for file in f:
                command_format_files.append(os.path.join(relpath, file))
    return list(set(command_format_files))


def bob_command_template_completer(prefix, parsed_args, **kwargs):
    command_template_paths = get_command_template_paths()
    if not command_template_paths:
        return None
    return get_command_template_names(command_template_paths)


# Always look into the current working directory first when importing modules
sys.path.insert(0, '')

logger = init_logger(app_name, "%(msg)s")

profile = load_profile(get_profile_path())
if profile is None:
    logger.error("ERROR: Loading profile failed! Invalid format!")
    sys.exit(1)

parser = argparse.ArgumentParser(
    description='Bob - the command builder',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Default placeholders:

""" + os.linesep.join(["  {} {}".format(("<" + x.name + ">").ljust(20), x.description) for x in profile.placeholder_values]) + """

Examples:

  bob -s target=localhost     -c "nmap -sS -p- <target> -oA nmap-syn-all_<target>_<date_time>"
  bob -s target:./targets.txt -c "nmap -sS -p- <target> -oA nmap-syn-all_<target>_<date_time>"
    """
)
parser.add_argument('-c', '--command-string', action="store", metavar="COMMAND_FORMAT_STRING",
                    dest='command_format_string',
                    help="The format of the command. "
                         "The placeholders are identified by less than (<) and greater than (>) signs.")
parser.add_argument('-s', '--set', action="append", metavar="PLACEHOLDER=VALUE | -s PLACEHOLDER:FILE", dest='data_set',
                    help="The value(s) used to replace the placeholder found in the command format. "
                         "Values can either be directly specified or loaded from file.")
parser.add_argument('-i', '--import', action="store", metavar="FILE", dest='import_file',
                    help="The value(s) used to replace the placeholder found in the command format. "
                         "The file should start with a header which specifies the placeholders. "
                         "The delimiter can be changed in the profile (default=\\t). ")
parser.add_argument('-t', '--template', action="store", metavar="FILE",
                    dest='command_template_name',
                    help="The template to use as command format.")\
    .completer = bob_command_template_completer
parser.add_argument('-l', '--list-templates', action="store_true",
                    dest='list_templates',
                    help="Lists all available templates.")
parser.add_argument('-f', '--filter', action="store", metavar="STRING", dest='filter',
                    help="The filter to include/exclude results (e.g. -f 'PLACEHOLDER==xx.* and PLACEHOLDER!=.*yy').")

argcomplete.autocomplete(parser)
arguments = parser.parse_args()

command_template_paths = get_command_template_paths()
if arguments.list_templates:
    if len(sys.argv) > 2:
        logger.error("ERROR: --list-templates can not be used with any other options!")
        sys.exit(1)
    command_template_names = get_command_template_names(command_template_paths)
    if not command_template_names:
        logger.warning("WARNING: No templates found!")
    for command_template_name in command_template_names:
        print(command_template_name)
    sys.exit(0)

command_format_string = arguments.command_format_string
command_template_name = arguments.command_template_name
if command_format_string and command_template_name:
    logger.error("ERROR: --command-string can not be used in conjunction with command-template!")
    sys.exit(1)

command_template_file = ""
if command_template_name:
    command_template_path = get_command_template_path(command_template_paths, command_template_name)
    if not command_template_path:
        logger.error("ERROR: Loading command file failed! The command template {} was not found!".format(command_template_name))
        sys.exit(1)
    command_template_file = os.path.join(command_template_path, command_template_name)

import_file = arguments.import_file
if import_file and not os.path.exists(import_file):
    logger.error("ERROR: Loading import file failed! The file {} was not found!".format(import_file))
    sys.exit(1)

# Map of placeholders with value lists e.g. { 'PLACEHOLDER-1': ('a','b','c'), 'PLACEHOLDER-2': ('d') }
data = {}

# Get reserved placeholders as defined within the profile
reserved_placeholder_values = get_reserved_placeholder_values(profile)

# Load data given via --set argument
if arguments.data_set:
    for placeholder_value in arguments.data_set:
        # Accepted data set format:
        #   PLACEHOLDER=VALUE
        #   PLACEHOLDER:FILE
        string_sep_pos = placeholder_value.find("=")
        file_sep_pos = placeholder_value.find(":")
        if (string_sep_pos <= 0 and file_sep_pos <= 0) or (string_sep_pos > 0 and file_sep_pos > 0):
            logger.error("ERROR: Parsing '{}' failed! Invalid format!".format(placeholder_value))
            parser.print_usage()
            sys.exit(1)
        is_value_sep = string_sep_pos > 0
        sep = "=" if is_value_sep else ":"
        if is_value_sep:
            try:
                placeholder, value = placeholder_value.split(sep)
                add_placeholder_value(data, placeholder.lower(), value)
            except:
                logger.error("ERROR: Loading placeholder value '{}' failed!".format(placeholder_value))
                sys.exit(1)
        else:
            placeholder, file = placeholder_value.split(sep)
            if not os.path.isfile(file):
                logger.error("ERROR: Loading placeholder value(s) for '{}' failed! The file {} was not found!".format(placeholder, file))
                sys.exit(1)

            try:
                with open(file) as f:
                    for value in f.read().splitlines():
                        add_placeholder_value(data, placeholder.lower(), value)
            except:
                logger.error("ERROR: Loading placeholder value(s) for '{}' failed! The file {} could not be processed!".format(placeholder, file))
                sys.exit(1)


# Load data from file given via --import argument
if import_file:
    try:
        import_data_file(import_file, data, profile.csv_delimiter if profile else '\t')
    except:
        logger.error("ERROR: Loading import file failed! The file {} has an invalid format!".format(import_file))
        sys.exit(1)

# Load template
if command_template_file:
    try:
        with open(command_template_file) as f:
            command_format_string = f.read()
    except:
        logger.error("ERROR: Loading template failed! The template {} could not be processed!".format(command_template_name))
        sys.exit(1)

placeholders = []
if command_format_string:
    # Parse placeholders from command format string
    placeholders = list(set(placeholder for placeholder in re.findall("<(\w+)>", command_format_string)))

if profile:
    reserved_placeholders = [key for key in data.keys() if key.lower() in reserved_placeholder_values]
    if reserved_placeholders:
        logger.error("ERROR: {} is/are already defined in your profile!".format(', '.join(["<" + item + ">" for item in reserved_placeholders])))
        sys.exit(1)
    for reserved_placeholder in reserved_placeholder_values:
        placeholders.append(reserved_placeholder)
        data[reserved_placeholder] = reserved_placeholder_values[reserved_placeholder]

# Retrieve data keys
data_keys = {data_key.lower() for data_key in data.keys()}

if placeholders:
    unset_placeholders = []
    for placeholder in placeholders:
        if placeholder.lower() not in data_keys:
            unset_placeholders.append(placeholder)
    if unset_placeholders:
        logger.error(
            "ERROR: Generating command(s) failed! Missing {}!".format(', '.join(["<" + item + ">" for item in unset_placeholders])))
        sys.exit(1)

data_frame = transform_data(command_format_string, [placeholder.lower() for placeholder in placeholders], data_keys)

if arguments.filter:
    try:
        # Filter data using query string defined by user
        data_frame = data_frame.query(arguments.filter)
    except:
        logger.error("ERROR: Filtering data failed! Invalid query!")
        sys.exit(1)

if command_format_string:
    placeholders = [placeholder for placeholder in re.findall("<(\w+)>", command_format_string)]
    for index, row in data_frame.iterrows():
        # Replace placeholders in command format string with values
        output_line = command_format_string
        for placeholder in placeholders:
            output_line = output_line.replace("<" + placeholder + ">", row[placeholder.lower()])
        print(output_line)
else:
    # Show data when --command-string or command-file is not set.
    print(data_frame.T)
    sys.exit(0)
