#!/bin/bash
#
# Test and example use of membranes
#
# Make sure your PYTHONPATH is set correctly to the directory above sb
#
# There is a race condition when starting a server: it takes a short
# ammount of time before it starts queueing requests, and during this
# time clients can get 'Connection refused'. This should not be a
# problem in practice as the server can be started well in advance.

run='python -m test.membrane_example'
address=http://localhost:8051

for extendable in false true
do
    echo "Starting a square server on localhost:8051 with extendable=$extendable"
    $run --square_server --value 1 --width 3 --extendable $extendable &
    pid=$!

    echo "Requests 1 2 3 4, without extendable, the 4th should return None"
    for i in $(seq 1 4)
    do
        $run --square_test --i $i --address $address
    done

    echo "Killing server"
    kill $pid
done

echo "Using the same function without a server"
for i in $(seq 1 4)
do
    $run --square_test --i $i
done

echo "Serving two membranes simultaneously"
$run --multiserve &
pid=$!

echo "Querying the multiserver"
echo "    First call 1..4"
$run --fancy_arguments_test --lower 1 --upper 4 --name Clementz --address $address/fancy_arguments
echo "    First call 1..5"
$run --fancy_arguments_test --lower 1 --upper 5 --name Aurora   --address $address/fancy_arguments

echo "    Requerying 1..4"
$run --fancy_arguments_test --lower 1 --upper 4 --name Vanja    --address $address/fancy_arguments
echo "    Requerying 1..5"
$run --fancy_arguments_test --lower 1 --upper 5 --name Aurora   --address $address/fancy_arguments

echo "    5 should not load here"
$run --square_test --i 5 --address $address/square

echo "    15 needs to be loaded"
$run --square_test --i 15 --address $address/square

echo "Testing that request are queued (no parallelism support)"
$run --square_test --i 1 --address $address/square & pid1=$!
$run --square_test --i 2 --address $address/square & pid2=$!
$run --square_test --i 3 --address $address/square & pid3=$!
$run --square_test --i 4 --address $address/square & pid4=$!

wait $pid1; wait $pid2; wait $pid3; wait $pid4

echo "Testing local and server working directories"
echo "membrane, server and local cwds should all match up"

cd ..;    $run --print_cwd --address $address/print_cwd
cd ..;    $run --print_cwd --address $address/print_cwd
cd /;     $run --print_cwd --address $address/print_cwd
cd /usr;  $run --print_cwd --address $address/print_cwd
cd /home; $run --print_cwd --address $address/print_cwd

echo "Killing server"
kill $pid
