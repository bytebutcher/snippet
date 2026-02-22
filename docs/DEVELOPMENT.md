# Development

This document provides guidance on setting up the development environment for this project, 
with an emphasis on ensuring the Python module structure works seamlessly for local development and testing.

## Directory Structure

The project follows this directory structure:
```scss
data/
src/
    <package-name>/
        __init__.py
        ... (other module files)
tests/
    codecs/
    __init__.py
    ... (other test files)
```

- **`src/`:** Contains the source code for the project.
- **`tests/`:** Contains all test files, organized by type (e.g., unit, integration).



## Setup

Create and switch to a dedicated environment using the following command:
```commandline
python3 -m venv .venv
source .venv/bin/activate
```

The package definition is stored in the `setup.py` file. 
To allow modifying the source code and testing changes immediately without reinstalling the package,
install the project in `Editable Mode` by running the following command in the terminal from the project root:
```commandline
pip install -e .
```

## Test

### How to install testing packages?

To install testing packages from the command line, issue the following command:
```commandline
pip install -e .[test]
```

### How to run tests using the command line?

To run tests from the command line, issue the following command:
```commandline
python3 test.py
```

## Publish

Publish an application on PyPi usually follows the steps below:

- **Step 1:** Build Package
- **Step 2:** Upload to TestPyPi
- **Step 3:** Test Package
- **Step 4:** Upload to PyPi

### Step 1: Build Package
**Important:** If you want to publish version 1.0.0 change the version in setup.py for your tests to 0.9.9.1 and increment the last digit for each test. If you are sure your package is working as expected use version 1.0.0.
```commandline
rm -rf build/ *.egg-info/ dist/ && python3 setup.py sdist bdist_wheel && twine check dist/*
```


### Step 2: Upload to TestPyPi

```commandline
twine upload -r testpypi dist/*
```

### Step 3: Test Package
Make sure to use `--extra-index-url` to pull packages from pypi when they do not exist on testpypi.
```commandline
pip3 install --extra-index-url https://test.pypi.org/simple/ <package_name>==<package_version>
```

### Step 4: Upload to PyPi
```commandline
twine upload dist/*
```

### Troubleshooting

#### Issue 1 - invalid command 'bdist_wheel'
- **Description:**
  When issuing the command python3 setup.py sdist bdist_wheel an error message appears: invalid command 'bdist_wheel'.
- **Solution:**
  Install the wheel package using pip3:
  ```commandline
  pip3 install wheel
  ```

# Resources

- https://twine.readthedocs.io/en/latest/
- https://docs.pytest.org/en/latest/
