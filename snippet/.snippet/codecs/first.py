from snippet.snippet import ListCodec


class Codec(ListCodec):
    """ Return the first item in a list. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, value):
        try:
            return [value[0]]
        except IndexError:
            return ['']
