# Balanced FP32 provisional numerical qualification

Clean source commit: `df97854c719014df862d6d6df450d02fe0cee756`.
UTC: 2026-10-17T13:46:44.504334+00:00 to 2026-10-17T13:48:02.023567+00:00. Native / Spike / DUT: **8/8 each passed**.
All 3,629 emitted results per native/DUT run were checked independently on the host. All eight host/DUT output checksums agree.

Inputs, expected values, provisional tolerances and reference methods are in each `cases/<name>/fixture.json`; exact compiled binary32 arrays are in `fp_fixture.h`.
Build policy: GCC 15.2, RV32IMF/ilp32f, `-O3 -ffp-contract=off -fno-fast-math`, scalar upstream kernels. FFT alone uses upstream `NDEBUG` to disable optional stderr logging; allocation attempts still fail and numerical checks remain enabled.
One initialized invocation is timed per case; setup, output validation and streaming equivalence checks are outside the ROI. No warmup policy, timer-overhead threshold, memory service or physical contract has been frozen.

| Kernel | Checked values | DUT ROI cycles | Maximum absolute error |
| --- | ---: | ---: | ---: |
| fir | 574 | 75,326 | 0 |
| iir | 528 | 17,653 | 7.60254151e-09 |
| fft | 512 | 41,929 | 3.66617365e-06 |
| pid | 515 | 8,782 | 0 |
| gemm | 500 | 155,749 | 2.45571137e-06 |
| bicg | 80 | 24,053 | 1.97106292e-06 |
| cholesky | 820 | 225,987 | 4.8279276e-07 |
| svm | 100 | 45,492 | 0 |

FIR and IIR whole-block and 4x64 streaming outputs/states match bitwise. PID includes its terminal state.
Cholesky: all 820 lower-triangle entries, positive diagonal and an independent reconstruction check pass; relative infinity-norm residual is `5.0252092818979085e-08` against provisional limit `2e-5`. Its serialized input has double-reference infinity-norm condition estimate `1671.5124509163`.
SVM: 100 labels match both pinned upstream labels and independent folded-weight double decisions; the smallest absolute reference decision is `0.6061864351498374`. This is not a near-boundary dataset.
FIR and PID use dyadic provisional values and are exact for this fixture; zero observed error does not establish general rounding accuracy.

[FFT ROI audit](fft-roi-audit.json) ties a named-symbol rebuild to the exact executed ELF hash. Its timed call closure contains no soft-double/libm calls; the runtime guard confirms no KissFFT allocation/free attempt. Twiddle generation and its double/libm calls are outside the ROI.
[Summary](summary.json), [run context](run-context.json), [numeric report](numeric-report.json) and [source pins](source-summary.json) retain identities, commands and outcomes. The [log index](log-index.json) maps original runtime log paths to archived files/JSON keys and hashes.
[Compiler stack usage](stack-usage.json) and static section sizes are available; stack high-water, memory headroom and larger milestone sizes remain to be qualified.
[Development history](development-history.json) preserves the resolved adapter-build failures. [Checker controls](checker-tests.txt) record six tests rejecting numerical errors, nonfinite values, missing/duplicate samples, wrong labels and excess Cholesky residual.

These are project-selected kernel diagnostics, not official CMSIS/KissFFT/PolyBench scores or a frozen AP5B performance/PPA baseline. The 1.20x/1.10x planning goals have not been assessed.
SVM patterns/model originate from CMSIS-DSP v1.18.0 under the included [Apache-2.0 license](CMSIS-DSP-LICENSE.txt); no model was retrained. All upstream source pins remain unchanged.

Reproduce from the source commit above:

```bash
make fetch-fp-sources
python3 scripts/test_fp_balanced_validation.py
make qualify-fp-balanced-dut JOBS=4
```

From this directory, verify archived file hashes with `sha256sum -c SHA256SUMS`.
