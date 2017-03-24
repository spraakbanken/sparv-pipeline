#!/usr/bin/env bash
# Script for distribution of Sparv pipeline and catapult

# Distributes two versions: with MIT license and with AGPL license
# The version with MIT license removes all references to freeling.
# This requires that the affected code lines are marked with a "FreeLing" comment.

# user fksparv cannot access SVN repo :(
USER=
if [ -z ${USER} ]; then echo "Please set variable USER!"&& exit 1; fi

DATE=`date +%Y-%m-%d`
# Extract version number from first line in file 'VERSION'
line=$(head -n 1 VERSION)
VERSION=${line#"version: "}
DIR_MIT=sparv_backend\_$VERSION\_MIT\_$DATE
DIR_AGPL=sparv_backend\_$VERSION\_AGPL\_$DATE

# export tools/annotate and catapult & zip content
echo -e "Distributing current version under MIT license!\n"
ssh $USER@k2.spraakdata.gu.se "cd /export/htdocs_sb/pub/sparv.dist/sparv_pipeline;
if [ -f $DIR_MIT.zip ]; then echo -e 'File $DIR_MIT.zip already exists!\n'; exit; fi;
mkdir $DIR_MIT && cd $DIR_MIT;
echo 'Exporting sources from SVN...';
svn export https://svn.spraakdata.gu.se/sb-arkiv/tools/annotate >/dev/null;
svn export https://svn.spraakdata.gu.se/repos/sparv/catapult >/dev/null;
echo 'Cleaning up...';
rm annotate/makefiles/Makefile.config;
mv annotate/makefiles/Makefile.config_default annotate/makefiles/Makefile.config;
mv annotate/VERSION VERSION;
mv annotate/MIT.license MIT.license;
rm annotate/AGPL.license;
rm annotate/distribute.sh;
mv annotate/README.txt README.txt;
rm annotate/SB_README.txt;
rm annotate/models/saldom.xml;
rm annotate/models/saldo.pickle;
rm annotate/models/saldo.compound.pickle;
rm annotate/models/hunpos.saldo.suc-tags.morphtable;
rm annotate/models/stats.pickle;
rm annotate/models/bettertokenizer.sv.saldo-tokens;
echo 'Removing references to Freeling';
rm annotate/python/sb/freeling.py;
rm -rf annotate/models/freeling;
rm annotate/models/treetagger/*;
rm annotate/bin/treetagger/*;
rm annotate/bin/word_alignment/*;
for f in \$(find ./annotate/makefiles -type f); do sed -i '/# FreeLing/d' \$f; done;
for f in \$(find ./annotate/python -type f); do sed -i '/FreeLing/d' \$f; done;

echo 'zipping files...';
cd ..;
zip -rq $DIR_MIT.zip $DIR_MIT;
rm -r $DIR_MIT;
if [ -f $DIR_MIT.zip ]; then echo -e 'Distribution with MIT license successful!\n'; else echo -e 'Something went wrong...\n'; fi;"


# export tools/annotate and catapult & zip content
echo -e "Distributing current version under AGPL license!\n"
ssh $USER@k2.spraakdata.gu.se "cd /export/htdocs_sb/pub/sparv.dist/sparv_pipeline;
if [ -f $DIR_AGPL.zip ]; then echo -e 'File $DIR_AGPL.zip already exists!\n'; exit; fi;
mkdir $DIR_AGPL && cd $DIR_AGPL;
echo 'Exporting sources from SVN...';
svn export https://svn.spraakdata.gu.se/sb-arkiv/tools/annotate >/dev/null;
svn export https://svn.spraakdata.gu.se/repos/sparv/catapult >/dev/null;
echo 'Cleaning up...';
rm annotate/makefiles/Makefile.config;
mv annotate/makefiles/Makefile.config_default annotate/makefiles/Makefile.config;
mv annotate/VERSION VERSION;
rm annotate/MIT.license;
mv annotate/AGPL.license AGPL.license;
rm annotate/distribute.sh;
mv annotate/README.txt README.txt;
rm annotate/SB_README.txt;
rm annotate/models/saldom.xml;
rm annotate/models/saldo.pickle;
rm annotate/models/saldo.compound.pickle;
rm annotate/models/hunpos.saldo.suc-tags.morphtable;
rm annotate/models/stats.pickle;
rm annotate/models/bettertokenizer.sv.saldo-tokens;
rm annotate/models/freeling/*;
rm annotate/models/treetagger/*;
rm annotate/bin/treetagger/*;
rm annotate/bin/word_alignment/*;

echo 'zipping files...';
cd ..;
zip -rq $DIR_AGPL.zip $DIR_AGPL;
rm -r $DIR_AGPL;
if [ -f $DIR_AGPL.zip ]; then echo -e 'Distribution with AGPL license successful!\n'; else echo -e 'Something went wrong...\n'; fi;"
