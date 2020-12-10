import unittest


if __name__ == '__main__':
    import tests
    loader = unittest.TestLoader()
    suite = tests.load_tests(loader, [])
    unittest.TextTestRunner().run(suite)
