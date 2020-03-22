#!/usr/bin/env python3
import shlex
import traceback

import argcomplete, argparse
import csv
import re
from pathlib import Path
import logging
import os
import sys
import itertools

from IPython.terminal.embed import InteractiveShellEmbed
try:
    import pandas as pd
except:
    sys.stderr.write("Missing python3 package pandas! ")
    sys.stderr.write("Please install requirements using 'pip3 install -r requirements.txt" + os.linesep)
    sys.exit(1)

try:
    import IPython
except:
    sys.stderr.write("Missing python3 package IPython! ")
    sys.stderr.write("Please install requirements using 'pip3 install -r requirements.txt" + os.linesep)
    sys.exit(1)

app_name = "bob"
app_version = "1.0b"

# Configuration files
# ===================
# Configuration files can be placed into a folder named ".bob". Either inside the application- or
# inside the home-directory.
app_config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".bob")
home_config_path = os.path.join(str(Path.home()), ".bob")


def init_logger(app_id, log_format="%(module)s: %(lineno)d: %(msg)s"):
    logger = logging.getLogger(app_id)
    logging.root.setLevel(logging.DEBUG)
    hdlr = logging.StreamHandler(sys.stderr)
    hdlr.setFormatter(logging.Formatter(log_format))
    logger.addHandler(hdlr)
    return logger


class CommandFormatArgumentParser(object):

    def parse(self, command_argument):
        # Accepted data set format:
        #   PLACEHOLDER=VALUE
        #   PLACEHOLDER:FILE
        separator = self.__get_separator(command_argument)
        return {
            "=": self.__parse_value,
            ":": self.__parse_file
        }.get(separator)(command_argument, separator)

    def __get_separator(self, command_argument):
        string_sep_pos = command_argument.find("=")
        file_sep_pos = command_argument.find(":")
        if (string_sep_pos <= 0 and file_sep_pos <= 0) or (string_sep_pos > 0 and file_sep_pos > 0):
            raise Exception("Parsing '{}' failed! Invalid format!".format(command_argument))
        is_value_sep = string_sep_pos > 0
        sep = "=" if is_value_sep else ":"
        return sep

    def __parse_value(self, placeholder_value, sep):
        try:
            placeholder, value = placeholder_value.split(sep)
            return {placeholder.lower(): value}
        except:
            raise Exception("Parsing '{}' failed! Unknown error!".format(placeholder_value))

    def __parse_file(self, placeholder_file, sep):
        placeholder, file = placeholder_file.split(sep)
        if not os.path.isfile(file):
            raise Exception("Parsing '{}' failed! File not found!".format(placeholder_file))

        try:
            data = Data()
            with open(file) as f:
                for value in f.read().splitlines():
                    data.append(placeholder.lower(), value)
            return data
        except:
            raise Exception("Parsing '{}' failed! Invalid file format!".format(placeholder_file))


class Data(dict):
    """
     Map of placeholders with value lists e.g. { 'PLACEHOLDER-1': ('a','b','c'), 'PLACEHOLDER-2': ('d') }
    """

    def append(self, placeholder, values=None):
        def _add(placeholder, value):
            if placeholder in self.keys():
                self[placeholder].append(value)
            else:
                self[placeholder] = [value]

        if values is None:
            for placeholder, values in CommandFormatArgumentParser().parse(placeholder).items():
                _add(placeholder.lower(), values)
        elif isinstance(values, list):
            for value in values:
                _add(placeholder.lower(), value)
        else:
            _add(placeholder.lower(), values)

    def to_data_frame(self, filter_string=None):
        # Create table data with equally sized lists by filling them with empty strings
        # e.g. { 'placeholder-1': ('a','b','c'), 'placeholder-2': ('d','','') }
        table_data = Data()
        max_length = max([len(self[key]) for key in self.keys()])
        for placeholder in self.keys():
            for item in self[placeholder]:
                table_data.append(placeholder, item)
            for i in range(0, max_length - len(self[placeholder])):
                table_data.append(placeholder, "")

        data_frame = pd.DataFrame(table_data).astype(str)

        if filter_string:
            data_frame = data_frame.query(filter_string)

        return data_frame.T


    def import_from_file(self, import_file_path, delimiter):
        if not os.path.exists(import_file_path):
            raise Exception("Importing '{}' failed! File not found!".format(import_file_path))

        try:
            with open(import_file_path, 'r') as f:
                reader = csv.DictReader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)
                for line in reader:
                    for placeholder in line.keys():
                        self.append(placeholder.lower(), line[placeholder])
        except:
            raise Exception("Importing '{}' failed! Invalid file format!".format(import_file_path))


