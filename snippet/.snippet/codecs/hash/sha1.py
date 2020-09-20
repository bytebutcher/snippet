from snippet.snippet import Codec


class Sha1(Codec):
    """
    Hashes a string using SHA1.

    Example:

        Input:
            abcdefghijklmnopqrstuvwxyz
            ^°!"§$%&/()=?´`<>| ,.-;:_#+'*~
            0123456789

        Output:
            518d5653e6c74547aa62b376c953be024ea3c1d3
    """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=["hashlib"])

    def run(self, input):
        import hashlib
        return hashlib.sha1(input.encode('utf-8', errors='surrogateescape')).hexdigest()