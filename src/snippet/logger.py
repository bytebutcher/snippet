import logging
import sys

from colorama import Fore

from snippet.utils import colorize


def log_method_call():
    """
    A decorator for logging method or function calls.

    It logs the name of the method/function and its arguments before the call is executed.
    Can be applied to both standalone functions and class methods.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = Logger.get_instance()
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            logger.debug(f"Calling {func.__name__}({signature})")
            return func(*args, **kwargs)

        return wrapper

    return decorator


class Logger:

    # Static logger instance
    _instance = None

    @staticmethod
    def get_instance():
        if Logger._instance is None:
            raise ValueError("Logger instance not initialized. Call initialize first.")
        return Logger._instance

    @staticmethod
    def initialize(app_id, log_format, level):
        if Logger._instance is not None:
            raise ValueError("Logger instance already initialized.")
        Logger._instance = Logger(app_id, log_format, level)
        return Logger._instance

    def __init__(self, app_id, log_format, level):
        self.logger = logging.getLogger(app_id)
        self.handler = logging.StreamHandler(sys.stderr)
        self.handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(self.handler)
        self._set_level(level)

    def _set_level(self, level):
        self.logger.setLevel(level)
        self.handler.setLevel(level)

    def _get_level(self):
        return self.logger.level

    def info(self, message):
        self.logger.info(colorize(" INFO: ", Fore.GREEN) + message)

    def debug(self, message):
        self.logger.debug(colorize("DEBUG: {}".format(message), Fore.LIGHTBLACK_EX))

    def warning(self, message):
        self.logger.warning(colorize(" WARN: ", Fore.LIGHTYELLOW_EX) + message)

    def error(self, message):
        self.logger.info(colorize("ERROR: ", Fore.RED) + message)

    level = property(fset=_set_level, fget=_get_level)
