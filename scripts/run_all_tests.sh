#!/bin/bash
set -euo pipefail

# scripts/run_all_tests.sh — Run regression suite on rv32_ooo_sim

TEST_DIR="build/tests"
SIM_EXE="build/sim/rv32_ooo_sim"

if [ ! -f "$SIM_EXE" ]; then
    echo "Error: $SIM_EXE not found. Run 'make sim-build' first."
    exit 1
fi

echo "============================================================"
echo "      RV32 Out-of-Order Core — Test Regression Suite        "
echo "============================================================"

PASS_COUNT=0
FAIL_COUNT=0
TOTAL_COUNT=0

for elf in "$TEST_DIR"/*.elf; do
    [ -f "$elf" ] || continue
    test_name=$(basename "$elf" .elf)
    TOTAL_COUNT=$((TOTAL_COUNT + 1))

    echo -n "  Testing [$test_name] ... "
    if "$SIM_EXE" "+elf=$elf" > "build/tests/${test_name}.log" 2>&1; then
        echo -e "\033[0;32m[PASS]\033[0m"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "\033[0;31m[FAIL]\033[0m"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "    --- Failure log: ---"
        tail -n 15 "build/tests/${test_name}.log" | sed 's/^/    /'
    fi
done

echo "============================================================"
echo " Regression Summary: $PASS_COUNT / $TOTAL_COUNT passed ($FAIL_COUNT failed)"
echo "============================================================"

if [ "$FAIL_COUNT" -ne 0 ]; then
    exit 1
fi
exit 0
