from snippet.snippet import Codec


class Sha512(Codec):
    """
    Hashes a string using SHA3 512.

    Example:

        Input:
            abcdefghijklmnopqrstuvwxyz
            ^°!"§$%&/()=?´`<>| ,.-;:_#+'*~
            0123456789

        Output:
            82ca87f576cadb05d4c911f36c98ed2735f45cad359d6ef5f6d544f5a3210e3e \
            cf080be15e539e23c15e2eb23054677d8a015ee56be2d9673c9f187d290906ed
    """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=["hashlib"])

    def run(self, input):
        import hashlib
        return hashlib.sha512(input.encode('utf-8', errors='surrogateescape')).hexdigest()