Wiki page about Korp & Pipeline:
* https://spraakbanken.gu.se/eng/node/19784
* Installation: https://spraakbanken.gu.se/swe/forskning/infrastruktur/sparv/distribution/importkedja

Extracting hunpos binaries:

    curl https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/hunpos/hunpos-1.0-linux.tgz | tar xz

Vowpal wabbit:

    git clone https://github.com/JohnLangford/vowpal_wabbit.git --depth 1
    cd vowpal_wabbit
    sudo make install -j4

When using git-svn you cannot do rebase with a dirty directory, and
the models directory will become dirty, so checkout without models
and then make another repo only for the models:

    git svn clone -r 150000 --localtime https://svn.spraakdata.gu.se/sb-arkiv/tools/annotate --ignore-paths="^models"
    cd annotate
    svn co https://svn.spraakdata.gu.se/sb-arkiv/tools/annotate/models
