#!/bin/bash
#
# A small test and example of using catapult and catalaunch.
#
# Make sure your PYTHONPATH is set correctly to the directory
# above sb, and that the catalaunch binary is in your PATH.
#
# Requires inotifywait, which is in the package inotify-tools:
#
#      pacman -S inotify-tools, or
#      aptitude install inotify-tools
#

rm tmp-test-* -v

N=0
for processes in 1 2
do
    for verbose in True False
    do
        echo "********************************************"
        echo "Running with $processes processes"
        echo "Running with verbose $verbose"

        # Remove old socket file, if it exists
        rm test.sock

        # Start a catapult process in the background. The pid is
        # stored and the process is killed at the end of this loop.
        # If verbose is off, all stdout and stderr should be
        # surpressed, unless scripts throw uncaught errors.
        python -m sb.catapult --socket_path test.sock \
            --processes $processes --verbose $verbose &
        catapult_pid=$!

        # Wait until the socket file is created
        inotifywait -e create .

        # Testing faulty commands. These should not destroy the catapult.
        echo "*** should fail ***"

        # This should send an error
        catalaunch test.sock -m test.silly --error
        catalaunch test.sock -m test.sily

        # Faulty commands
        catalaunch test.sock -m
        catalaunch test.sock -n test.silly
        catalaunch test.sock sillly.py
        catalaunch test.sock
        catalaunch test.sokc
        catalaunch

        # The rest should behave properly.
        echo "*** should succeed ***"

        # Start four silly processes in the background.
        # The argument to catalaunch is a socket file, and then
        # supporting modules with -m or files plus arguments, as the
        # python interpreter.
        catalaunch test.sock -m test.silly --msg 1 & pid1=$!
        catalaunch test.sock -m test.silly --msg 2 & pid2=$!
        catalaunch test.sock silly.py --msg 3 &      pid3=$!
        catalaunch test.sock silly.py --msg 4 &      pid4=$!

        ## Test with running ls with os.system.
        catalaunch test.sock -m test.silly --ls

        # Catalaunch preserves the directory it is launched from
        OLD_PWD=`pwd`
        cd ..
        catalaunch $OLD_PWD/test.sock -m test.silly --ls
        cd $OLD_PWD

        catalaunch test.sock -m test.silly --write \
            --file tmp-test-$N \
            --msg "n:$N processes: $processes verbose: $verbose pwd: `pwd`"
        N=$(( $N + 1 ))
        cd /
        catalaunch $OLD_PWD/test.sock $OLD_PWD/silly.py --write \
            --file $OLD_PWD/tmp-test-$N \
            --msg "n:$N processes: $processes verbose: $verbose pwd: `pwd`"
        N=$(( $N + 1 ))
        cd $OLD_PWD

        # Wait until all silly processes are done
        wait $pid1; wait $pid2; wait $pid3; wait $pid4

        # Kill the catapult
        kill $catapult_pid
        echo "********************************************"
        echo
    done
done

rm test.sock

echo
echo "*** a successful run lists 8 files here:"
for file in $( ls tmp-test-* )
do
    echo -n "$file: "
    cat $file
    echo
    rm $file
done
echo "*** end of test"
