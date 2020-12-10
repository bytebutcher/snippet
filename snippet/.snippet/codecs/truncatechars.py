from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Truncate a string after `arg` number of characters. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, value, arg):
        length = int(arg)
        return value[:length]