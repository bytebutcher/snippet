import os
import unittest

test_path = os.path.dirname(os.path.realpath(__file__))


def load_tests(loader, filter):
    """
    Load all test cases and return a unittest.TestSuite object.
    """
    suite = unittest.TestSuite()
    for r, d, f in os.walk(test_path):
        module_path = os.path.relpath(r, os.path.dirname(test_path)).replace(os.path.sep, ".")
        for file in f:
            filename, ext = os.path.splitext(file)
            if ext == ".py" and not file.startswith("_"):
                if not filter or module_path + "." + filename in filter:
                    print("[ADD ] " + module_path + "." + filename)
                    test = loader.loadTestsFromName(module_path + "." + filename)
                    suite.addTest(test)
                else:
                    print("[SKIP] " + module_path + "." + filename)
    return suite
