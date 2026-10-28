STATUS=ERROR
sby -f check.q.sby > /dev/null && STATUS=$(awk '{print $1}' check.q/status)
echo $STATUS > status
case $STATUS in
    PASS)
        echo "Proved equivalence of partition 'check.q' using strategy 'pdr'"
    ;;
    FAIL)
        echo "Could not prove equivalence of partition 'check.q' using strategy 'pdr': partitions not equivalent"
    ;;
    UNKNOWN)
        echo "Could not prove equivalence of partition 'check.q' using strategy 'pdr': equivalence unknown"
    ;;
    TIMEOUT)
        echo "Could not prove equivalence of partition 'check.q' using strategy 'pdr': timeout"
    ;;
    *)
        cat check.q/ERROR 2> /dev/null
        echo "Execution of strategy 'pdr' on partition 'check.q' encountered an error."
        echo "More details can be found in '/workspace/build/experiments/fpu-mapping-v1/formal-controls/positive-pdr/strategies/check.q/pdr/check.q/logfile.txt'."
        exit 1
    ;;
esac
exit 0

