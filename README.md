# Språkbanken's Sparv-Pipeline

The Sparv-Pipeline is a corpus annotation pipeline created by [Språkbanken](https://spraakbanken.gu.se/).
The source code is made available under the [MIT license](https://opensource.org/licenses/MIT).

Additional documentation can be found here:
https://spraakbanken.gu.se/eng/research/infrastructure/sparv

For questions, problems or suggestions contact:
sb-sparv@svenska.gu.se

## Prerequisites

* A Unix-like environment (e.g. Linux, OS X)
* Python 3.4 or newer
* GNU Make
* Java

## Installation

* Set variables in Makefile.config (especially SPARV_PIPELINE_PATH).
* Add `SPARV_MAKEFILES` to your environment variables and point its path
  to the `makefiles` directory.
* Create a Python 3 virtual environment and install the requirements:

    ```
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
    ```
* Build the pipeline models:

    ```
    make -C models/ all
    # Optional: remove unnecessary files to save disk space
    make -C models/ space
    ```

## Installation of additional software

Please check https://spraakbanken.gu.se/eng/research/infrastructure/sparv/distribution/pipeline for more information!