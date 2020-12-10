from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Center the value in a field of a given width. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, value, arg):
        return value.center(int(arg))