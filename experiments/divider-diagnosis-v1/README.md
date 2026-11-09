# Read-only integer DIV/REM diagnosis

The November 8 recommendation authorized operand/latency diagnosis separately
from the A+B implementation. No divider RTL has changed.

The observer relinks only the host harness against B's retained generated model
and runtime objects. All 27 retained profiles select exactly six workloads with
retired DIV/DIVU/REM/REMU instructions. Each has an observer off/on pair checked
against its accepted profile, memory audit and result log. Forty-eight real
instruction controls compare original/off/on ordered traces, exact results,
operand categories and both 1-cycle and 33-cycle latencies.

All six workload pairs pass. Every completed measured operation takes 33 cycles
from request acceptance to first valid and completion grant. The divider has
highest completion priority; no completion arbitration stall was observed.
Zero/overflow controls take one cycle. These are paired unit-interface latencies,
not the older per-PC ROB-head wait averages.

| B workload | Accepted issues | Retired DIV/REM | New early-result operand share |
| --- | ---: | ---: | ---: |
| cubic | 22,960 | 22,960 | 32.23% |
| nbody | 8,120 | 8,120 | 0% |
| nettle-aes | 4,602 | 4,056 | 100% |
| st | 21,320 | 21,320 | 0% |
| ud | 31,038 | 31,038 | 85.71% |
| wikisort | 9,640 | 9,636 | 2.53% |

The last column counts disjoint operand categories in priority order: existing
zero/overflow paths, absolute divisor one, absolute dividend below divisor,
then remaining power-of-two divisors. It is a share of **accepted issues**, not
saved CPU cycles. `nettle-aes` cancels 546 issued operations on flush; `wikisort`
cancels four. All other issued operations complete inside the measured region.

Early results look promising for `ud` and part of `cubic`; they offer little to
`st`, `nbody` or `wikisort`. Leading-zero skipping and two quotient bits per
iteration remain separate alternatives. Their area, timing and CPU cycle benefit
require independently selected RTL experiments. Leading-zero opportunities
overlap early-result categories and must not be added to them. None of the FP32
eight contains retired integer DIV/REM in the fixed corpus.

`review.py` rechecks the exact recorded sources, objects, outputs and controls.
The original run's source snapshot remains under the archived `source/` tree;
the tracked runner changes only repository-root discovery for its new location.
