"""Install script for the Sparv Pipeline."""

import os.path

import setuptools


def get_version(rel_path):
    """Get version number from package."""
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, rel_path)) as f:
        for line in f:
            if line.startswith("__version__"):
                delim = '"' if '"' in line else "'"
                return line.split(delim)[1]
        else:
            raise RuntimeError("Unable to find version string.")


setuptools.setup(
    name="sparv-pipeline",
    version=get_version("sparv/__init__.py"),
    description="Språkbanken's corpus annotation pipeline",
    url="https://github.com/spraakbanken/sparv-pipeline/",
    author="Språkbanken",
    author_email="sb-info@svenska.gu.se",
    license="MIT",
    packages=setuptools.find_packages(include=["sparv", "sparv.*"]),
    zip_safe=False,
    python_requires=">=3.6",
    install_requires=[
        "alive-progress==1.4.3",
        "nltk==3.4.5",
        "python-dateutil==2.8.0",
        "pyyaml==5.1.2",
        "snakemake==5.13.0"
        ],
    entry_points={
        "console_scripts": [
            "sparv=sparv.__main__:main"
        ]
    }
)
