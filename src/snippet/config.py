import os
import sys

from iterfzf import iterfzf

from snippet.logger import Logger
from snippet.models import Data
from snippet.utils import safe_join_path


class Config(object):

    def __init__(self, app_name, paths, log_level):
        self.paths = paths
        self.format_template_paths = [safe_join_path(path, "templates") for path in paths]
        self.codec_paths = [safe_join_path(path, "codecs") for path in paths]
        self.logger = Logger.initialize(app_name, "%(msg)s", log_level)
        self.profile = self._load_profile()
        self.codecs = self._load_codecs()
        self._reserved_placeholder_values = []

    def _load_profile(self):
        for profile_path in self.paths:
            profile_file = safe_join_path(profile_path, "snippet_profile" + ".py")
            if os.path.exists(profile_file):
                try:
                    self.logger.debug("Loading profile at {} ...".format(profile_path))
                    # Since the path may contain special characters which can not be processed by the __import__
                    # function we temporarily add the path in which the profile.py is located to the PATH.
                    sys.path.append(profile_path)
                    profile = __import__("snippet_profile").Profile()
                    sys.path.pop()
                    return profile
                except:
                    self.logger.warning("Loading profile at {} failed!".format(profile_path))
        return None

    def _load_codecs(self):

        codecs = {}
        for codec_path in self.codec_paths:
            # Since the path may contain special characters which can not be processed by the __import__
            # function we temporarily add the path in which the codecs are located to the PATH.
            if os.path.exists(codec_path):
                sys.path.append(codec_path)
                filepath = codec_path
                for r, d, f in os.walk(filepath):
                    for file in f:
                        filename, ext = os.path.splitext(file)
                        if ext == ".py":
                            try:
                                self.logger.debug("Loading codec {} at {}...".format(filename, filepath))
                                codecs[filename] = getattr(__import__(filename), "Codec")()
                            except Exception as err:
                                self.logger.warning("Loading codec {} failed!".format(filename))
                                self.logger.exception(err)
                sys.path.pop()

        return codecs

    def _get_template_file(self, format_template_name):
        if not format_template_name:
            return None

        if format_template_name.endswith(".snippet"):
            # Consider template files in the current working directory.
            format_template_file = safe_join_path(os.getcwd(), format_template_name)
            return format_template_file if os.path.isfile(format_template_file) else None

        for format_template_path in self.format_template_paths:
            format_template_file = safe_join_path(format_template_path, format_template_name)
            if os.path.isfile(format_template_file):
                return format_template_file

        return None

    def _get_editor(self):
        return self.profile.editor

    def get_reserved_placeholders(self):
        return self.profile.placeholder_values if self.profile else []

    def get_reserved_placeholder_names(self):
        for reserved_placeholder in self.get_reserved_placeholders():
            yield reserved_placeholder.name

    def get_reserved_placeholder_values(self):
        if self._reserved_placeholder_values:
            return dict(self._reserved_placeholder_values)

        self._reserved_placeholder_values = Data()
        if self.profile:
            for placeholder_value in self.profile.placeholder_values:
                placeholder_name = placeholder_value.name
                self._reserved_placeholder_values.append(placeholder_name, placeholder_value.element())

        return dict(self._reserved_placeholder_values)

    def get_format_template_names(self):
        format_template_files = []
        # Get templates from home or app directory.
        for format_template_file_path in self.format_template_paths:
            if os.path.exists(format_template_file_path):
                exclude_extensions = ['.txt', '.md']
                exclude_directories = ['.git']
                for r, d, f in os.walk(format_template_file_path):
                    d[:] = [dir for dir in d if dir not in exclude_directories]
                    relpath = r[len(format_template_file_path) + 1:]
                    for file in f:
                        if list(filter(lambda x: file.lower().endswith(x), exclude_extensions)):
                            continue
                        format_template_files.append(safe_join_path(relpath, file))

        # Also consider files in the local directory which ends with .snippet.
        for file in os.listdir(os.fsencode(os.getcwd())):
            filename = os.fsdecode(file)
            if os.path.isfile(filename) and filename.endswith(".snippet"):
                format_template_files.append(filename)

        return sorted(list(set(format_template_files)))

    def get_format_template(self, format_template_name):
        format_template_file = self._get_template_file(format_template_name)
        if not format_template_file:
            format_template_name = iterfzf(self.get_format_template_names(), query=format_template_name)

        format_template_file = self._get_template_file(format_template_name)
        if not format_template_file:
            raise Exception("Loading {} failed! Template not found!".format(format_template_name or "template"))

        try:
            with open(format_template_file) as f:
                lines = []
                for line in f.read().splitlines():
                    lines.append(line)
                return format_template_name, os.linesep.join(lines)
        except:
            raise Exception("Loading {} failed! Invalid template format!".format(format_template_name or "template"))

    editor = property(_get_editor)