#!/usr/bin/env python3
import codecs as _codecs
import json
from inspect import signature

import argcomplete, argparse

from collections import defaultdict, OrderedDict, namedtuple

import os
import sys
from pathlib import Path
import logging
import shutil
import subprocess
import traceback

from snippet.config import Config
from snippet.models import Data
from snippet.parsers import PlaceholderFormatParser, ArgumentFormatParser
from snippet.processing import DataBuilder
from snippet.utils import safe_join_path, log_format_template, log_format_string, print_line

app_name = "snippet"

# Configuration files
# ===================
# Configuration files can be placed into a folder named ".snippet". Either inside the application- or
# inside the home-directory.
app_config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".snippet")
home_config_path = os.path.join(str(Path.home()), ".snippet")


class Snippet(object):

    def __init__(self, config: Config):
        self._format_string = ""
        self.config, self.logger = config, config.logger
        self.codec_formats = {}
        self.data = Data()

    def _get_format_string(self):
        return self._format_string

    def _set_format_string(self, format_string):
        if format_string:
            if isinstance(format_string, list):
                self._format_string = os.linesep.join(format_string)
            else:
                self._format_string = format_string

    def _set_arguments(self, data_values):
        placeholder = None
        unset_placeholders = self.list_unset_placeholders()
        last_assigned_placeholder = None
        for data_value in data_values:
            if data_value:  # Ignore empty string arguments (e.g. ""); use "arg=" instead
                for assigned_placeholder, assigned_values in ArgumentFormatParser().parse(data_value).items():
                    if assigned_placeholder:
                        # $ snippet -f "<arg>" arg=val
                        placeholder = assigned_placeholder
                        last_assigned_placeholder = assigned_placeholder
                    else:
                        # $ snippet -f "<arg>" val
                        if last_assigned_placeholder:
                            # Use the last assigned placeholder if any.
                            # $ snippet -f "<arg>" arg=val1 val2
                            placeholder = last_assigned_placeholder
                        else:
                            # Use the next not-assigned placeholder in the format string.
                            # $ snippet -f "<arg>" val1 val2
                            if len(unset_placeholders) == 0:
                                if not placeholder:
                                    # No placeholders left to assign values to.
                                    # $ snippet -f "text" val1
                                    self.logger.warning(
                                        "Can not assign '{}' to unknown placeholder!".format(assigned_values))
                                    continue
                                else:
                                    # Use the last placeholder if any.
                                    # $ snippet -f "<arg1> <arg2>" val1 val2 val3
                                    pass
                            else:
                                placeholder = unset_placeholders.pop(0)
                    self.data.append(placeholder, assigned_values)

    def _get_arguments(self):
        return self.data

    def create_or_edit_template(self, template_name, format_string):
        home_template_path = safe_join_path(home_config_path, "templates")
        home_template_file = safe_join_path(home_template_path, template_name)

        if os.path.isfile(home_template_file):
            # Edit existing file in home path
            subprocess.call((self.config.editor, home_template_file))
            return

        try:
            app_template_path = safe_join_path(app_config_path, "templates")
            app_template_file = safe_join_path(app_template_path, template_name)
            home_template_dir = os.path.dirname(home_template_file)
            os.makedirs(home_template_dir, exist_ok=True)
            if os.path.isfile(app_template_file):
                # App files should not be altered.
                # If template exists in app path, do not edit here.
                # Instead, make copy to home path and edit this file.
                # Templates in home path override templates in app path.
                shutil.copyfile(app_template_file, home_template_file)

            if format_string:
                with open(home_template_file, 'w') as f:
                    f.write(format_string)

            subprocess.call((self.config.editor, home_template_file))
            self.logger.info("Successfully created template '{}'!".format(template_name))
        except:
            raise Exception("Creating template '{}' failed!".format(template_name))

    def get_template(self, template_name):
        return self.config.get_format_template(template_name)

    def list_templates(self, filter_string=None):
        template_names = self.config.get_format_template_names()
        if filter_string:
            return [template_name for template_name in template_names if filter_string in template_name]
        else:
            return template_names

    def list_codecs(self, filter_string=None):
        if filter_string:
            return sorted([codec_name for codec_name in self.config.codecs.keys() if
                           filter_string in self.config.codecs.keys()])
        else:
            return sorted(self.config.codecs.keys())

    def list_environment(self):
        result = []
        temporary_data = Data()
        for placeholder in self.data.keys():
            temporary_data[placeholder] = self.data[placeholder]
        reserved_placeholder_values = self.config.get_reserved_placeholder_values()
        for placeholder in reserved_placeholder_values.keys():
            temporary_data[placeholder] = reserved_placeholder_values[placeholder]
        for placeholder, values in temporary_data.items():
            if len(values) == 1:
                result.append("export {}=\"{}\"".format(placeholder, values[0]))
            else:
                result.append("export {}=\"\\('{}'\\)\"".format(placeholder, "' '".join(values)))
        return result

    def list_placeholders(self):
        """ Returns all the placeholders found in the format string. """
        return [placeholder.name for placeholder in PlaceholderFormatParser().parse(self._format_string)]

    def list_reserved_placeholders(self):
        """ Returns the list of reserved placeholders (aka Presets) e.g. 'datetime', 'date', ... """
        return self.config.get_reserved_placeholder_names()

    def list_unset_placeholders(self):
        """ Returns the placeholders in the format string which are not associated with any value yet. """
        unset_placeholders = []
        for placeholder in self.list_placeholders():
            if placeholder not in self.data and \
                    placeholder not in self.list_reserved_placeholders():
                unset_placeholders.append(placeholder)
        return unset_placeholders

    def import_environment(self):
        """
        Import values found in environment variables which name match the placeholder names found in the format string.
        Note, that an environment variable matching a placeholder is only loaded when no value is assigned yet.
        """

        reserved_placeholders = self.config.get_reserved_placeholder_values().keys()

        def _import_environment(placeholder, data):
            if data and placeholder not in reserved_placeholders:
                self.data.append(placeholder, data)

        for placeholder, data in os.environ.items():
            if not placeholder.islower() or placeholder.startswith("_"):
                # Do not load upper case environment variables to prevent users from getting into the habit of
                # defining upper case environment variables and messing up their environment.
                # In addition, loading upper case environment variables may result in loading unwanted/pre-defined
                # values.
                # Do not load placeholders which start with underscore as these are usually private variables used
                # by other applications.
                continue

            # Only set environment data when not already defined
            if placeholder not in self.data:
                _import_environment(placeholder, data)

    def build(self):
        return DataBuilder(self._get_format_string(), self.data, self.codec_formats, self.config).build()

    format_string = property(_get_format_string, _set_format_string)
    arguments = property(_get_arguments, _set_arguments)


