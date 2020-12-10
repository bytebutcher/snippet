from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Adds the argument to the value. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, value, arg):
        try:
            return str(int(value) + int(arg))
        except (ValueError, TypeError):
            try:
                return value + arg
            except Exception:
                return ''