from snippet.snippet import ListCodec


class Codec(ListCodec):
    """ Return the last item in a list. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, value):
        try:
            return [value[-1]]
        except IndexError:
            return ['']