def main():
    log_level = logging.DEBUG if "--debug" in sys.argv or "-d" in sys.argv else logging.WARN
    config = Config(app_name, [home_config_path, app_config_path], log_level)
    logger = config.logger
    snippet = Snippet(config)

    def argparse_template_completer(prefix, parsed_args, **kwargs):
        return config.get_format_template_names()

    parser = argparse.ArgumentParser(
        description='snippet',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Placeholder presets:

""" + os.linesep.join(["  {}  {}".format(("<" + x.name + ">").rjust(20, ' '), x.description) for x in
                       config.get_reserved_placeholders()]) + """

    Codecs:

""" + os.linesep.join(["  {}  {}".format(x.rjust(20, ' '), config.codecs[x].__doc__.strip()) for x in
                       config.codecs.keys()]) + """

    Examples:

        # Add a new snippet to the database
        $ snippet -e archive/extract-tgz -f 'tar -xzvf <archive>'

        # Edit a snippet (will open vim)
        $ snippet -e archive/extract-tgz

        # Search a snippet which include the term "extract" (will open fzf)
        $ snippet -t extract

        # Fill snippet with a value
        $ snippet -t archive/extract-tgz /path/to/foo.tar.gz

        # Fill snippet with multiple values
        $ snippet -t archive/extract-tgz /path/to/foo.tar.gz /path/to/bar.tar.gz

        # Fill snippet with multiple values while using repeatable placeholders (e.g. <file...>)
        $ snippet -f "tar -czvf <archive> <file...>" /path/to/foo.tar file=foo bar

        # Using presets (e.g. '<datetime>' to include current datetime)
        $ snippet -f "tar -czvf '<datetime>.tar.gz' <file...>" file=foo bar

        # Import values from file
        $ snippet -f "tar -czvf '<datetime>.tar.gz' <file...>" file:files.txt

        # Using optionals
        $ snippet -f "python3 -m http.server[ --bind <lhost>][ <lport>]" lport=4444

        # Using defaults
        $ snippet -f "python3 -m http.server[ --bind <lhost>] <lport='8000'>"

        # Overwriting defaults
        $ snippet -f "python3 -m http.server[ --bind <lhost>] <lport='8000'>" lport=9090

        # Using codecs
        $ snippet -f "tar -czvf <archive|squote> <file...|squote>" /path/to/foo.tar file=foo bar

        # Using multiple codecs with arguments
        $ snippet -f "cp <file|squote> <file|add:'.bak'|squote>" /path/to/foo /path/to/bar
        """
    )
    parser.add_argument('data_values', metavar='VALUE | PLACEHOLDER=VALUE | PLACEHOLDER:FILE', nargs='*',
                        help='When no placeholder is specified the first unset placeholder found in the format string will '
                             'be replaced with the value(s). Otherwise the specified placeholder will be replaced with '
                             'the value or the content of the file. A list of values can be assigned by explicitly '
                             'declaring the placeholder (e.g. "ARG1=val1" "ARG2=val2").')
    parser.add_argument('-e', '--edit', action="store", metavar="NAME",
                        dest='edit',
                        help="Edit (or create) a snippet with the specified name.") \
        .completer = argparse_template_completer
    parser.add_argument('-f', '--format-string', action="store", metavar="FORMAT_STRING",
                        dest='format_string',
                        help="The format of the data to generate. "
                             "The placeholders are identified by angle brackets (<, >). "
                             "Optional parts can be denoted using square brackets ([, ]).")
    parser.add_argument('-t', '--template', action="store", metavar="FILE",
                        dest='template_name',
                        help="The template to use as format string.") \
        .completer = argparse_template_completer
    parser.add_argument('--list-templates', action="store_true",
                        dest='list_templates',
                        help="Lists all available templates.")
    parser.add_argument('--list-codecs', action="store_true",
                        dest='list_codecs',
                        help="Lists all available codecs.")
    parser.add_argument('--env', '--environment', action="store_true",
                        dest='environment',
                        help="Shows all environment variables.")
    parser.add_argument('-q', '--quiet', action="store_false",
                        dest='verbose',
                        help="Do not print additional information (e.g. format string, template, ...).")
    parser.add_argument('-d', '--debug', action="store_true",
                        dest='debug',
                        help="Prints additional debug information (e.g. stack traces).")

    argcomplete.autocomplete(parser)
    arguments = parser.parse_args()

    if arguments.debug:
        config.logger.level = logging.DEBUG
    elif arguments.verbose:
        config.logger.level = logging.INFO
    else:
        config.logger.level = logging.WARN

    try:
        if arguments.edit:
            snippet.create_or_edit_template(arguments.edit, arguments.format_string)
            sys.exit(0)

        if arguments.list_codecs and arguments.list_templates:
            raise Exception("--codec-list can not be used in combination with --template-list!")

        if arguments.list_templates:
            template_names = snippet.list_templates()
            if not template_names:
                logger.warning("No templates found!")
            for template_name in template_names:
                print(template_name)
            sys.exit(0)

        if arguments.list_codecs:
            codec_names = snippet.list_codecs()
            if not codec_names:
                logger.warning("No codecs found!")
            for codec_name in codec_names:
                print(codec_name)
            sys.exit(0)

        if arguments.format_string and arguments.template_name:
            raise Exception("--format-string can not be used in conjunction with --template!")

        if arguments.format_string and not sys.stdin.isatty():
            raise Exception("--format-string can not be used in conjunction with piped input!")

        if arguments.template_name and not sys.stdin.isatty():
            raise Exception("--template can not be used in conjunction with piped input!")

        format_string = arguments.format_string
        if arguments.template_name:
            format_template_name, format_string = snippet.get_template(arguments.template_name)
            log_format_template(format_template_name, logger)

        if not sys.stdin.isatty():
            format_string = "".join(sys.stdin.readlines())

        if not format_string:
            format_string = os.environ.get("FORMAT_STRING")

        # Make sure that escape sequences like \n, \t, etc. are handled correctly.
        snippet.format_string = _codecs.decode(format_string or '', 'unicode_escape')
        if snippet.format_string:

            if arguments.data_values:
                snippet.arguments = arguments.data_values

            snippet.import_environment()

            if arguments.environment:
                for line in snippet.list_environment():
                    print(line)
                sys.exit(0)

        if not snippet.format_string:
            parser.print_usage(file=sys.stderr)
            sys.exit(1)

        log_format_string(format_string, logger)
        for lines in snippet.build():
            # Handle format strings with line separators
            for line in lines.splitlines():
                print_line(line)
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        logger.error(str(e))
        if arguments.debug:
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
