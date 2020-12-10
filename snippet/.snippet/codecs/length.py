from snippet.snippet import Codec


class Codec(Codec):
    """ Return the length of the value - useful for lists. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, value):
        try:
            return str(len(value)) # Works for lists and strings
        except (ValueError, TypeError):
            return "0"