# Sparv Plugin Development

![Sparv logo](../images/sparv_detailed.png){ align=right .intro-logo } Sparv is a modular text analysis pipeline
designed for linguistic annotation and processing. Its flexible architecture allows users to extend its functionality by
developing custom plugins, making it suitable for a wide range of language technology tasks.

Developing plugins enables you to add new annotation steps or processing modules to the pipeline, integrate external
tools, or customize Sparv for specific languages or domains.

Plugins are Python packages that register new processors (annotators, exporters, etc.) with Sparv. They interact with
the pipeline through a well-defined API and can be distributed and installed independently.

This guide provides an overview of the plugin system and how to create your own plugins.

If you have any questions, problems or suggestions please contact <sb-sparv@svenska.gu.se>.
