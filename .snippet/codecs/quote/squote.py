from snippet import Codec


class DQuote(Codec):
    """
    Surrounds a string with double quotes.

    Example:

        Input:
            abcdefghijklmnopqrstuvwxyz

        Output:
            "abcdefghijklmnopqrstuvwxyz"
    """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, input):
        return '"{}"'.format(input)
