#!/usr/bin/python3
import argparse
import csv
import re
from pathlib import Path
import logging
import os
import sys
import itertools

import pandas as pd

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


def add_placeholder_value(data_frame, placeholder, value):
    if placeholder in data_frame:
        data_frame[placeholder].append(value)
    else:
        data_frame[placeholder] = [value]


def transform_data(command_format_string, placeholders, data_keys, filter_query):
    # Remove unused data
    if command_format_string:
        for data_key in data_keys:
            if data_key not in placeholders:
                data.pop(data_key, None)
    # Create matrix from data e.g. (('a','d'), ('b','d'), ('c','d'))
    data_matrix = list(itertools.product(*[data[key] for key in data.keys()]))
    #
    # Create table data from matrix e.g. { 'placeholder-1': ('a','b','c'), 'placeholder-2': ('d','d','d') }
    data_keys = list(data.keys())
    table_data = {}
    for i in range(0, len(data_matrix)):
        for j in range(0, len(data_keys)):
            add_placeholder_value(table_data, data_keys[j], data_matrix[i][j])
    #
    # Create data frame from table data
    data_frame = pd.DataFrame(table_data)
    # Handle everything as string which requires that the user needs to put quotes around every value in the filter.
    # This makes it easier to write such filter-queries in the long run since no one needs to think about whether
    # to put quotes around a value or not.
    data_frame = data_frame.astype(str)
    #
    # Filter data using query string defined by user
    if arguments.filter:
        try:
            data_frame = data_frame.query(filter_query)
        except:
            # Error - invalid filter format
            # Error - placeholder used in filter not defined
            logger.error("ERROR: Invalid filter!")
            sys.exit(1)
    return data_frame

# Always look into the current working directory first when importing modules
sys.path.insert(0, '')

logger = init_logger(app_name, "%(msg)s")

