import os.path

from snippet.codecs import StringCodec


class Codec(StringCodec):
    """ Extracts the filename from a file path. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, input):
        return os.path.basename(input.encode('utf-8', errors="surrogateescape")).decode('utf-8',
                                                                                       errors="surrogateescape")