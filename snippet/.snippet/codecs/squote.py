from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Surrounds a string with single quotes. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, input):
        return "'{}'".format(input)