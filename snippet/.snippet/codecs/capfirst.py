from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Capitalize the first character of the value. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, value):
        return value and value[0].upper() + value[1:]
