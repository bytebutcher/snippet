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

| Command | Description |
|---|---|
| `make install` | Install package in editable mode |
| `make install-test` | Install package with test dependencies |

## Test

| Command | Description |
|---|---|
| `make test` | Run unit tests |
| `make test-integration` | Build and run integration tests in docker |
| `make test-integration-quick` | Run integration tests using existing image (skips build) |

## Publish

| Command | Description |
|---|---|
| `make publish-test` | Upload to TestPyPi |
| `make publish` | Upload to PyPi |

Both `publish-test` and `publish` will automatically run `build`, `test`, and `test-integration` first.

**Version tip:** When testing a publish (e.g., `1.0.0`), use version `0.9.9.1` and increment the last digit for each test run. Only use your real version when you're confident everything works.

**TestPyPi install tip:** Use `--extra-index-url` to pull dependencies from PyPi when they don't exist on TestPyPi:
```commandline
pip3 install --extra-index-url https://test.pypi.org/simple/ <package_name>==<package_version>
```

# Resources

- https://twine.readthedocs.io/en/latest/
- https://docs.pytest.org/en/latest/
