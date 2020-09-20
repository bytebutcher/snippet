from snippet.snippet import Codec


class SafeFilename(Codec):
    """
    Transforms a string to a safe file name by replacing all special-characters with an underscore.

    Example:

        Input:
            some $string$

        Output:
            some__string_
    """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=[])

    def run(self, input):
        return "".join([x if x.isalnum() else "_" for x in input])