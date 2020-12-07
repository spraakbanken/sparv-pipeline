# Requirements for Input Data
In order for Sparv to be able to process your corpus, please make sure your input data meets the following requirements:

1. Make sure you don't have any manually created directories called `sparv-workdir` or `export` in your corpus directory
   as Sparv will attempt to create and use these.

2. If your corpus is in XML format, make sure your **XML is valid** and that the text to be analysed is actual text (not
   attribute values).

3. Your input documents must use the same file format, same file extension and (if applicable) the same markup.

4. If your corpus is in XML format, make sure you don't have any elements of attributes called "not" as this is a
   reserved keyword in the Sparv pipeline.

5. If your input documents are very large or if your corpus consists of a large amount of really small documents Sparv
   might become quite slow. The recommended size per document lies around 5-10 MB. If your machine has lots of memory,
   processing larger documents may work just fine.
