import unittest

from tests.main import new_snippet


class TestUrlCodec(unittest.TestCase):

    def testUrl(self):
        self.assertEqual(new_snippet("<arg1|url>", ["arg1=^°!\"§$%&/()=?´`<>| ,.-;:_#+'*~"]), [
            "%5E%C2%B0%21%22%C2%A7%24%25%26/%28%29%3D%3F%C2%B4%60%3C%3E%7C%20%2C.-%3B%3A_%23%2B%27%2A%7E"])
