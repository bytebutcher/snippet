import pathlib
import setuptools
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="snippet-cli",
    version="1.0.0",
    description="An advanced snippet manager for the command-line.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/bytebutcher/snippet",
    author="bytebutcher",
    author_email="thomas.engel.web@gmail.com",
    license="GPL-3.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent"
    ],
    packages=setuptools.find_packages(),
    install_requires=[
        'pyparsing==2.4.6',
        'argcomplete==1.11.1',
        'iterfzf==0.5.0.20.0',
        'tabulate==0.8.7',
        'colorama==0.4.3'
    ],
    entry_points={
        "console_scripts": [
            "snippet=snippet:main",
        ]
    },
)
