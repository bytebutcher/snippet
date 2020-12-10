import re

from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Convert a string into titlecase. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, value):
        t = re.sub("([a-z])'([A-Z])", lambda m: m[0].lower(), value.title())
        return re.sub(r'\d([A-Z])', lambda m: m[0].lower(), t)
