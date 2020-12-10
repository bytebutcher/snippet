from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Encodes a string to an URL. Spaces are encoded to plus-signs. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=["urllib"])

    def run(self, input):
        import urllib.parse
        return urllib.parse.quote_plus(input.encode('utf-8', errors='surrogateescape'))