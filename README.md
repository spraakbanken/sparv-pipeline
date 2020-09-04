# Språkbanken's Sparv Pipeline

The Sparv pipeline is a corpus annotation tool run from the command line. Additional documentation can be found here:
https://spraakbanken.gu.se/en/tools/sparv/pipeline.

Check the [changelog](docs/changelog.md) to see what's new!

Sparv is developed by [Språkbanken](https://spraakbanken.gu.se/). The source code is available under the [MIT
license](https://opensource.org/licenses/MIT).

If you have any questions, problems or suggestions please contact <sb-sparv@svenska.gu.se>.

## Prerequisites

* A Unix-like environment (e.g. Linux, OS X)
* [Python 3.6](http://python.org/) or newer

### Additional prerequisites

* [Java](http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html) (if you want to run the
  Malt parser, Swedish word sense disambiguation or the Stanford Parser)

## Installation

The Sparv pipeline can be installed using [pip](https://pip.pypa.io/en/stable/installing):

```
pip install --user sparv-pipeline
```

Alternatively you can install Sparv from the latest release from GitHub with pipx:

```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install https://github.com/spraakbanken/sparv-pipeline/archive/latest.tar.gz
```

Now you should be ready to run the Sparv pipeline! Try it by typing `sparv --help`.

### Installation of additional software

The Sparv Pipeline can be used together with several plugins and third-party software. Please check the Sparv user
manual on [Språkbanken's homepage](https://spraakbanken.gu.se/en/tools/sparv/pipeline/installation) for more details!


## Running tests

If you want to run the tests you will need to clone this project from
[GitHub](https://github.com/spraakbanken/sparv-pipeline) since the test data is not distributed with pip. TODO: What
about the zip-release??

Before cloning the repository with [git](https://git-scm.com/downloads) make sure you have [Git Large File
Storage](https://git-lfs.github.com/) installed (`apt install git-lfs`). Some files will not be downloaded correctly
otherwise.

We recommend that you set up a virtual environment and install the dependencies (including the dev dependencies) listed
in `setup.py`:

```
python3 -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

Now with the virtual environment activated you can run `pytest` from the sparv-pipeline directory. You can run
particular tests using the provided markers (e.g. `pytest -m swe` to run the Swedish tests only) or via substring
matching (e.g. `pytest -k "not slow"` to skip the slow tests).
