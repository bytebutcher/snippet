from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Encodes a text using Base64. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=["base64"])

    def run(self, input):
        import base64
        return base64.b64encode(input.encode('utf-8', errors="surrogateescape")).decode('utf-8',
                                                                                       errors="surrogateescape")