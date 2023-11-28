from collections import OrderedDict

from colorama import Fore

from snippet.parsers import PlaceholderFormatParser
from snippet.utils import colorize


class EscapedBracketCodec:

    @staticmethod
    def encode(str, opener, closer):
        return str.replace('\\' + opener, chr(14)).replace('\\' + closer, chr(15))

    @staticmethod
    def decode(str, opener, closer):
        return str.replace(chr(14), '\\' + opener).replace(chr(15), '\\' + closer)


class PlaceholderValuePrintFormatter:

    @staticmethod
    def build(format_string, data_frame):

        def _unique_placeholders(placeholders):
            """ Returns a list of unique placeholders while preserving the required and default attribute. """
            result = {}
            for placeholder in placeholders:
                if placeholder.name not in result:
                    result[placeholder.name] = placeholder
                result[placeholder.name].required = result[placeholder.name].required or placeholder.required
                result[placeholder.name].default = result[placeholder.name].default or placeholder.default
            return result.values()

        lines = []
        placeholders = PlaceholderFormatParser().parse(format_string)
        if not placeholders:
            # No placeholders in format string.
            return lines

        placeholder_names = OrderedDict.fromkeys([placeholder.name for placeholder in placeholders])
        placeholder_name_max_len = len(max(placeholder_names, key=len))
        unique_placeholders = _unique_placeholders(placeholders)

        # Print assigned values for each placeholder.
        lines.append(colorize("Placeholders:", Fore.YELLOW))
        for placeholder in unique_placeholders:
            # Retrieve values.
            if placeholder.name in data_frame:
                values = list(OrderedDict.fromkeys(data_frame[placeholder.name]))
            elif placeholder.name + "..." in data_frame:
                values = list(OrderedDict.fromkeys(data_frame[placeholder.name + "..."][0]))
            else:
                values = None

            is_default = placeholder.default and values == list(placeholder.default)
            is_set = values is not None
            if not is_set or is_default:
                if placeholder.default:
                    status = colorize(" (default)", Fore.BLUE)
                    value = colorize(placeholder.default, Fore.LIGHTBLUE_EX)
                elif placeholder.required:
                    status = colorize("(required)", Fore.RED)
                    value = colorize("<not assigned>", Fore.LIGHTRED_EX)
                else:
                    status = colorize("(optional)", Fore.GREEN)
                    value = colorize("<not assigned>", Fore.LIGHTGREEN_EX)

                # No value assigned.
                lines.append("   {} {} = {}".format(
                    colorize(placeholder.name.rjust(placeholder_name_max_len), Fore.WHITE), status, value))
            else:
                # Print list of assigned values.
                status = colorize("(required)", Fore.GREEN) \
                    if placeholder.required else colorize("(optional)", Fore.GREEN)
                for i in range(len(values)):
                    placeholder_name = placeholder.name if i == 0 else len(placeholder.name) * " "
                    value = values[i]
                    lines.append("   {} {} {} {}".format(
                        colorize(placeholder_name.rjust(placeholder_name_max_len), Fore.WHITE),
                        status, "=" if i == 0 else "|", value))
                    if i == 0: status = len("(optional)") * " "  # Show (required/optional) only for the first value.

        return lines