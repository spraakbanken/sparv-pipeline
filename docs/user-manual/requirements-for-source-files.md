# Requirements for Source Files
In order for Sparv to be able to process your corpus, please make sure your source files meet the following
requirements:

1. Make sure you don't have any manually created directories called `sparv-workdir` or `export` in your corpus directory
   as Sparv will attempt to create and use these.

2. If your corpus is in XML format, make sure your **XML is valid** and that the text to be analysed is actual text (not
   attribute values).

3. Your source documents must all use the same file format, same file extension and (if applicable) the same markup.

4. If your corpus is in XML format, make sure you don't have any elements or attributes called "not" as this is a
   reserved keyword in the Sparv pipeline.

5. If your source documents are very large or if your corpus consists of a large number of tiny documents, Sparv
   may become quite slow. Very large files may also lead to memory problems. Try keeping the maximum file size per
   document around 5-10 MB, and in the case of many tiny files, combining them into larger files if possible.
   If your machine has a lot of memory, processing larger documents may work just fine.
