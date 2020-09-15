
# Writing a Sparv module
- Explain the most important classes and util functions
- List annotators (decorators), their options and what they are used for
- When should you use the SparvError class?

## Importer module

## Exporter module


# Writing Plugins
Writing a Sparv plugin is not much different from writing a Sparv module. The main difference is that the code for a
plugin is not stored together with the core Sparv code. Instead it usually lives in a separate repository. Reasons for
writing new code as a plugin instead of a module could be that the author does not want it to be part of the Sparv core
or that the code cannot be distributed under the same license.

A working sparv plugin is the [sparv-freeling](https://github.com/spraakbanken/sparv-freeling) plugin.

The following is an example of a typical folder structure of a plugin:

    sparv-freeling/
    ├── freeling
    │   ├── freeling.py
    │   ├── __init__.py
    │   └── models.py
    ├── LICENSE
    ├── README.md
    └── setup.py

In the above example the `freeling` folder is basically a Sparv module. The `setup.py` is what really makes this behave
as a plugin. If the `setup.py` is constructed correctly, the plugin code can then be injected into the Sparv pipeline
code using pipx:

    pipx inject sparv-pipeline ./sparv-freeling

Now the plugin functionality should be available and it should be treated just like any other module within the Sparv
pipeline.
