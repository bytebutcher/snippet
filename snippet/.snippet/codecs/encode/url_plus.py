from snippet.snippet import Codec


class UrlPlus(Codec):
    """
    Encodes a string to an URL. Spaces are encoded to plus-signs.

    Example:

        Input:
            abcdefghijklmnopqrstuvwxyz
            ^°!"§$%&/()=?´`<>| ,.-;:_#+'*~
            0123456789

        Output:
            abcdefghijklmnopqrstuvwxyz \\
            %0A%5E%C2%B0%21%22%C2%A7%24%25%26/%28%29%3D%3F%C2%B4%60%3C%3E%7C+%2C.-%3B%3A_%23%2B%27%2A%7E%0A \\
            0123456789
    """

    def __init__(self):
        super().__init__(author="bytebutcher", dependencies=["urllib"])

    def run(self, input):
        import urllib.parse
        return urllib.parse.quote_plus(input.encode('utf-8', errors='surrogateescape'))