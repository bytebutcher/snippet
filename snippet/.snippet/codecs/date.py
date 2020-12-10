from snippet.snippet import StringCodec
from datetime import datetime


class Codec(StringCodec):
    """ Takes a list of items and joins them with the specified separator. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, input, format):
        return datetime.fromtimestamp(float(input)).strftime(format)