class Config(object):

    def __init__(self, paths):
        self.paths = paths
        self.command_template_paths = [os.path.join(path, "templates") for path in paths]
        self.profile = self.__load_profile()

    def __load_profile(self):
        for profile_path in self.paths:
            if os.path.exists(profile_path):
                try:
                    # Since the path may contain special characters which can not be processed by the __import__
                    # function we temporary add the template path in which the profile.py is located to the PATH.
                    sys.path.append(profile_path)
                    profile = __import__("bob_profile").Profile()
                    sys.path.pop()
                    return profile
                except:
                    pass
        return None

    def get_reserved_placeholders(self):
        if self.profile:
            return self.profile.placeholder_values
        return []

    def get_reserved_placeholder_values(self):
        reserved_placeholders = Data()
        if self.profile:
            for placeholder_value in self.profile.placeholder_values:
                placeholder_name = placeholder_value.name
                reserved_placeholders.append(placeholder_name.lower(), placeholder_value.element())

        return reserved_placeholders

    def get_command_template_names(self):
        command_format_files = []
        for command_format_file_path in self.command_template_paths:
            if os.path.exists(command_format_file_path):
                for r, d, f in os.walk(command_format_file_path):
                    relpath = r[len(command_format_file_path) + 1:]
                    for file in f:
                        command_format_files.append(os.path.join(relpath, file))
        return sorted(list(set(command_format_files)))

    def get_command_template(self, command_template_name):
        for command_template_path in self.command_template_paths:
            command_template_file = os.path.join(command_template_path, command_template_name)
            if os.path.exists(command_template_file):
                try:
                    with open(command_template_file) as f:
                        return os.sep.join(f.read().splitlines())
                except:
                    raise Exception("Loading '{}' failed! Invalid template format!".format(command_template_name))
        raise Exception("Loading '{}' failed! Template not found!".format(command_template_name))


class CommandsBuilder(object):

    def __init__(self, command_format_string, data, config):
        self.command_format_string = command_format_string
        self.data = data
        self.config = config

    def get_placeholders(self):
        if self.command_format_string:
            return list(set(placeholder for placeholder in re.findall("<(\w+)>", self.command_format_string)))
        else:
            return []

    def transform_data(self, filter_string=None):
        """
        Transforms the data from a map of placeholders with value lists into a data frame.
        """
        temporary_data = Data()

        placeholders = [placeholder.lower() for placeholder in self.get_placeholders()]
        for placeholder in self.data.keys():
            if placeholder in placeholders:
                # Add to temporary data while removing duplicate items
                temporary_data[placeholder] = set(self.data[placeholder])

        reserved_placeholder_values = self.config.get_reserved_placeholder_values()
        if any(reserved_placeholder in temporary_data.keys() for reserved_placeholder in reserved_placeholder_values.keys()):
            raise Exception("{} is/are already defined in your profile!".format(
                    ', '.join(["<" + placeholder + ">" for placeholder in reserved_placeholder_values.keys() if placeholder in temporary_data])))

        for placeholder, value in reserved_placeholder_values.items():
            if placeholder in placeholders:
                # Add to temporary data while removing duplicate items
                temporary_data[placeholder] = set(value)

        unset_placeholders = [placeholder for placeholder in placeholders if placeholder not in temporary_data]
        if unset_placeholders:
            raise Exception("Missing data for {}!".format(', '.join(["<" + item + ">" for item in unset_placeholders])))

        # Create matrix from data e.g. (('a','d'), ('b','d'), ('c','d'))
        data_matrix = list(itertools.product(*[temporary_data[key] for key in temporary_data.keys()]))

        # Create table data from matrix e.g. { 'placeholder-1': ('a','b','c'), 'placeholder-2': ('d','d','d') }
        data_keys = list(temporary_data.keys())
        table_data = Data()
        for i in range(0, len(data_matrix)):
            for j in range(0, len(data_keys)):
                table_data.append(data_keys[j], data_matrix[i][j])

        # Create data frame from table data
        # Handle everything as string which requires that the user needs to put quotes around every value in the filter.
        # This makes it easier to write such filter-queries in the long run since no one needs to think about whether
        # to put quotes around a value or not.
        data_frame = pd.DataFrame(table_data).astype(str)

        if filter_string:
            data_frame = data_frame.query(filter_string)

        return data_frame

    def build(self, filter_string=None):
        result = []
        if self.command_format_string:
            data_frame = self.transform_data(filter_string)
            if len(data_frame) == 0:
                return [self.command_format_string]

            placeholders = self.get_placeholders()
            for index, row in data_frame.iterrows():
                # Replace placeholders in command format string with values
                output_line = self.command_format_string
                for placeholder in placeholders:
                    output_line = output_line.replace("<" + placeholder + ">", row[placeholder.lower()])
                result.append(output_line)

        return result


