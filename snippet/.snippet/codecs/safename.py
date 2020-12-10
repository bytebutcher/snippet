from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Transforms a string to a safe file name by replacing all special-characters with an underscore. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, input):
        return "".join([x if x.isalnum() else "_" for x in input])