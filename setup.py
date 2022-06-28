"""Install script for the Sparv Pipeline."""

import os.path

import setuptools


def get_version(rel_path):
    """Get version number from package."""
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, rel_path), encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                delim = '"' if '"' in line else "'"
                return line.split(delim)[1]
        else:
            raise RuntimeError("Unable to find version string.")


def get_readme(readme_path):
    """Get the contents of the README file."""
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, readme_path), encoding="utf-8") as f:
        return f.read()


setuptools.setup(
    name="sparv-pipeline",
    version=get_version("sparv/__init__.py"),
    description="Språkbanken's text analysis tool",
    long_description=get_readme("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/spraakbanken/sparv-pipeline/",
    author="Språkbanken",
    author_email="sb-info@svenska.gu.se",
    license="MIT",
    packages=setuptools.find_namespace_packages(include=["sparv", "sparv.*"]),
    zip_safe=False,
    python_requires=">=3.6.2",
    install_requires=[
        "appdirs==1.4.4",
        "iso-639==0.4.5",
        "docx2python==1.27.1",
        "nltk==3.6.7",
        "protobuf~=3.19.0", # Used by Stanza; see https://github.com/spraakbanken/sparv-pipeline/issues/161
        "python-dateutil==2.8.2",
        "PyYAML==6.0",
        "questionary==1.10.0",
        "rich==11.0.0",
        "snakemake==6.3.0",
        "stanza==1.3.0",
        "torch>=1.9.1",  # Used by Stanza; see https://github.com/spraakbanken/sparv-pipeline/issues/82
        "typing-inspect==0.7.1"
    ],
    extras_require={
        "dev": [
            "pandocfilters==1.5.0",
            "pytest==6.2.5",
            "pytest-sugar==0.9.4"
        ]
    },
    entry_points={
        "console_scripts": [
            "sparv=sparv.__main__:main"
        ]
    },
    package_data={
        "sparv": ["core/Snakefile", "resources/config/*", "resources/config/presets/*"]
    }
)