parser = argparse.ArgumentParser(
    description='Bob - the command builder',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Format patterns:

{DATE}      current date YYYYMMDD
{DATETIME}  current date and time YYYYYMMDDhhmm

Examples:

bob -s TARGET=localhost -c "nmap -sP {TARGET} -oA nmap_sp_{TARGET}_{DATETIME}"
bob -s TARGET:./targets.txt -c "wfuzz --wordlist=/usr/share/wordlists/... {TARGET} > wfuzz_{TARGET}_{DATETIME}"
bob -s LHOST=192.168.0.1 -s LPORT=4444 -t shell/perl

    """
)
parser.add_argument('-s', '--set', action="append", metavar="PLACEHOLDER=VALUE | -s PLACEHOLDER:FILE", dest='data_set',
                    help="The value(s) used to replace the placeholder found in the command format.")
parser.add_argument('-i', '--import', action="store", metavar="FILE", dest='import_file',
                    help="The value(s) used to replace the placeholder found in the command format.")
parser.add_argument('-c', '--command-string', action="store", metavar="COMMAND_FORMAT_STRING",
                    dest='command_format_string',
                    help="The command format in which output should be printed."
                         "(e.g. 'nmap -sV {TARGET} -p {PORTS}').")
parser.add_argument('-t', '--command-file', action="store", metavar="FILE",
                    dest='command_format_file',
                    help="The template file to use which contains the command format in which output should be printed.")
parser.add_argument('-l', '--command-template-list', action="store_true", dest='command_template_list',
                    help="Prints the names of all present command templates.")
parser.add_argument('-f', '--filter', action="store", metavar="STRING", dest='filter',
                    help="A filter to include/exclude results (e.g. -f 'PLACEHOLDER==xx.* and PLACEHOLDER!=.*yy').")
parser.add_argument('-p', '--profile', action="store", metavar="PROFILE", dest='profile',
                    help="The profile to load (default: ~/.bob/profile).")
arguments = parser.parse_args()

command_format_string = arguments.command_format_string
command_format_file = arguments.command_format_file
if command_format_string and command_format_file:
    logger.error("ERROR: --command-string can not be used in conjunction with command-file!")
    sys.exit(1)

if command_format_file:
    if os.path.exists(os.path.join(app_config_command_format_file_path, command_format_file)):
        command_format_string = os.path.join(app_config_command_format_file_path, command_format_file)
    elif not os.path.exists(os.path.join(home_config_command_format_file_path, command_format_file)):
        command_format_string = os.path.join(home_config_command_format_file_path, command_format_file)
    else:
        logger.error("ERROR: Loading command file failed! The file {} was not found!".format(command_format_file))
        sys.exit(1)

import_file = arguments.import_file
if import_file and not os.path.exists(import_file):
    logger.error("ERROR: Loading import file failed! The file {} was not found!".format(import_file))
    sys.exit(1)

profile_path = ""
if os.path.isfile(app_config_profile):
    profile_path = app_config_path
elif os.path.isfile(home_config_profile):
    profile_path = home_config_path
else:
    logger.warning("WARNING: Loading profile failed! File not found!")

# Map of placeholders with value lists e.g. { 'PLACEHOLDER-1': ('a','b','c'), 'PLACEHOLDER-2': ('d') }
data = {}
# Load data given via --set argument
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
    try:
        if is_value_sep:
            placeholder, value = placeholder_value.split(sep)
            add_placeholder_value(data, placeholder.lower(), value)
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
    except:
        logger.error("ERROR: Loading placeholder value '{}' failed!".format(placeholder_value))
        sys.exit(1)

# Load data from file given via --import argument
if import_file:
    try:
        with open(import_file, 'r' ) as f:
            reader = csv.DictReader(f)
            for line in reader:
                for placeholder in line.keys():
                    add_placeholder_value(data, placeholder.lower(), line[placeholder])
    except:
        logger.error("ERROR: Loading import file failed! The file {} has an invalid format!".format(import_file))
        sys.exit(1)

# Load command format string from file given via --command-format-file
if command_format_file:
    try:
        with open(command_format_file) as f:
            command_format_string = f.readline()
    except:
        logger.error("ERROR: Loading command file failed! The file {} could not be processed!".format(command_format_file))
        sys.exit(1)

if profile_path:
    try:
        # Import profile.py
        #
        # Since the path may contain special characters which can not be processed by the __import__ function
        # we change the working directory to the path in which the profile.py is located.
        current_working_directory = os.getcwd()
        os.chdir(profile_path)
        profile = __import__("profile").Profile()
        os.chdir(current_working_directory)

        # Add all variables (aka placeholders) and values found in profile.py to the data map
        for placeholder in [item for item in dir(profile) if not item.startswith("__")]:
            if placeholder[0].isupper():
                # ignore classes
                continue
            if placeholder.lower() in data:
                logger.error("ERROR: The specified placeholder '{}' is already defined in your profile!")
                sys.exit(1)
            element = getattr(profile, placeholder).getElement()
            if isinstance(element, list):
                for value in element:
                    add_placeholder_value(data, placeholder.lower(), value.getValue())
            else:
                add_placeholder_value(data, placeholder.lower(), element)
    except Exception as e:
        logger.error("ERROR: Loading profile failed! The file has an invalid format!")
        sys.exit(1)

# Retrieve data keys
data_keys = {data_key.lower() for data_key in data.keys()}

placeholders = []
if command_format_string:
    # Parse placeholders from command format string
    placeholders = set(placeholder for placeholder in re.findall("<(\w+)>", command_format_string))
    for placeholder in placeholders:
        if placeholder.lower() not in data_keys:
            logger.error("ERROR: Generating command(s) failed! The placeholder <{}> has no associated data!".format(placeholder))
            sys.exit(1)

data_frame = transform_data(command_format_string, placeholders, data_keys, arguments.filter)
if arguments.command_format_string or arguments.command_format_file:
    placeholders = [placeholder for placeholder in re.findall("<(\w+)>", command_format_string)]
    for index, row in data_frame.iterrows():
        # Replace placeholders in command format string with values
        output_line = command_format_string
        for placeholder in placeholders:
            output_line = output_line.replace("<" + placeholder + ">", row[placeholder.lower()])
        print(output_line)
else:
    # Show data when --command-string or command-file is not set.
    print(data_frame)
    sys.exit(0)