class Bob(object):

    command_format_string = None
    filter_string = None
    data = Data()

    def __init__(self, config: Config):
        self.config = config

    def use_template(self, template_name):
        self.command_format_string = self.config.get_command_template(template_name)
        return self.command_format_string

    def list_templates(self, filter_string=None):
        template_names = self.config.get_command_template_names()
        if filter_string:
            return [template_name for template_name in template_names if filter_string in template_name]
        else:
            return template_names

    def list_options(self, filter_string=None):
        temporary_data = Data()
        for placeholder in self.data.keys():
            temporary_data[placeholder] = self.data[placeholder]
        reserved_placeholder_values = self.config.get_reserved_placeholder_values()
        for placeholder in reserved_placeholder_values.keys():
            temporary_data[placeholder] = reserved_placeholder_values[placeholder]
        return temporary_data.to_data_frame()

    def list_placeholders(self):
        return CommandsBuilder(self.command_format_string, self.data, self.config).get_placeholders()

    def import_data_file(self, import_file_path, delimiter=None):
        if not delimiter:
            delimiter = self.config.profile.csv_delimiter if self.config.profile else '\t'
        self.data.import_from_file(import_file_path, delimiter)

    def import_environment(self):
        placeholders = [placeholder.lower() for placeholder in self.list_placeholders()]
        reserved_placeholders = self.config.get_reserved_placeholder_values().keys()
        for placeholder in placeholders:
            if placeholder not in self.data and placeholder not in reserved_placeholders:
                data = os.environ.get(placeholder)
                if data:
                    if data.startswith('\(') and data.endswith('\)'):
                        for value in shlex.split(data[2:-2]):
                            self.data.append(placeholder, value)
                    else:
                        self.data.append(placeholder, data)

    def build(self):
        return CommandsBuilder(self.command_format_string, self.data, self.config).build(self.filter_string)


class InteractiveShell(object):

    class Function(object):

        def __init__(self, name=None, meta=None, callback=None):
            self.name = name
            self.meta = meta if meta else name
            self.callback = callback

    def __init__(self):
        self.ipython = InteractiveShellEmbed(banner1="""{app_name} {app_version}
Type '%help' for more information""".format(app_name=app_name, app_version=app_version), exit_msg="")

    def register_functions(self, name, functions):

        def _function(line):
                args = shlex.split(line)
                if isinstance(functions, InteractiveShell.Function):
                    try:
                        functions.callback(*args)
                    except Exception as err:
                        logger.error("ERROR: {}".format(err))
                    return
                elif isinstance(functions, list):
                    if args:
                        arg = args[0]
                        if arg in function_parameters_map:
                            try:
                                function_parameters_map[arg].callback(*args[1:])
                            except Exception as err:
                                logger.error("ERROR: {}".format(err))
                            return
                logger.error("Usage: %{} <{}>".format(name, " | ".join(function_parameters_map.keys())))
                return

        function_parameters_map = {fp.name: fp for fp in functions} if isinstance(functions, list) else {}
        if function_parameters_map:
            self.ipython.set_hook('complete_command', lambda x, y: function_parameters_map.keys(), re_key="%" + name)
        self.ipython.register_magic_function(_function, 'line', magic_name=name)

    def run(self):
        self.ipython()


config = Config([home_config_path, app_config_path])
bob = Bob(config)

def argparse_template_completer(prefix, parsed_args, **kwargs):
    return config.get_command_template_names()


logger = init_logger(app_name, "%(msg)s")

