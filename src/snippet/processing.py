import copy
import itertools
import os
import re
from collections import OrderedDict

from snippet.codecs import CodecRunner
from snippet.formatters import PlaceholderValuePrintFormatter
from snippet.models import Data
from snippet.parsers import FormatStringParser, PlaceholderFormatParser
from snippet.utils import replace_within


class DataBuilder(object):

    def __init__(self, format_string, data, codec_formats, config):
        self.data = data
        self.config = config
        self.codec_formats = codec_formats
        self._codec_runner = CodecRunner(config.codecs)
        self._format_string = format_string
        self._format_string_minified = self._minify_format_string(format_string)
        self._placeholders = PlaceholderFormatParser().parse(self._remove_comments(self._format_string_minified))

    def _remove_comments(self, string):
        return os.linesep.join([line for line in string.splitlines() if not line.startswith("#")])

    def _minify_format_string(self, format_string):
        """
        Initializes the format string.

        This function removes optional parts of the supplied format string which were not set by the user or the
        snippet system (e.g. reserved placeholders).
        """
        # Collect defaults and set them if no value was assigned.
        for placeholder in PlaceholderFormatParser().parse(self._remove_comments(format_string)):
            if placeholder.default is not None and placeholder.name not in self.data.keys():
                self.data.append(placeholder.name, placeholder.default)

        # Check whether parameters are empty.
        parameters = {}

        # Collect parameters specified by the user.
        for parameter in self.data.keys():
            # $ snippet -f "[<arg>]" arg=
            parameters[parameter] = self.data[parameter] != [""]

        # Collect reserved placeholders (e.g. <datetime>).
        for parameter in self.config.get_reserved_placeholder_names():
            parameters[parameter] = True  # is never empty

        return FormatStringParser(self.config).parse(format_string, parameters)

    def transform_data(self) -> Data:
        """
        Transforms the data from a map of placeholders with value lists into a data frame.
        """
        temporary_data = Data()

        # Add all data which has an associated placeholder to a temporary dict.
        placeholder_names = self._get_placeholder_names()
        for placeholder_name in self.data.keys():
            if placeholder_name in placeholder_names:
                temporary_data[placeholder_name] = self.data[placeholder_name]

        # Do not allow using reserved placeholders.
        reserved_placeholder_values = self.config.get_reserved_placeholder_values()
        if any(reserved_placeholder in temporary_data.keys() for reserved_placeholder in
               reserved_placeholder_values.keys()):
            raise Exception("{} is/are already defined in your profile!".format(
                ', '.join(["<" + placeholder_name + ">" for placeholder_name in reserved_placeholder_values.keys() if
                           placeholder_name in temporary_data])))

        # Add all reserved placeholders which have an associated placeholder to the temporary dict.
        for placeholder_name, value in reserved_placeholder_values.items():
            if placeholder_name in placeholder_names:
                # Add to temporary data. Remove duplicates while preserving order
                temporary_data[placeholder_name] = OrderedDict.fromkeys(value)

        # Move placeholders which are tagged as repeatable (e.g. <ARG...>) to temporary map before creating matrix.
        repeatable_placeholders = {}
        placeholder_names = list(temporary_data.keys())
        for placeholder_name in placeholder_names:
            # Get all placeholders specified in the format string which have the same name.
            _p = [p for p in self.get_placeholders() if p.name == placeholder_name]
            # Get all placeholders specified in the format string which are repeatable and have the same name.
            _r = [p for p in _p if p.repeatable]
            is_repeatable = len(_r) > 0
            if is_repeatable:
                if len(_p) == len(_r):
                    # All placeholders in the format string are repeatable placeholders e.g. "<ARG...> <ARG...>"
                    repeatable_placeholders[placeholder_name] = temporary_data.pop(placeholder_name, None)
                else:
                    # Not repeatable and repeatable placeholders are defined in format string e.g. "<ARG...> <ARG>"
                    repeatable_placeholders[placeholder_name] = copy.deepcopy(temporary_data[placeholder_name])

        # Create matrix from data e.g. (('a','d'), ('b','d'), ('c','d'))
        # This list does only contain placeholders which are not tagged as repeatable (e.g. <ARG...>).
        data_matrix = list(itertools.product(*[temporary_data[key] for key in temporary_data.keys()]))

        # Create table data from matrix e.g. { 'placeholder-1': ('a','b','c'), 'placeholder-2': ('d','d','d') }
        # Add placeholders which are tagged as repeatable (e.g. <ARG...>) to the table data again.
        data_keys = list(temporary_data.keys())
        table_data = Data()
        for i in range(0, len(data_matrix)):
            for j in range(0, len(data_keys)):
                table_data.append(data_keys[j], data_matrix[i][j])
            for placeholder_name in repeatable_placeholders:
                # Store repeatable placeholder in table_data as list.
                # Use different key to avoid overwriting placeholders which is not repeatable.
                table_data.append(placeholder_name + "...",
                                  [[item for item in repeatable_placeholders[placeholder_name]]])

        return table_data

    def get_placeholders(self):
        return list(self._placeholders)

    def _get_placeholder_names(self):
        """ Returns a unique list of placeholder names. """
        return set([placeholder.name for placeholder in self.get_placeholders()])

    def _escape_brackets(self, str):
        if str:
            return str.replace("[", "\\[").replace("]", "\\]").replace("<", "\\<").replace(">", "\\>")
        else:
            return str

    def _unescape_brackets(self, str):
        if str:
            return str.replace("\\[", "[").replace("\\]", "]").replace("\\<", "<").replace("\\>", ">")
        else:
            return str

    def _replace_placeholders_in_line(self, line, placeholders, data_frame, line_start, line_end, iteration):
        for placeholder in reversed(placeholders):
            if line_start <= placeholder.start < line_end:
                adjusted_start = placeholder.start - line_start
                adjusted_end = placeholder.end - line_start
                row = data_frame[placeholder.name + "..." if placeholder.repeatable else placeholder.name]
                value = self._codec_runner.run(row[iteration], placeholder)
                line = replace_within(line, self._escape_brackets(value), adjusted_start, adjusted_end)

        return line

    def _process_format_string(self, format_string, data_frame, placeholders):
        result = []
        # Determine the number of outputs to be generated
        num_iterations = len(next(iter(data_frame.values()), []))

        if not num_iterations:
            self.config.logger.debug('No placeholders defined or already set through optionals...')
            # Handling scenarios with no dynamic placeholders or placeholders already set:
            # Example 1: snippet -f "abc def" -> Output: "abc def"
            # Example 2: snippet -f "a[b<arg1='test'>b]a" arg1= -> Output: "aa"
            # Example 3: snippet -f "abc [<arg1> <arg2>]" arg1=test -> Output: "abc "
            return [format_string]

        # Processing format_string multiple times for each set of values in data_frame:
        # Example 1: snippet -f "<arg>" arg=1 -> Output: "1"
        # Example 2: snippet -f "<arg>" arg=1 arg=2 -> Outputs: "1", "2"
        for iteration in range(num_iterations):
            line_start = 0
            processed_lines = []

            # Iterate over each line in format_string for processing
            for line in format_string.splitlines(keepends=True):
                if not line.startswith("#"):
                    # Replace placeholders in non-comment lines
                    line_end = line_start + len(line)
                    line = self._replace_placeholders_in_line(line, placeholders, data_frame, line_start, line_end, iteration)
                    line_start = line_end

                processed_lines.append(line)

            result.append(''.join(processed_lines))

        return result

    def _validate_codecs(self, placeholders):
        for placeholder in placeholders:
            for codec in placeholder.codecs:
                if codec.name not in self.config.codecs:
                    raise Exception(f"Parsing '{self._format_string}' failed! Codec '{codec.name}' does not exist!")

    def _assign_defaults(self, placeholders):
        for placeholder in placeholders:
            if placeholder.name not in self.data.keys() and placeholder.default:
                self.data.append(placeholder.name, placeholder.default)

    def _log_placeholder_values(self, data_frame):
        for output in PlaceholderValuePrintFormatter.build(self._remove_comments(self._format_string), data_frame):
            self.config.logger.info(output)

    def _validate_required_placeholders(self, placeholders, data_frame):
        # Get all required placeholders which are not assigned. Also consider repeatables (see transform_data).
        unset_placeholders = OrderedDict.fromkeys([
            placeholder.name for placeholder in placeholders
            if placeholder.name not in data_frame.keys() and
               placeholder.required and
               placeholder.name + "..." not in data_frame.keys()])

        if unset_placeholders:
            missing_placeholders = ', '.join(f"<{name}>" for name in unset_placeholders)
            raise Exception(f"Missing data for {missing_placeholders}!")

    def _check_for_unmatched_placeholders(self, processed_output):
        # Check for unmatched placeholders in each output, ignoring comments and escaped angle brackets.
        for output in processed_output:
            output_string = ''.join(line for line in output.splitlines() if not line.startswith('#'))
            placeholders = re.findall(r"([\\]?<.*?>)", output_string)
            unescaped_placeholders = [item for item in placeholders if
                                      not (item.startswith('\\<') and item.endswith('\\>'))]

            if unescaped_placeholders:
                raise Exception(f"Invalid placeholder format: {unescaped_placeholders[0]}")

    def build(self):
        if not self._format_string_minified:
            return []

        placeholders = self.get_placeholders()
        self._assign_defaults(placeholders)
        self._validate_codecs(placeholders)

        data_frame = self.transform_data()
        self._log_placeholder_values(data_frame)
        self._validate_required_placeholders(placeholders, data_frame)
        processed_output = self._process_format_string(self._format_string_minified, data_frame, placeholders)
        self._check_for_unmatched_placeholders(processed_output)

        return [self._unescape_brackets(line) for line in processed_output]
