from snippet.snippet import Codec


class Sha256(Codec):
    """
    Hashes a string using SHA256.

    Example:

        Input:
            abcdefghijklmnopqrstuvwxyz
            ^°!"§$%&/()=?´`<>| ,.-;:_#+'*~
            0123456789

        Output:
            0a4035197aa3b94d8ee2ff7d5b286636 \\
            f6264f6c96ffccf3c4b777a8fb9be674
    """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=["hashlib"])

    def run(self, input):
        import hashlib
        return hashlib.sha256(input.encode('utf-8', errors='surrogateescape')).hexdigest()