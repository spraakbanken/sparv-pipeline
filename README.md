# Språkbanken's Sparv Pipeline

The Sparv pipeline is a corpus annotation tool run from the command line. The documentation can be found here:
https://spraakbanken.gu.se/sparv/docs.

Check the [changelog](changelog.md) to see what's new!

Sparv is developed by [Språkbanken](https://spraakbanken.gu.se/). The source code is available under the [MIT
license](https://opensource.org/licenses/MIT).

If you have any questions, problems or suggestions please contact <sb-sparv@svenska.gu.se>.

## Prerequisites

* A Unix-like environment (e.g. Linux, OS X or [Windows Subsystem for
  Linux](https://docs.microsoft.com/en-us/windows/wsl/about)) *Note:* Most things within Sparv should work in a Windows
  environment as well but we cannot guarantee anything since we do not test our software on Windows.
* [Python 3.6.1](http://python.org/) or newer
* [Java](http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html) (if you want to run
  Swedish dependency parsing, Swedish word sense disambiguation or the Stanford Parser)

## Installation

The Sparv pipeline can be installed using [pip](https://pip.pypa.io/en/stable/installing). We even recommend using
[pipx](https://pipxproject.github.io/pipx/) so that you can install the `sparv` command globally:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install sparv-pipeline
```

Alternatively you can install Sparv from the latest release from GitHub:

```bash
pipx install https://github.com/spraakbanken/sparv-pipeline/archive/latest.tar.gz
```

Now you should be ready to run the Sparv command! Try it by typing `sparv --help`.

The Sparv Pipeline can be used together with several plugins and third-party software. Please check the [Sparv user
manual](https://spraakbanken.gu.se/en/tools/sparv/pipeline/installation) for more details!

## Roadmap

* Export of corpus metadata to META-SHARE format
* Support for Swedish historic texts
* Support for parallel corpora
* Preprocessing of indata with automatic chunking

## Running tests

If you want to run the tests you will need to clone this project from
[GitHub](https://github.com/spraakbanken/sparv-pipeline) since the test data is not distributed with pip.

Before cloning the repository with [git](https://git-scm.com/downloads) make sure you have [Git Large File
Storage](https://git-lfs.github.com/) installed (`apt install git-lfs`). Some files will not be downloaded correctly
otherwise.

We recommend that you set up a virtual environment and install the dependencies (including the dev dependencies) listed
in `setup.py`:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

Now with the virtual environment activated you can run `pytest` from the sparv-pipeline directory. You can run
particular tests using the provided markers (e.g. `pytest -m swe` to run the Swedish tests only) or via substring
matching (e.g. `pytest -k "not slow"` to skip the slow tests).
