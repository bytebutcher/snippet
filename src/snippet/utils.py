import os
import sys

from colorama import Fore, Style
from iterfzf import iterfzf


def log_format_string(format_string, logger):
    logger.info(colorize("Format:", Fore.YELLOW))
    for line in format_string.split(os.linesep):
        if line.startswith("#"):
            logger.info(colorize("   {}".format(line), Fore.BLUE))
        else:
            logger.info(colorize("   {}".format(line), Fore.WHITE))


def log_format_template(format_template_name, logger):
    logger.info(colorize("Template:", Fore.YELLOW))
    logger.info(colorize("   {}".format(format_template_name), Fore.WHITE))


def colorize(string: str, color):
    """ Colorize a string. """
    return color + string + Style.RESET_ALL


def safe_join_path(*argv):
    """
    os.path.join does ignore everything prior to a component starting with a slash.
    This implementation does consider all components and normalizes the path.
    """
    return os.path.normpath(os.sep.join(argv))


def replace_within(string: str, replacement: str, start: int, end: int) -> str:
    """
    Return a copy of string with text replaced within the range of position start and end with the replacement string.

    string: the base string.
    replacement: the text which serves as replacement.
    start: the start position of the range with 0 <= start < len(text) && start <= end.
    end: the end position of the range with 0 <= end < len(text).
    """
    return string[:start] + replacement + string[end:]


def select_line(lines, query=None):
    """ Select format string from list of lines using iterfzf. """
    lines = [colorize(line, Fore.BLUE) if line.startswith("#") else line for line in lines.splitlines()]
    if len(lines) > 1:
        return iterfzf(reversed(lines), query=query, multi=True, ansi=True)
    else:
        return lines


def print_line(line):
    """ Color printing a line of the (evaluated) format string regarding comments. """
    if line.startswith("#"):
        print(colorize(line, Fore.BLUE), file=sys.stderr)
    else:
        print(line)