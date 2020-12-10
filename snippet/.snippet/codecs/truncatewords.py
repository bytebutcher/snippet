from snippet.snippet import StringCodec


class Codec(StringCodec):
    """ Truncate a string after `arg` number of words. """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, content, arg):
        length = int(arg)
        words = content.split()
        if len(words) <= length:
            return content
        else:
            return ' '.join(words[:length])