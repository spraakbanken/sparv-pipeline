# Writing Sparv Plugins

This section provides a practical guide to creating your own Sparv plugins. If you are new to the concepts of Sparv
modules, processors, and the plugin system, please refer to the previous sections for background. Here, we focus on the
concrete steps and best practices for developing, structuring, and distributing Sparv plugins.

## Getting Started

To help you get started quickly, we recommend using the official [Sparv plugin
template](https://github.com/spraakbanken/sparv-plugin-template), which provides a minimal working example and a
suggested project structure.

## Naming Requirements

The name of a Sparv module or plugin is the name of the *Python package directory* containing the module code. In
addition to being a valid Python identifier, the name must start with a namespace (representing the plugin author or
organization), followed by an underscore. This is to avoid name clashes with other plugins and will be enforced in the
future. In the example below, we use the prefix `sbx_` (for Språkbanken Text).

In addition to the Sparv module name, which is what is used in the pipeline, the plugin also has a separate
*distribution name* that is defined in the project file (`pyproject.toml`) for the plugin. This name is not directly
used by Sparv but is important for external purposes, such as publishing the plugin on [PyPI](https://pypi.org/). It is
recommended that this name starts with `sparv-` (for discoverability), followed by the same namespace described above.
For example, `sparv-sbx-typo-correction`. Ideally, this name should also be used for the directory containing the plugin
and any version control repository hosting it (e.g., GitHub), ensuring consistency across all references.

## Plugin Structure

A typical plugin structure looks like this:

```text
sparv-sbx-uppercase/
├── sbx_uppercase
│   ├── uppercase.py
│   └── __init__.py
├── LICENSE
├── pyproject.toml
└── README.md
```

In this example, `sparv-sbx-uppercase` is the root directory of the plugin project, which also serves as the
distribution name (used for packaging and publishing). The `sbx_uppercase` directory inside it is the Python package
containing the actual module code, and its name (`sbx_uppercase`) is also the Sparv module name, which is used when
referencing the module in the Sparv pipeline.

The `uppercase.py` file contains the [module code](#module-code) for the Sparv processors, while the mandatory
[`__init__.py` file](#__init__py) is used to make the processors discoverable by Sparv.

The [project file](#pyprojecttoml) `pyproject.toml` in the root directory contains metadata about the plugin (though
this metadata is not directly used by Sparv). It is what makes the plugin installable.

While the `README.md` and `LICENSE` files are not strictly necessary for the plugin to work, we strongly recommend
including them if you plan to publish your plugin.

## pyproject.toml

The `pyproject.toml` file is required to install a plugin and connect it to Sparv. Here is a minimal
example, taken from the [Sparv plugin template](https://github.com/spraakbanken/sparv-plugin-template):

```toml title="pyproject.toml"
[project]
name = "sparv-sbx-uppercase"
version = "0.1.0"
description = "Uppercase converter (example plug-in for Sparv)"
readme = "README.md"
license = "MIT"
dependencies = [
    "sparv~=5.0"
]
entry-points."sparv.plugin" = { sbx_uppercase = "sbx_uppercase" }
```

Ensure there is a `sparv.plugin` entry point (the last line above) that points to the package directory containing the
code, as this is how Sparv discovers the plugin. It is also advisable to add `sparv` to the list of dependencies,
specifying the major version of Sparv the plugin is developed for. `"sparv~=5.0"` under `dependencies` means the plugin
is compatible with any version of Sparv 5, but not with Sparv 4 or Sparv 6.

For more information about the `pyproject.toml` file, check the [Python Packaging User
Guide](https://packaging.python.org/en/latest/specifications/declaring-project-metadata/).

## \_\_init\_\_.py

Each Sparv module requires an [`__init__.py`](https://docs.python.org/3/reference/import.html#regular-packages) file,
which is essential for Sparv to register the module. It is important that this file imports all the Python scripts
containing your decorated Sparv functions.

The `__init__.py` file must include a short (one sentence) description of the module. This description will appear when
running the `sparv modules` command. You can provide this description using the `__description__` variable or as a
docstring. In the example below, both methods are shown, but only one is necessary. If both are present, the
`__description__` value takes precedence.

A longer description can be included by adding additional lines, separated from the first line by a blank line. Only the
first line will be shown in space-limited contexts, such as when running `sparv modules`. The full description will
appear when running `sparv modules modulename`.

Below is an example of an `__init__.py` file:

```python title="__init__.py"
"""Example of a Sparv annotator that converts tokens to uppercase."""

from . import uppercase

__description__ = "Example of a Sparv annotator that converts tokens to uppercase."
```

Additionally, the `__init__.py` file can include a list of languages that the module supports, and module-wide
[configuration parameters](#config-parameters) can be declared. This is explained in more detail in later sections.

## Module Code

A Sparv module is a Python package that contains at least one Python function using [Sparv
decorators](sparv-decorators.md) and [Sparv classes](sparv-classes.md). You can also use various [Sparv
utilities](utilities.md) for common tasks.

Sparv classes describe the dependencies and outputs of your module, and define how it interacts with other modules in
the Sparv pipeline. Here is an example from the [Sparv plugin
template](https://github.com/spraakbanken/sparv-plugin-template):

```python title="uppercase.py"
from sparv.api import Annotation, Output, annotator

@annotator("Convert every word to uppercase.")
def uppercase(
    word: Annotation = Annotation("<token:word>"),
    out: Output = Output("<token>:sbx_uppercase.upper", description="Uppercase version of the word")
):
    """Convert to uppercase."""
    out.write([val.upper() for val in word.read()])
```

In this script, we import the classes `Annotation`, `Output`, and the `annotator` decorator from `sparv.api`.

!!! warning "Important"

    Always import from `sparv.api`—other sub-packages like `sparv.core` are for internal use and may change without
    notice.

The `@annotator` decorator marks the `uppercase` function as an annotator, which means it can produce one or more
annotations. The first argument to the decorator is a description, which is shown in help texts (for example, when
running `sparv modules`). Just like the description in the `__init__.py` file, this description should be short (usually
a single sentence), but can include a longer description separated from the first line by a blank line.

The function parameters define how the processor interacts with the rest of the pipeline: what it needs as input and
what it produces as output. Both **type hints** and **default values** are required for the parameters. The type hints
merely indicate the kind of parameter, while the default values specify the actual dependencies and outputs. The default
values are almost always instances of Sparv classes, such as `Annotation` or `Output`.

> [!NOTE]
>
> The type hints and the default values are in most cases the same, except for configuration parameters. For parameters
> that read config variables, the default value uses the `Config` class, while the type hint is a standard Python type
> such as `str`, `int`, or `bool`, indicating the expected type of the configuration value.

In the example above, the `uppercase` function has two parameters: `word` and `out`. The `word` parameter is of type
`Annotation`, which means it expects an annotation as input. The `out` parameter is of type `Output`, indicating that
the function will produce an output annotation. The default values for these parameters are instances of the
`Annotation` and `Output` classes, respectively. The `Annotation("<token:word>")` specifies that the function requires
the `<token:word>` annotation as input, while `Output("<token>:sbx_uppercase.upper")` specifies that the function will
produce the `<token>:sbx_uppercase.upper` annotation as output.

For every `Output` parameter, make sure to include a short description of the output annotation, one sentence long, as
shown in the example.

Sparv functions are not meant to be called directly by you or by other Sparv functions. Instead, they are registered
with the Sparv pipeline when the module is imported. Sparv then calls them as needed, based on the pipeline's dependency
graph. When you run Sparv, it automatically determines which functions to run to produce the outputs you request,
resolving all dependencies for you.

!!! warning "Important"

    If your module relies on additional libraries beyond Sparv’s built-in dependencies, especially large or slow-loading
    ones (for example, `torch`), import them inside the functions that actually use them rather than at the module level.
    This prevents unnecessary delays in Sparv’s startup time when your module is not in use, since every extra library
    import contributes to startup overhead.

For more details about the `annotator` decorator and other Sparv decorators, refer to the [Sparv
decorators](sparv-decorators.md) page.

## Reading and Writing Files

Sparv classes such as `Annotation` and `Output` provide built-in methods for reading and writing files, as seen with
`word.read()` and `out.write()` in the example above. It is crucial that a Sparv module uses these methods exclusively
for file operations. This practice ensures that files are correctly placed within the file structure, making them
accessible to other modules. Additionally, these methods handle Sparv's internal data format properly.

## Logging

To log messages from Sparv modules, use [Python's logging library](https://docs.python.org/3.6/library/logging.html).
Utilize the provided `get_logger` function to obtain a logger instance for your module. This function handles importing
the logging library and sets the correct module name in the log output:

```python
from sparv.api import get_logger
logger = get_logger(__name__)

logger.error("An error was encountered!")
```

You can use any of the official [Python logging levels](https://docs.python.org/3.6/library/logging.html#levels).

By default, Sparv writes log output with the level `WARNING` and higher to the terminal. Users can change the log level
with the `--log LOGLEVEL` flag, which is supported by most commands. Additionally, users can write log output to a
file using the `--log-to-file LOGLEVEL` flag. The log file will be named with the current date and timestamp and can
be found in the `logs/` directory within the corpus directory.

### Progress Bar

You can add a progress bar to individual annotators using the custom `progress()` logging method. Initialize the
progress bar by calling `logger.progress()`, either without arguments or by supplying a total value:
`logger.progress(total=50)`. A progress bar initialized without a total will display an indeterminate
progress bar, which is useful when the total number of items to process is unknown at the start. A total value can be
set later by calling `logger.progress(total=50)` again. It is also possible to change the total value later.

Once the total is set, update the progress by calling `logger.progress()` again. If no argument is supplied, the
progress advances by 1. To advance by a different amount, use the `advance=` keyword argument. To set the progress to a
specific number, call the method with that number as the argument. Here are some examples:

```python
from sparv.api import get_logger
logger = get_logger(__name__)

# Initialize progress bar with no known total
logger.progress()

# Initialize bar with known total
logger.progress(total=50)

# Advance progress by 1
logger.progress()

# Advance progress by 2
logger.progress(advance=2)

# Set progress to 5
logger.progress(5)
```

## Error Messages

To notify users of critical errors that prevent a processor from continuing, use the [SparvErrorMessage
class](utilities.md#sparverrormessage). This class raises an exception, halts the current Sparv process, and displays a
user-friendly error message without showing the usual Python traceback.

```python
from sparv.api import SparvErrorMessage

@annotator("Convert every word to uppercase")
def uppercase(word: Annotation = Annotation("<token:word>"),
              out: Output = Output("<token>:sbx_uppercase.upper", description="Uppercase version of the word"),
              important_config_variable: str = Config("sbx_uppercase.some_setting")):
    """Convert to uppercase."""
    # Ensure important_config_variable is set by the user
    if not important_config_variable:
        raise SparvErrorMessage("Please set the config variable 'sbx_uppercase.some_setting'!")
    ...
```

## Config Parameters

By declaring configuration parameters, you can make your Sparv module customizable by users. This allows users to
set keys in the [corpus config file](../user-manual/corpus-configuration.md) to control how your module behaves.

Config parameters are declared using the `Config` class from `sparv.api`. They can be declared either by using the
`config` argument in the [Sparv decorators](sparv-decorators.md), or by using the `__config__` global variable
in the module's `__init__.py` file. Both methods are equivalent, but for parameters that are used by multiple
functions, it is recommended to declare them in the `__init__.py` file. A configuration parameter can be declared
in the same decorator as the function using it, or in a different decorator, or even in a different module.

Whichever method you choose, the configuration parameters are declared as a list of `Config` objects. Each `Config`
object specifies the name of the parameter, a description, and optionally a default value. There are also several
parameters for specifying constraints on the configuration value, described in the Config Validation section below. The
description is mandatory, and will be visible in the help texts when running `sparv modules`.

Once declared, these configuration parameters can be referenced in the function signatures of Sparv processors, either
by using the `Config` class, or by using a special placeholder syntax in other Sparv class parameters. This placeholder
syntax uses square brackets to refer to a configuration key, for example: `Model("[wsd.sense_model]")`. When Sparv
runs the processor, it will automatically substitute the value of the configuration parameter `wsd.sense_model` in
place of the placeholder. This can be used in any Sparv class except `Config`, and the placeholder can also be part of
a larger string, such as `Model("wsd/[wsd.sense_model]")`. Which way you choose to reference the configuration depends
on whether you want a Sparv class or simply the value of the configuration parameter.

The following example demonstrates how to declare and use configuration parameters in a Sparv processor, showing both
ways of referencing configuration values:

```python
from sparv.api import Binary, Config, Model, annotator

@annotator(
    "Word sense disambiguation",
    config=[
        Config("wsd.sense_model", default="wsd/ALL_512_128_w10_A2_140403_ctx1.bin", description="Path to sense model"),
        Config("wsd.jar", default="wsd/saldowsd.jar", description="Path name of the executable .jar file"),
        Config("wsd.default_prob", default=-1.0, description="Default value for unanalyzed senses"),
        ...
    ],
)
def annotate(
    wsdjar: Binary = Binary("[wsd.jar]"),
    sense_model: Model = Model("[wsd.sense_model]"),
    default_prob: float = Config("wsd.default_prob"),
    ...
):
    ...
```

Note that when using the `Config` class, the type hint in the function signature should be a standard Python type
indicating the expected type of the configuration value.

Here is an example of how to declare configuration parameters in the module's `__init__.py` file:

```python title="__init__.py"
__config__ = [
    Config("korp.remote_host", description="Remote host to install to"),
    Config("korp.mysql_dbname", description="Name of database where Korp data will be stored")
]
```

> [!NOTE]
>
> The `Config` class is used both for declaring configuration parameters and for accessing them in function signatures,
> depending on the context. When used in a function signature, only the name of the parameter is used, and any other
> arguments (like `default` or `description`) are ignored.

Like all input to your processors, configuration parameters are passed to the function as arguments. Never try to read
the configuration file directly. The Sparv core is responsible for reading and passing configuration values to modules,
ensuring the [config hierarchy](#config-hierarchy) and [config inheritance](#config-inheritance) are respected.

### Config Validation

The `Config` class includes several parameters for validating configuration values. Beyond specifying the data type
(e.g., `int`, `float`, `str`, `bool`), you can define a list of valid values, a range of values, or a regular expression
pattern that the value must match. For a full list of available parameters, refer to the [Sparv
Classes](sparv-classes.md#sparv.api.classes.Config) page.

It is recommended to at least specify the data type for each configuration parameter. This may be enforced in future
versions of Sparv.

The validation parameters are also used to generate the Sparv configuration JSON schema, which can be used to validate
corpus configuration files outside of Sparv.

### Config Hierarchy

When Sparv processes the corpus configuration, it determines the value of each configuration parameter by searching in
the following order of precedence (from highest to lowest):

1. The user's corpus configuration file
2. Any parent corpus configuration file(s)
3. The default configuration file in the [Sparv data
   directory](../user-manual/installation-and-setup.md#setting-up-sparv)
4. The default value specified when declaring the configuration parameter

A value found in a higher-priority source overrides any value from a lower-priority source.

### Config Inheritance

Sparv importers and exporters inherit part of their configuration from the general config categories `import` and
`export`. For example, when setting `export.annotations` as follows:

```yaml
export:
    annotations:
        - <token>:hunpos.pos
        - <token>:saldo.baseform
```

the config parameter `csv_export.annotations` for the CSV exporter will automatically be set to the same value, unless
explicitly overridden in the corpus config file:

```yaml
csv_export:
    annotations:
        - <token>:hunpos.pos
        - <token>:saldo.baseform
```

It is highly recommended to use the same configuration key names for importers and exporters as those used by the
`import` and `export` categories, in order to make use of this inheritance. When using these key names, ensure that the
expected value types are compatible between your importer/exporter and the corresponding `import` or `export` category.

Below is a list of existing configuration keys for the `import` and `export` categories that are inherited by importers
and exporters:

#### Inheritable Configuration Keys for `import`

| Config Key          | Description                                                                 |
|:--------------------|:----------------------------------------------------------------------------|
| `text_annotation`   | The annotation representing one text. Any text-level annotations will be attached to this annotation. |
| `encoding`          | Encoding of the source file. Defaults to UTF-8.                             |
| `keep_control_chars`| Set to True if control characters should not be removed from the text.      |
| `keep_unassigned_chars` | Set to True if unassigned characters should not be removed from the text. |
| `normalize`         | Normalize input using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'. |
| `source_dir`        | The path to the directory containing the source files relative to the corpus directory. |

#### Inheritable Configuration Keys for `export`

| Config Key                | Description                                                                 |
|:--------------------------|:----------------------------------------------------------------------------|
| `default`                 | Exports to create by default when running 'sparv run'.                      |
| `source_annotations`      | List of annotations from the source file to be kept.                        |
| `annotations`             | List of automatic annotations to include in the export.                     |
| `word`                    | The token strings to be included in the export.                             |
| `remove_module_namespaces`| Set to False if module namespaces should be kept in the export.             |
| `sparv_namespace`         | A string representing the namespace to be added to all annotations created by Sparv. |
| `source_namespace`        | A string representing the namespace to be added to all annotations present in the source. |
| `scramble_on`             | Chunk to scramble the XML export on.                                        |

## Languages and Varieties

To restrict an annotator, exporter, installer, or model builder to specific languages, use the `language` parameter in
the decorator and provide a list of ISO 639-3 language codes:

```python
@annotator("Convert every word to uppercase", language=["swe", "eng"])
def ...
```

These Sparv functions will only be available if one of their specified languages matches the language in the [corpus
config file](../user-manual/corpus-configuration.md). If no language codes are specified, the function will be available
for all languages.

To restrict an entire module to specific languages, assign a list of language codes to the `__language__` variable in
the module's `__init__.py` file. This will restrict all functions in the module to the specified languages.

Sparv also supports language varieties, which is useful for functions targeting specific varieties of a language. For
example, Sparv has annotators for historical Swedish from the 1800s, marked with the language code `swe-1800`. Here,
`swe` is the ISO 639-3 code for Swedish, and `1800` is an arbitrary string representing the variety. Functions marked
with `swe-1800` will be available for corpora with the following configuration:

```yaml title="config.yaml"
metadata:
    language: "swe"
    variety: "1800"
```

Functions marked only with `swe` will be available for all varieties of Swedish, including `swe-1800`.

## Installing and Uninstalling Plugins

Installation and uninstallation of Sparv plugins are handled by the `sparv plugins` command. How to use this command is
described in the [Installation and Setup](../user-manual/installation-and-setup.md#installing-and-uninstalling-plugins)
section of the user manual.

> [!TIP]
>
> To make development easier, you can install a plugin in **editable mode**. This means that changes to the plugin code
> will immediately be available to Sparv without having to reinstall the plugin. This is done by using the `-e` flag
> when installing from a local directory:
>
> ```sh
> sparv plugins install -e ./sparv-sbx-uppercase
> ```

## Advanced Features

This section covers some advanced features that can be useful, but are not required for most Sparv plugins.

### Wildcards

Some processors use wildcards in the names of their input and output annotations, allowing them to produce various
annotations with different wildcard values. Wildcards are placeholders that can be replaced with specific values when
referenced in the pipeline. For example, the annotator `misc.number_by_position` uses wildcards. Its output is defined
as `Output("{annotation}:misc.number_position")`. Here, the wildcard `{annotation}` can be replaced with any annotation,
and the annotator will generate a new attribute for the spans of that annotation. If a user requests the annotation
`<sentence>:misc.number_position` (by including it in one of the export lists in the corpus configuration), Sparv will
annotate every span of the `<sentence>` annotation with a number attribute. Similarly, requesting
`document:misc.number_position` will add a number attribute to the `document` annotation.

Wildcards are similar to config variables as they provide customization to annotators. However, the main difference is
that a config variable is explicitly set in the corpus configuration, while a wildcard receives its value automatically
when referenced, whether by a user or by another processor in the pipeline.

Wildcards are always enclosed in curly brackets `{}` when referenced in the input or output annotations of the annotator
that produces them. They must also be declared in the `wildcards` argument of the `@annotator` decorator, as shown in
the following example:

```python
@annotator("Number {annotation} by position", wildcards=[Wildcard("annotation", Wildcard.ANNOTATION)])
def number_by_position(
    out: Output = Output("{annotation}:misc.number_position", description="Position of {annotation} within file"),
    chunk: Annotation = Annotation("{annotation}"),
    ...
):
    ...
```

For a wildcard to be meaningful, the same wildcard variable must be used in both the input annotation (typically
`Annotation`) and the output annotation (e.g., `Output`) within the same annotation function.

An annotator can also have multiple wildcards, as demonstrated in the following example:

```python
@annotator(
    "Number {annotation} by relative position within {parent}",
    wildcards=[Wildcard("annotation", Wildcard.ANNOTATION), Wildcard("parent", Wildcard.ANNOTATION)],
)
def number_relative(
    out: Output = Output(
        "{annotation}:misc.number_rel_{parent}", description="Relative position of {annotation} within {parent}"
    ),
    parent: Annotation = Annotation("{parent}"),
    child: Annotation = Annotation("{annotation}"),
    ...
):
    ...
```

The `Wildcard` class is described on the [Sparv Classes](sparv-classes.md) page.

### Function Order

In some cases, you may need to create multiple Sparv functions that generate the same output files (such as annotation
files, export files, or model files). Sparv needs to know the priority of these functions to determine which one to use.
For example, consider two functions, `annotate()` and `annotate_backoff()`, both producing an annotation output called
`mymodule.foo`. Ideally, `mymodule.foo` should be produced by `annotate()`. However, if `annotate()` cannot run (perhaps
because it requires another annotation file `mymodule.bar` that is unavailable for some corpora), you want
`annotate_backoff()` to produce `mymodule.foo` instead.

The priority of functions is specified using the `order` argument in the `@annotator`, `@exporter`, or `@modelbuilder`
decorator. A lower number indicates a higher priority.

```python
@annotator("Create foo annotation", order=1)
def annotate(
    out: Output = Output("mymodule.foo", description="Foo annotation"),
    bar_input: Annotation = Annotation("mymodule.bar")):
    ...


@annotator("Create foo annotation when bar is not available", order=2)
def annotate_backoff(
    out: Output = Output("mymodule.foo", description="Foo annotation"):
    ...
```

### Preloaders

Preloader functions are used by the `sparv preload` command to speed up the annotation process. They work by preloading
the Python module along with models or processes that would otherwise need to be loaded each time the annotator is run.
These preloaded resources are kept in memory for as long as the `sparv preload` process is running, so that subsequent
annotator calls can reuse them without reloading, significantly improving performance for expensive initializations.

A preloader setup has two main parts:

1. A preloader function, which receives the annotator arguments needed to initialize the resource and returns the
    preloaded value (e.g., a loaded model or a started process).
2. A regular annotator, whose decorator tells Sparv how to call the preloader and which parameter should receive the
    returned value.

The preloader function itself should be small and focused on initialization. It takes a subset of the annotator's
arguments, typically things like a `Model`, `Binary`, or configuration value, and returns the loaded model, started
process, or other reusable object.

On the annotator side, three decorator parameters are required:

1. `preloader`: the function to call during `sparv preload`
2. `preloader_params`: the names of the annotator parameters whose values should be passed to the preloader function
3. `preloader_target`: the name of the annotator parameter that should receive the returned preloaded value

The annotator must therefore include an extra parameter with the same name as `preloader_target`. That parameter will
contain the preloaded object when the annotator runs through `sparv preload`. As the preloader is optional, the
annotator should also be able to run without it, so the `preloader_target` parameter should be optional (i.e., have a
default value of `None`).

Here is an example of a preloader function and an annotator that uses it:

```python
from sparv.api import Annotation, Model, Output, annotator


def preloader(model: Model) -> dict:
    """Preload POS model."""
    return load_model(model)


@annotator(
    "Part-of-speech tagging.",
    preloader=preloader,
    preloader_params=["model"],
    preloader_target="model_preloaded",
)
def pos_tag(
    word: Annotation = Annotation("<token:word>"),
    out: Output = Output("<token>:pos.tag", description="Part-of-speech tag"),
    model: Model = Model("pos.model"),
    model_preloaded: dict | None = None,
):
    """Annotate tokens with part-of-speech tags."""
    if model_preloaded:
        model = model_preloaded
    else:
        model = load_model(model)
```

In this example, the preloader function receives the annotator's `model` argument and returns a loaded model. The
annotator decorator then connects the pieces as follows:

1. `preloader=preloader` tells Sparv which function performs the initialization.
2. `preloader_params=["model"]` tells Sparv to pass the annotator's `model` argument to that function.
3. `preloader_target="model_preloaded"` tells Sparv to inject the return value into the annotator parameter named
    `model_preloaded`.

Inside the annotator, `model_preloaded` is optional. If a preloaded model is available, it is reused, otherwise the
annotator loads the model itself. This fallback is what makes the annotator work both with and without `sparv preload`.

When using the `sparv preload` command with this annotator, the preloader function runs once, and every time the
annotator is used, it receives the preloaded model via the `model_preloaded` parameter.

In addition to the required parameters above, there are two optional ones: `preloader_shared` and
`preloader_cleanup`.

`preloader_shared` is a boolean that defaults to `True`. By default, Sparv runs the preloader function once, and if
using `sparv preload` with multiple parallel processes (using the `--processes` flag), they all share the same preloaded
result. Setting `preloader_shared` to `False` makes the preloader function run once per process, which is usually needed
when preloading processes rather than models. To avoid overloading the system, you can limit the number of processes for
a specific preloaded annotator using the [`threads`
section](../user-manual/corpus-configuration.md#limiting-the-number-of-threads) in the corpus configuration file used
for the `sparv preload` command.

`preloader_cleanup` refers to a function that runs after each (preloaded) use of the annotator. This function should
take the same arguments as the preloader function, plus an extra argument for the preloaded value with the same name as
the `preloader_target` parameter in the annotator decorator. It should return the same type of object as the preloader
function, which Sparv will use as the new preloaded value. This is rarely needed but can be useful for preloading
processes that need regular restarting. The cleanup function would track when restarting is needed, call the preloader
function to start a new process, and return it.
