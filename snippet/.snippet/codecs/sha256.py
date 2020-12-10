from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Hashes a string using SHA256. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=["hashlib"])

    def run(self, input):
        import hashlib
        return hashlib.sha256(input.encode('utf-8', errors='surrogateescape')).hexdigest()