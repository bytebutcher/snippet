from snippet.snippet import Codec


class B64(Codec):
    """
    Encodes a text using Base64.

    Example:

        Input:
            abcdefghijklmnopqrstuvwxyz
            ^°!"§$%&/()=?´`<>| ,.-;:_#+'*~
            0123456789

        Output:
            YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoKXsKwISLCpyQlJi8oKT0/wrRgPD58ICwuLTs6XyMrJyp+CjAxMjM0NTY3ODk=
    """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=["base64"])

    def run(self, input):
        import base64
        return base64.b64encode(input.encode('utf-8', errors="surrogateescape")).decode('utf-8',
                                                                                       errors="surrogateescape")