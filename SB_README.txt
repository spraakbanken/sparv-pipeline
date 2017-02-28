Wiki page about Korp & Pipeline:
* https://spraakbanken.gu.se/eng/node/19784

When using git-svn you cannot do rebase with a dirty directory, so
checkout first without the model directory, and then make another
repo only for the models:

    git svn clone -r 150000 --localtime https://svn.spraakdata.gu.se/sb-arkiv/tools/annotate --ignore-paths="^models"
    cd annotate
    git svn clone -r 150000 --localtime https://svn.spraakdata.gu.se/sb-arkiv/tools/annotate/models
