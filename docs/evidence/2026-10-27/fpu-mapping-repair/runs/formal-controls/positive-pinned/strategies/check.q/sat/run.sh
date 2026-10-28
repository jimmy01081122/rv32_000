yosys -ql run.log run.ys
if grep "SAT temporal induction proof finished - model found for base case: FAIL!" run.log > /dev/null ; then
	echo FAIL > status
	echo "Could not prove equivalence of partition 'check.q' using strategy 'sat'"
elif grep "Reached maximum number of time steps -> proof failed." run.log > /dev/null ; then
	echo UNKNOWN > status
	echo "Could not prove equivalence of partition 'check.q' using strategy 'sat'"
elif grep "Induction step proven: SUCCESS!" run.log > /dev/null ; then
	echo PASS > status
	echo "Proved equivalence of partition 'check.q' using strategy 'sat'"
else
	echo ERROR > status
	echo "Execution of strategy 'sat' on partition 'check.q' encountered an error.
Details can be found in '/workspace/build/experiments/fpu-mapping-v1/formal-controls/positive-pinned/strategies/check.q/sat/run.log'."
	exit 1
fi
exit 0

