from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Hashes a string using MD5. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=["hashlib"])

    def run(self, input):
        import hashlib
        return hashlib.md5(input.encode('utf-8', errors='surrogateescape')).hexdigest()