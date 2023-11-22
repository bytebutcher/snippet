import logging
import os
import tempfile
import unittest
from parameterized import parameterized

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

    ####################################################################################################################
    # Placeholder
    ####################################################################################################################

    def test_simple_placeholders(self):
        self.assertEqual(new_snippet("abc <arg1> <arg2> def", ["arg1=test", "arg2=tset"]), ["abc test tset def"])

    def test_simple_multiline_placeholders(self):
        self.assertEqual(new_snippet("abc <arg1>\n<arg2> def", ["arg1=test", "arg2=tset"]), ["abc test\ntset def"])

    def test_simple_multiline_placeholders_with_comments(self):
        self.assertEqual(new_snippet("abc <arg1>\n#no replace <arg1> or <arg2>\n<arg2> def", ["arg1=test", "arg2=tset"]), ["abc test\n#no replace <arg1> or <arg2>\ntset def"])

    def test_simple_multiline_placeholders_ignore_placeholders_in_comments(self):
        self.assertEqual(
            new_snippet("abc <arg1>\n#no replace <argx> or <argy>\n<arg2> def", ["arg1=test", "arg2=tset"]),
            ["abc test\n#no replace <argx> or <argy>\ntset def"])

    def test_placeholder_empty_value(self):
        self.assertEqual(new_snippet("abcX<arg1>Ydef", ["arg1="]), ["abcXYdef"])

    def test_uppercase_placeholder_name_in_argument(self):
        self.assertEqual(new_snippet("<arg1>", ["ARG1=test"]), ["test"])

    def test_uppercase_placeholder_name_in_format_string(self):
        self.assertEqual(new_snippet("<ARG1>", ["arg1=test"]), ["test"])

    def test_uppercase_placeholder_name_in_format_string_argument(self):
        self.assertEqual(new_snippet("<ARG1>", ["ARG1=test"]), ["test"])

    def test_simple_placeholder_file_test(self):
        self.assertEqual(new_snippet("abc <arg1> <arg2> def", ["arg1=test", "arg2:tests/data.txt"]), [
            "abc test 1234567 def", "abc test QWERTYU def", "abc test  a b c def"])

    ####################################################################################################################
    # Optional
    ####################################################################################################################

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
        self.assertEqual(new_snippet("abc <arg1> [ <arg2> <arg3> ] <arg4>", ["arg1=test", "arg2=tset", "arg4=yyyy" ]), [
            "abc test  yyyy"
        ])
        self.assertEqual(new_snippet("abc <arg1> [ <arg2> <arg3> ] <arg4>",
            ["arg1=test", "arg2=tset", "arg3=xxxx", "arg4=yyyy" ]), [
            "abc test  tset xxxx  yyyy"
        ])

    def test_optional_arguments_no(self):
        self.assertEqual(new_snippet("abc [<arg1> <arg2>]", ["arg1=test"]), [
            "abc "
        ])

    def test_optional_and_required(self):
        self.assertEqual(new_snippet("a<arg>b[c<arg>d]", ["arg="]), [
            "ab"
        ])

    def test_optional_default_text(self):
        self.assertEqual(new_snippet("<arg1> [<arg2='test'> <arg3>]", ["arg1=123", "arg3=321"]), [
            "123 test 321"
        ])
        self.assertEqual(new_snippet("<arg1> [<arg2='test'> <arg3>]", ["arg1=123"]), [
            "123 "
        ])

    def test_optional_default_and_required(self):
        self.assertEqual(new_snippet("<arg1> [<arg1='test'>]", []), [
            "test test"
        ])

    def test_unset_optional_with_default_text(self):
        self.assertEqual(new_snippet("a[b<arg1='test'>b]a", ["arg1="]), [
            "aa"
        ])

    ####################################################################################################################
    # Default
    ####################################################################################################################

    def test_placeholder_default_text(self):
        self.assertEqual(new_snippet("abc <arg1='=!Test!='>", []), [
            "abc =!Test!="
        ])

    def test_placeholder_default_text_with_codec(self):
        self.assertEqual(new_snippet("abc <arg1|b64='test'>", []), [
            "abc dGVzdA=="
        ])

    ####################################################################################################################
    # Repeatable
    ####################################################################################################################

    def test_repeatable_placeholder(self):
        self.assertEqual(new_snippet("abc <arg1...>", ["arg1=1", "2", "3"]), [
            "abc 1 2 3"
        ])

    def test_repeatable_placeholder_default_text(self):
        self.assertEqual(new_snippet("abc <arg1...='test'>", []), [
            "abc test"
        ])

    def test_repeatable_placeholder_default_text_with_codec(self):
        self.assertEqual(new_snippet("abc <arg1...|b64='test'>", []), [
            "abc dGVzdA=="
        ])

    ####################################################################################################################
    # Codecs
    ####################################################################################################################

    def test_codec(self):
        self.assertEqual(new_snippet("abc <arg1> <arg1|b64> <arg2> <arg2|b64|b64> def", ["arg1=test", "arg2=tset"]), [
            "abc test dGVzdA== tset ZEhObGRBPT0= def"])

    def test_codec_join(self):
        self.assertEqual(new_snippet("<arg1...>", ['arg1=1', '2', '3']), [
            '1 2 3'
        ])
        self.assertEqual(new_snippet("<arg1...|join:','>", ['arg1=1', '2', '3']), [
            '1,2,3'
        ])

    def test_codec_missing_argument(self):
        self.assertRaises(Exception, new_snippet, "<arg1...|join>", ['arg1=1', '2', '3'])

    ####################################################################################################################
    # Escaped characters in format string
    ####################################################################################################################

    def test_escaped_square_bracket_in_format_string(self):
        self.assertEqual(new_snippet("\[General\]", []), [
            "[General]"
        ])

    def test_escaped_angle_bracket_in_format_string(self):
        self.assertEqual(new_snippet("\<html\>", []), [
            "<html>"
        ])

    def test_argument_escaped_quote(self):
        self.assertEqual(new_snippet("<arg1>", ['arg1=\"']), [
            '\"'
        ])

    def test_argument_escaped_angle_bracket(self):
        self.assertEqual(new_snippet("<arg1>", ['arg1=\<html\>']), [
            '\<html\>'
        ])

    ####################################################################################################################
    # Misc
    ####################################################################################################################

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

    def test_angle_bracket_in_argument(self):
        # Value of arg1 should not be replaced with value of arg3
        self.assertEqual(new_snippet("123 <arg1> 456 <arg3>", ["arg1=<arg3>", "arg3=789"]), [
            "123 <arg3> 456 789"
        ])

    def test_arguments_quote(self):
        self.assertEqual(new_snippet("<arg1>", ['arg1="']), [
            '"'
        ])

    @parameterized.expand([
        ['< arg1>', ['arg1=test']],  # illegal space
        ['<arg1 >', ['arg1=test']],  # illegal space
        ['< arg1 >', ['arg1=test']],  # illegal space
        ['<arg1 |b64>', ['arg1=test']],  # illegal space
        ['<arg1| b64>', ['arg1=test']],  # illegal space
        ['<arg1 | b64>', ['arg1=test']],  # illegal space
        ['<arg1 ...>', ['arg1=test']],  # illegal space
        ['<arg1... >', ['arg1=test']],  # illegal space
        ['<arg1 ... >', ['arg1=test']],  # illegal space
        ['<arg1..>', ['arg1=test']],  # illegal number of dots
        ['<arg1... |join:",">', ['arg1=test']],  # illegal space
        ['<arg1...|join : "," >', ['arg1=test']],  # illegal space
        ['<arg1...|join: "," >', ['arg1=test']],  # illegal space
        ['<arg1...|join:"," >', ['arg1=test']],  # illegal space
        ['<arg1...|join: ",">', ['arg1=test']],  # illegal space
        ['<arg1...|join :"," >', ['arg1=test']],  # illegal space
        ['<arg1...|join : ",">', ['arg1=test']],  # illegal space
        ['<arg1 ="test">', ['arg1=test']],  # illegal space
        ['<arg1= "test">', ['arg1=test']],  # illegal space
        ['<arg1 ="test">', ['arg1=test']],  # illegal space
        ['abc <arg1=test>', ['arg1=test']],  # no quotes
        ['<arg1...|join:,>', ['arg1=test']],  # no quotes
        ['<arg1\>', ['arg1=test']],  # not completely escaped
        ['\<arg1>', ['arg1=test']],  # not completely escaped
    ])
    def test_invalid_format_string(self, format, arguments):
        self.assertRaises(Exception, lambda: new_snippet(format, arguments))