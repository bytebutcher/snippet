import unittest

from tests.main import new_snippet


class TestAddCodec(unittest.TestCase):

    def testAddIntegers(self):
        self.assertEqual(new_snippet("<arg1|add:'12'>", ["arg1=21"]), ["33"])

    def testAddString(self):
        self.assertEqual(new_snippet("<arg1|add:'456'>", ["arg1=test"]), ["test456"])

    def testAddMixed(self):
        self.assertEqual(new_snippet("<arg1|add:'test'>", ["arg1=123"]), ["123test"])
        self.assertEqual(new_snippet("<arg1|add:'123'>", ["arg1=test"]), ["test123"])

    def testAddRepeatable(self):
        self.assertEqual(new_snippet("<arg1...|add:'abc'>", ["arg1=def", "arg1=cba"]), ["defabc cbaabc"])
        self.assertEqual(new_snippet("<arg1...|add:'123'>", ["arg1=321", "arg1=111"]), ["444 234"])