from snippet.snippet import Codec


class Md5(Codec):
    """
    Hashes a string using MD5.

    Example:

        Input:
            abcdefghijklmnopqrstuvwxyz
            ^°!"§$%&/()=?´`<>| ,.-;:_#+'*~
            0123456789

        Output:
            4384c8873a173210f11c30d6ae54baec
    """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=["hashlib"])

    def run(self, input):
        import hashlib
        return hashlib.md5(input.encode('utf-8', errors='surrogateescape')).hexdigest()