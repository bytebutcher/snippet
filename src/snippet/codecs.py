from inspect import signature


class Codec(object):
    """ Abstract codec class used for individual codecs. """

    def __init__(self, author, dependencies):
        self.name = self.__class__.__name__
        self.author = author
        self.dependencies = dependencies

    def run(self, text, *args):
        pass


class StringCodec(Codec):
    pass


class ListCodec(Codec):
    pass


class CodecRunner:
    """ Applies the codecs specified in the placeholder to the assigned values. """

    def __init__(self, codecs):
        self._codecs = codecs

    def run(self, row_item, placeholder):
        def run_codec(codec, input, arguments):
            try:
                expected_parameters = len(signature(codec.run).parameters) - 1  # do not count input
                actual_parameters = 1 if isinstance(arguments, str) else len(arguments)
                if expected_parameters != actual_parameters:
                    raise Exception(
                        "Expected {} parameters, got {}, {}!".format(expected_parameters, actual_parameters, arguments))
                if isinstance(arguments, str):
                    return codec.run(input, arguments)
                elif len(arguments) == 0:
                    return codec.run(input)
                else:
                    return codec.run(input, *arguments)
            except Exception as err:
                # Add the codec name to the exception message to know where this exception is coming from.
                raise Exception("{}: {}".format(codec.name, '.'.join(err.args)))

        if isinstance(row_item, list):  # Repeatable
            values = row_item
            for placeholder_codec in placeholder.codecs:
                codec = self._codecs[placeholder_codec.name]
                if isinstance(codec, StringCodec):
                    values = [run_codec(codec, value, placeholder_codec.arguments) for value in values]
                elif isinstance(codec, ListCodec):
                    values = run_codec(codec, values, placeholder_codec.arguments)
                else:
                    values = [run_codec(codec, values, placeholder_codec.arguments)]
            return " ".join(values)
        else:
            value = row_item
            for placeholder_codec in placeholder.codecs:
                codec = self._codecs[placeholder_codec.name]
                if isinstance(codec, StringCodec):
                    value = run_codec(codec, value, placeholder_codec.arguments)
                elif isinstance(codec, ListCodec):
                    value = " ".join(run_codec(codec, [value], placeholder_codec.arguments))
                else:
                    value = run_codec(codec, value, placeholder_codec.arguments)
            return value
