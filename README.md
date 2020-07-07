# Språkbanken's Sparv Pipeline

The Sparv Pipeline is a corpus annotation pipeline created by [Språkbanken](https://spraakbanken.gu.se/).
The source code is made available under the [MIT license](https://opensource.org/licenses/MIT).

Additional documentation can be found here:
https://spraakbanken.gu.se/en/tools/sparv/pipeline

For questions, problems or suggestions contact:
sb-sparv@svenska.gu.se

## Prerequisites

* A Unix-like environment (e.g. Linux, OS X)
* [Python 3.6](http://python.org/) or newer
* [pip](https://pip.pypa.io/en/stable/installing)
* [Git](https://git-scm.com/downloads) and [Git Large File Storage](https://git-lfs.github.com/)

### Additional prerequisites
* [Java](http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html) (if you want to run the Malt parser or Swedish word sense disambiguation)

## Installation

* Before cloning the git repository make sure you have
  [Git Large File Storage](https://git-lfs.github.com/)
  installed (`apt install git-lfs`). Some files will not be downloaded correctly otherwise.
* The sparv-pipeline directory must not be removed after installation, so make sure to clone to a 
  location where it can be kept permanently.
* After cloning, install pipx and sparv-pipeline:

```
cd sparv-pipeline
python3 -m pip install --user pipx
python3 -m pipx ensurepath
cd ..
pipx install -e sparv-pipeline
```

* Now you should be ready to run the Sparv pipeline! Try it by typing `sparv --help`.

## Installation of additional software

The Sparv Pipeline can be used together with several plugins and third-party software. Please check [Språkbanken's homepage](https://spraakbanken.gu.se/verktyg/sparv/importkedja/installation) for more details!


## Running tests

Setup a virtual environment, activate it and install the dependencies (including the dev dependencies) listed in `setup.py`:

```
python3 -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

Now with the virtual environment activated you can run `pytest` from the sparv-pipeline directory.
