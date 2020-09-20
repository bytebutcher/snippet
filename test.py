import logging
import unittest
from snippet.snippet import Config, Snippet, app_name, home_config_path, app_config_path

config = Config(app_name, [home_config_path, app_config_path], logging.DEBUG)

def new_snippet(format_string, arguments):
    s = Snippet(config)
    s.format_string = format_string
    s.arguments = arguments
    return s.build()


class TestSnippet(unittest.TestCase):

    def test_no_placeholders(self):
        self.assertEqual(new_snippet("abc def", []), ["abc def"])

    def test_simple_placeholders(self):
        self.assertEqual(new_snippet("abc <arg1> <arg2> def", ["arg1=test", "arg2=tset"]), ["abc test tset def"])

    def test_placeholder_empty_value(self):
        self.assertEqual(new_snippet("abc <arg1> def", ["arg1="]), ["abc  def"])

    def test_uppercase_placeholder_name_in_argument(self):
        self.assertEqual(new_snippet("<arg1>", ["ARG1=test"]), ["test"])

    def test_uppercase_placeholder_name_in_format_string(self):
        self.assertEqual(new_snippet("<ARG1>", ["arg1=test"]), ["test"])

    def test_uppercase_placeholder_name_in_format_string_argument(self):
        self.assertEqual(new_snippet("<ARG1>", ["ARG1=test"]), ["test"])

    def test_simple_placeholder_file_test(self):
        self.assertEqual(new_snippet("abc <arg1> <arg2> def", ["arg1=test", "arg2:test/data.txt"]), [
            "abc test 1234567 def", "abc test QWERTYU def", "abc test  a b c def"])

    def test_codec(self):
        self.assertEqual(new_snippet("abc <arg1> <arg1:b64> <arg2> <arg2:b64:b64> def", ["arg1=test", "arg2=tset"]), [
            "abc test dGVzdA== tset ZEhObGRBPT0= def"])

    def test_optional_arguments_without_start(self):
        self.assertEqual(new_snippet("[<arg2>] abc <arg1>", ["arg1=test"]), [
            " abc test"
        ])

    def test_optional_arguments_without_end(self):
        self.assertEqual(new_snippet("abc <arg1> [<arg2>]", ["arg1=test"]), [
            "abc test "
        ])

    def test_optional_arguments_without_middle(self):
        self.assertEqual(new_snippet("abc <arg1> [<arg2>] cba", ["arg1=test"]), [
            "abc test  cba"
        ])

        self.assertEqual(new_snippet("abc <arg1> [<arg2>] cba <arg3>", ["arg1=test", "arg3=tset"]), [
            "abc test  cba tset"
        ])
        self.assertEqual(new_snippet("abc <arg1> [<arg2>] cba <arg3> bsd", ["arg1=test", "arg3=tset"]), [
            "abc test  cba tset bsd"
        ])

    def test_optional_arguments_with(self):
        self.assertEqual(new_snippet("abc <arg1> [<arg2>]", ["arg1=test", "arg2=tset"]), [
            "abc test tset"
        ])

    def test_optional_arguments_no(self):
        self.assertEqual(new_snippet("abc [<arg1> <arg2>]", ["arg1=test"]), [
            "abc "
        ])

    def test_optional_and_required(self):
        self.assertEqual(new_snippet("a<arg>b[c<arg>d]", ["arg="]), [
            "ab"
        ])

    def test_placeholder_default_text(self):
        self.assertEqual(new_snippet("abc <arg1==!Test!=>", []), [
            "abc =!Test!="
        ])

    def test_placeholder_default_text_with_codec(self):
        self.assertEqual(new_snippet("abc <arg1:b64=test>", []), [
            "abc dGVzdA=="
        ])

    def test_repeatable_placeholder_default_text(self):
        self.assertEqual(new_snippet("abc <arg1...=test>", []), [
            "abc test"
        ])

    def test_repeatable_placeholder_default_text_with_codec(self):
        self.assertEqual(new_snippet("abc <arg1:b64...=test>", []), [
            "abc dGVzdA=="
        ])

    def test_optional_default_text(self):
        self.assertEqual(new_snippet("<arg1> [<arg2=test> <arg3>]", ["arg1=123", "arg3=321"]), [
            "123 test 321"
        ])
        self.assertEqual(new_snippet("<arg1> [<arg2=test> <arg3>]", ["arg1=123"]), [
            "123 "
        ])

    def test_optional_default_and_required(self):
        self.assertEqual(new_snippet("<arg1> [<arg1=test>]", []), [
            "test test"
        ])

    def test_unset_optional_with_default_text(self):
        self.assertEqual(new_snippet("a[b<arg1=test>b]a", ["arg1="]), [
            "aa"
        ])

    def test_parse_big_single_argument(self):
        self.assertEqual(
            new_snippet("<arg1>", ["arg1=a b arg2=c d"]),
            ["a b arg2=c d"]
        )

    def test_parse_big_single_argument_two(self):
        self.assertEqual(
            new_snippet("<arg1>", ["a b arg2=c d"]),
            ["a b arg2=c d"]
        )

    def test_escaped_square_bracket_in_format_string(self):
        self.assertEqual(new_snippet("\[General\]", []), [
            "[General]"
        ])

    def test_escaped_angle_bracket_in_format_string(self):
        self.assertEqual(new_snippet("\<html\>", []), [
            "<html>"
        ])

    def test_angle_bracket_in_argument(self):
        # Value of arg1 should not be replaced with value of arg3
        self.assertEqual(new_snippet("123 <arg1> 456 <arg3>", ["arg1=<arg3>", "arg3=789"]), [
            "123 <arg3> 456 789"
        ])

    def test_arguments_quote(self):
        self.assertEqual(new_snippet("<arg1>", ['arg1="']), [
            '"'
        ])

    def test_argument_escaped_quote(self):
        self.assertEqual(new_snippet("<arg1>", ['arg1=\"']), [
            '\"'
        ])

    def test_argument_escaped_angle_bracket(self):
        self.assertEqual(new_snippet("<arg1>", ['arg1=\<html\>']), [
            '\<html\>'
        ])


if __name__ == '__main__':
    unittest.main()