parser = argparse.ArgumentParser(
    description='Bob - the command builder',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Placeholder presets:

""" + os.linesep.join(["  {} {}".format(("<" + x.name + ">").ljust(20), x.description) for x in config.get_reserved_placeholders()]) + """

Examples:

  bob -s target=localhost     -c "nmap -sS -p- <target> -oA nmap-syn-all_<target>_<date_time>"
  bob -s target:./targets.txt -c "nmap -sS -p- <target> -oA nmap-syn-all_<target>_<date_time>"
    """
)
parser.add_argument('-c', '--command-format', action="store", metavar="COMMAND_FORMAT_STRING",
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
parser.add_argument('-e', '--environment', action="store_true",
                    dest='environment',
                    help="Uses the environment variables to replace the placeholders found in the command format. "
                         "Can be overridden by the --set and --import argument. Note that only lower-case variables "
                         "are considered that are matching the placeholders specified in the command format.")
parser.add_argument('-t', '--template', action="store", metavar="FILE",
                    dest='command_template_name',
                    help="The template to use as command format.")\
    .completer = argparse_template_completer
parser.add_argument('--view-template', action="store_true",
                    dest='view_template',
                    help="View the template instead of using it as generator. Can only be used in combination with "
                         "the --template argument.")
parser.add_argument('-l', '--list-templates', action="store_true",
                    dest='list_templates',
                    help="Lists all available templates.")
parser.add_argument('-f', '--filter', action="store", metavar="STRING", dest='filter',
                    help="The filter to include/exclude results (e.g. -f 'PLACEHOLDER==xx.* and PLACEHOLDER!=.*yy').")
parser.add_argument('--interactive', action="store_true",
                    dest='interactive',
                    help="Drops into an interactive python shell.")

argcomplete.autocomplete(parser)
arguments = parser.parse_args()

try:
    if arguments.list_templates:
        command_template_names = bob.list_templates()
        if not command_template_names:
            logger.warning("WARNING: No templates found!")
        for command_template_name in command_template_names:
            print(command_template_name)
        sys.exit(0)

    if arguments.command_format_string and arguments.command_template_name:
        raise Exception("--command-string can not be used in conjunction with --template!")

    if arguments.command_format_string:
        bob.command_format_string = arguments.command_format_string

    if arguments.view_template and not arguments.command_template_name:
        raise Exception("--view-template must be used in combination with --template!")

    if arguments.command_template_name:
        command_format_string = bob.use_template(arguments.command_template_name)
        if arguments.view_template:
            print(command_format_string)
            sys.exit(0)

    if not bob.command_format_string and arguments.environment:
        bob.command_format_string = os.environ.get("COMMAND_FORMAT")

    if arguments.import_file:
        bob.import_data_file(arguments.import_file)

    # Load data given via --set argument
    if arguments.data_set:
        for _data in arguments.data_set:
            bob.data.append(_data)

    if arguments.environment and bob.command_format_string:
        bob.import_environment()

    bob.filter_string = arguments.filter

    if arguments.interactive:
        shell = InteractiveShell()

        def print_lines(lines):
            for line in lines:
                print(line)

        def _show_help(*args, **kwargs):
            print("%use command_format <string>")
            print("    set the command format e.g. %use command_format 'test <date_time>'.")
            print("%use template <string>")
            print("    set the command format via a template name e.g. %use template test.")
            print("%show command_format")
            print("    shows the current command format.")
            print("%show options")
            print("    shows the current list of potential placeholders and values.")
            print("%show templates [filter_string]")
            print("    shows the available list of templates. The list can be filtered by specifying a filter string.")
            print("%set <placeholder=value|placeholder:file>")
            print("    sets a potential placeholder and the associated values.")
            print("%unset <placeholder>")
            print("    unsets a potential placeholder.")
            print("%import <file> [delimiter]")
            print("    imports data from a given csv-file. The default delimiter is \\t.")
            print("%build")
            print("    builds the commands.")
            print("%help")
            print("    show this help.")

        # Register magic functions and autocomplete
        shell.register_functions("use", [
            InteractiveShell.Function(
                name="command_format", callback=lambda *args, **kwargs: setattr(bob, "command_format_string", *args)),
            InteractiveShell.Function(
                name="template", callback=lambda *args, **kwargs: bob.use_template(*args))
        ])
        shell.register_functions("show", [
            InteractiveShell.Function(
                name="command_format", callback=lambda *args, **kwargs: print(bob.command_format_string)),
            InteractiveShell.Function(
                name="options", callback=lambda *args, **kwargs: print(bob.list_options(*args))),
            InteractiveShell.Function(
                name="templates", callback=lambda *args, **kwargs: print_lines(bob.list_templates(*args)))
        ])
        shell.register_functions("set", InteractiveShell.Function(
            meta="placeholder=value | placeholder:file", callback=lambda *args, **kwargs: bob.data.append(*args)
        ))
        shell.register_functions("unset", InteractiveShell.Function(
            meta="placeholder", callback=lambda args, *kwargs: bob.data.pop(*args)
        ))
        shell.register_functions("import", InteractiveShell.Function(
            meta="file", callback=lambda *args, **kwargs: bob.import_data_file(*args)
        ))
        shell.register_functions("build", InteractiveShell.Function(
            callback=lambda *args, **kwargs: print_lines(bob.build()))
        )
        shell.register_functions("help", InteractiveShell.Function(callback=_show_help))

        shell.run()
        sys.exit(0)

    if bob.command_format_string:
        for line in bob.build():
            print(line)
    else:
        print(bob.list_options())
except Exception as e:
    logger.error("ERROR: {}".format(e))
    traceback.print_exc() # Uncomment this line for printing traceback
    sys.exit(1)
