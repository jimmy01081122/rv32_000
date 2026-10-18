# TT slew margin diagnosis: intermediate results, not a qualified baseline

The first whole-core route review is preserved separately in
`../global-route-initial-review/`: SS had 541 slew violations and FF had 30.
These attempts keep the same 18 frozen RTL files and independent acceptance
constraints. Only TT cell/buffer repair and routing change.

`physical-14000ps-tt-abc-slew30-hold50-v5/` completed TT repair with 30% slew
margin and a 50 ps hold target. Its route updates cover modified nets only;
it lacks the final whole-design routing check and cannot qualify the baseline.
`physical-14000ps-tt-abc-full-route-v6/` adds that check, with 174,227 routed
nets, 1,436,518 µm wirelength, 29.58% total resource demand and zero overflow.
Both jobs exited 0 with unchanged declared inputs. Their separate source and
ancestry records remain in `run.json` and `job.json`.

| Corner | v6 setup slack at 14 ns (ps) | Hold slack (ps) | Slew violations |
| --- | ---: | ---: | ---: |
| TT | 6885.046 | 48.603 | 0 |
| SS | 3907.117 | 85.040 | 171 |
| FF | 8543.944 | 17.036 | 0 |

The full v6 review correctly rejects closure. Its 21,834.80388 µm² area is an
unqualified intermediate value, not a comparison denominator. The final route
database, SDC and guide are gzip archives with byte-preserving decompression.
All three independent corner processes and their raw reports are retained.

`paired-pin-diagnosis/` uses fresh TT and SS processes on the same v6 database;
`slew-diagnose.tcl` first runs the production reporting script, then calls native
`sta::report_slews` and `report_net`. At `place18130/A`, TT rise slew is
222.6700 ps and SS is 349.1768 ps, above the unchanged 320 ps SS limit. The
driver is `u_rob.next_seq[9]$_SDFFE_PP0P_/QN`, with seven loads and 17.4939 fF
wire capacitance. Its clock slew is only 18.9285 ps TT / 24.1427 ps SS.
This representative failing data net explains why a 224 ps TT target can still
fail SS; it does not establish the ratio for every net.

The next clean attempt starts again from the original pre-ECO route and uses
a 45% TT slew margin (176 ps optimizer target), keeping the 50 ps hold target.
It must independently pass TT/SS/FF electrical and timing checks; neither the
library limits nor the serialized I/O/clock constraints are relaxed. No CPU
architecture optimization is implemented by these physical repairs.

`grt-cache-controls/` retains two real CLI rejections for a changed period and
an unsuccessful source checkpoint. `four-cell-eco-api/` retains the small
development probe for the final whole-route/antenna command sequence; it is
API evidence only and has no durable whole-core job record.

Run `sha256sum -c SHA256SUMS` here to verify this archive.
