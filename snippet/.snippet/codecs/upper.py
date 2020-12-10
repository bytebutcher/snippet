from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Convert a string into all uppercase. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, value):
        return value.upper()