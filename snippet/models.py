import json
import shlex
from collections import namedtuple, defaultdict


class PlaceholderFormat:
    """ An object representation of a placeholder. """

    Codec = namedtuple('Codec', ['name', 'arguments'])

    def __init__(self, format_string: str, required):
        try:
            data, self.start, self.end = format_string
            self.name = data.get("name").lower()  # Required
            self.codecs = [
                PlaceholderFormat.Codec(codec[0].lower(), codec[1:]) for codec in data.get("codecs", [])]  # Optional
            self.default = data.get("default")  # Optional
            self.repeatable = "repeatable" in data  # True or False
            self.required = required  # True or False
        except Exception:
            raise Exception("Transforming placeholders failed! Invalid format!")

    def __str__(self):
        return json.dumps(self.__dict__)


class Data(defaultdict):
    """ Map of placeholders with value lists e.g. { 'PLACEHOLDER-1': ('a','b','c'), 'PLACEHOLDER-2': ('d') } """

    def __init__(self):
        super().__init__(list)

    def append(self, placeholder, values):
        placeholder_key = placeholder.lower()
        if isinstance(values, list):
            for value in values:
                self[placeholder_key].append(value)
        else:
            if values.startswith('\\(') and values.endswith('\\)'):
                for value in shlex.split(values[2:-2]):
                    self[placeholder_key].append(value)
            else:
                self[placeholder_key].append(values)

    def to_data_frame(self):
        # Create table data with equally sized lists by filling them with empty strings
        # e.g. { 'placeholder-1': ('a','b','c'), 'placeholder-2': ('d','','') }
        table_data = Data()
        max_length = max([len(self[key]) for key in self.keys()])
        for placeholder in self.keys():
            for item in self[placeholder]:
                table_data.append(placeholder, item)
            for i in range(0, max_length - len(self[placeholder])):
                table_data.append(placeholder, "")

        return table_data