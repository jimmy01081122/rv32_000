# Historical phase reports

These are archived research records, not fresh results for the current checkout.
Use [STATUS.md](../docs/STATUS.md) and the [session handoff](../docs/SESSION_HANDOFF.md)
for current evidence. Original report bodies are retained so numerical claims,
source revisions and assumptions can be audited rather than silently rewritten.

| Report(s) | Historical topic |
| --- | --- |
| [AP0](AP0_ASAP7_BASELINE.md), [AP0.1](AP0_1_ASAP7_REBASELINE.md) | Initial ASAP7 characterization and rebaseline |
| [AP1A artifacts](ap1a_operand_register) | Operand-register synthesis/constraint evidence |
| [AP2B](ap2b_signoff_report.md), [AP2C](ap2c_signoff_report.md) | Integer execution/timing work |
| [AP3A1](ap3a1_signoff_report.md), [AP3A2](ap3a2_signoff_report.md), [AP3B](ap3b_signoff_report.md) | FP execution boundaries and timing |
| [AP4A](ap4a_attribution_report.md), [AP4B](ap4b_signoff_report.md), [AP4F](ap4f_signoff_report.md) | FP path attribution and unit restructuring |
| [AP5A](ap5a_signoff_report.md) | Historical clock/LSU path characterization before AP5B |

## Interpretation limits

- A phase's original "signoff" label refers to its historical checks; it is not
  evidence that the current RTL is fully verified or physically closed.
- AP5A reports internal Fmax 175.69 MHz and a system estimate of 153.18 MHz at
  its 6 ns run. REG2OUT WNS is -528.19 ps, so that run did not close all interfaces.
- The existing STA helper uses FF libraries and global-route parasitic estimates;
  the current ORFS config skips detailed routing. Audit the exact raw artifacts
  before interpreting historical "post-route" or full-closure language.
- Power reports lack a demonstrated workload-activity methodology in the helper.
  They are not measured silicon power or validated workload energy.
- Historical ACT4 58/58 and Embench 14/14 results refer to subsets; neither is
  complete RV32IMF verification or the proposed 19-workload Embench baseline.
- CoreMark iterations, compiler flags and declared clock differ between runs.
  A 1 MHz reporting convention cannot establish a 10-second run at a higher
  claimed implementation frequency.
- Source, constraints and benchmark configurations must match before computing
  a before/after speedup. Current AP5B has no new physical report in this session.

Raw result directories and archives remain in place. New experiments must create
their own revision/configuration-keyed evidence and update the current status.
