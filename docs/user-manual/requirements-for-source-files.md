# Requirements for Source Files
In order for Sparv to be able to process your corpus, please make sure your source files meet the following
requirements:

1. Make sure you don't have any manually created directories called `sparv-workdir` or `export` in your corpus directory
   as Sparv will attempt to create and use these.

2. If your corpus is in XML format, make sure your **XML is valid** and that the text to be analysed is actual text (not
   attribute values).

3. Your source files must all use the same file format, same file extension and (if applicable) the same markup.

4. If your source files are very large or if your corpus consists of a large number of tiny files, Sparv
   may become quite slow. Very large files may also lead to memory problems. Try keeping the maximum file size per
   file around 5-10 MB, and in the case of many tiny files, combining them into larger files if possible.
   If your machine has a lot of memory, processing larger files may work just fine.
