import unittest

from tests.main import new_snippet


class TestB64Codec(unittest.TestCase):

    def testB64(self):
        self.assertEqual(new_snippet("<arg1|b64>", ["arg1=test"]), ["dGVzdA=="])
        self.assertEqual(new_snippet("<arg1|b64|b64>", ["arg1=test"]), ["ZEdWemRBPT0="])