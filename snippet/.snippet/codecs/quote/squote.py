from snippet.snippet import Codec


class Squote(Codec):
    """
    Surrounds a string with single quotes.

    Example:

        Input:
            abcdefghijklmnopqrstuvwxyz

        Output:
            'abcdefghijklmnopqrstuvwxyz'
    """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, input):
        return "'{}'".format(input)