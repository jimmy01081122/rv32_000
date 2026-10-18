# Controlled FMA contraction experiment

Both policies ran on clean source `581ee86f1bd55bc6eff7cc123c660ab94446eb6f` using the same corrected RTL.
UTC run: 2026-10-17T23:49:34.925463+00:00 to 2026-10-18T00:11:05.455630+00:00 (the run began on October 17 UTC and completed October 18).
The context also preserves Asia/Taipei timestamps. Archive date is completion day in UTC.

`off` and `fast` each pass **8/8 native / Spike / DUT**, checking 3,629 native
and 3,629 DUT values per policy against unchanged independent references/tolerances.
Both use `-O3 -fno-fast-math`; only compiler contraction is changed.
RAM is 1 MiB, data latency 1 cycle, extra random delay 0.
All off ROIs retire zero FMA; all fast ROIs retire actual single-precision FMA.

| Kernel | off cycles | fast cycles | off/fast | fast retired FMA |
| --- | ---: | ---: | ---: | ---: |
| fir | 75,326 | 74,311 | 1.013659 | 8,192 |
| iir | 17,653 | 13,523 | 1.305406 | 4,096 |
| fft | 41,929 | 40,867 | 1.025987 | 1,536 |
| pid | 8,782 | 7,248 | 1.211645 | 1,024 |
| gemm | 155,749 | 133,275 | 1.168629 | 15,000 |
| bicg | 24,053 | 23,927 | 1.005266 | 3,192 |
| cholesky | 225,987 | 194,161 | 1.163916 | 10,660 |
| svm | 45,492 | 43,392 | 1.048396 | 4,400 |

Diagnostic geometric means: DSP **1.132501x**, matrix/ML **1.094211x**,
equal-group FP32 **1.113191x**. These ratios compare compiler policies on one CPU;
they do not measure architecture speedup, frequency or PPA. Formal policy/defaults
remain open. [Interpretation and numerical table](../../../FMA_CONTRACTION_REVIEW.md).

Before accepting these runs, a cancellation probe exposed an old RTL precision bug.
The [before context](before/context.json) and [failed raw output](raw/before/dut.txt)
retain that expected failure separately; its tooling was uncommitted but RTL clean.
Commit `25c1dd1` fixes normalization before precision reduction and subnormal packing.
The new [finite qualification](finite/summary.json) passes all **3,400** exact
result/fflags cases on the integer oracle, Spike and DUT, covering four FMA opcodes
and five rounding modes on finite inputs. `finite/vectors.json` and `fma_vectors.h`
retain the exact oracle cases. This does not cover all NaN/Inf inputs or full FP ISA.

Post-fix regressions on the same source: lint/build PASS; directed **18/18**;
Spike commit comparisons **18/18**; [Embench](embench/dut-gate-report.json)
**19/19 native / Spike / DUT**, including ISA/ABI checks. Python numerical and
pairing validators pass 12 controls at the measured commit. A subsequent tool-only
review adds the failed-process/stale-score rejection; all 13 controls pass in
`post-run-driver-tests.txt`, identified by `post-run-tooling-review.json`. Synthetic ROI-profile assertions pass;
[FIR profile invariance](profile-invariance.json) passes for both off and fast
with observer removed. No physical synthesis/STA result was produced for this fix.

## Evidence layout

- `run-context.json`: clean source/tree, simulator/image identities, commands,
  timestamps and exit codes for the complete pipeline.
- `comparison.json`, `off/summary.json`, `fast/summary.json`: source identities,
  commands, ELF/log hashes, numerical checks, ROI cycles and retired FMA counts.
- `fixture-references.json`: identical fixture/header files reused from the
  October 17 qualification. SHA256SUMS also checks those relative external paths.
  The prior archive retains the upstream SVM dataset Apache-2.0 license.
- `source-summary.json`: pinned upstream source identities, unchanged between modes.
- `raw/fp/{off,fast}/<kernel>/{native,dut}.txt`: all emitted values, checksums and
  DUT ROI statistics; adjacent files retain build, attributes, sizes and Spike logs.
- `raw/finite`, `raw/before`, `raw/embench`, `raw/pipeline`: exact original stdout
  bytes, including empty successful logs. Before-fix failures are historical evidence,
  not members of the new pass denominator.
- `log-index.json`: original runtime path to archive path, SHA-256 and byte count.
- `regenerable-artifacts.json`: exact hashes/sizes for ignored binaries, compiler
  stack reports and full disassemblies. They are not checked in. Probe/symbol ELFs
  retain metadata and are not guaranteed byte-identical on rebuild; executed FP
  benchmark ELFs are stripped as recorded in their commands.
- `python-tests.txt`: 12 validator positive/negative controls.

Reproduce from the source commit above after preparing the pinned Docker images:

```bash
make fetch-fp-sources
python3 -m unittest discover -s scripts -p 'test_fp*.py'
make lint sim-build JOBS=4
make compare-fp-contraction JOBS=4
make test diff-test JOBS=4
make qualify-embench-fp-dut JOBS=4
make summarize-embench-fp-dut
```

From this archive directory: `sha256sum -c SHA256SUMS`.
The results apply to provisional daily fixtures; official scores, the AP5B physical
baseline, and the 1.20x/1.10x architecture/area planning goals remain unassessed.
