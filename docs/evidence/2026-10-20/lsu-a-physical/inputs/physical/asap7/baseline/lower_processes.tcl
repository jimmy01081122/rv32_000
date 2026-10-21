# Standard ORFS canonicalization hook. Avoid the pathological latch traversal
# on large mux graphs by simplifying them before extracting sequential cells.
# Fail closed if ANY process remains; no inferred latch is silently discarded.
proc_clean
proc_rmdead
proc_init
proc_arst
proc_mux
opt_expr
opt_clean
proc_dff
proc_memwr
proc_clean
opt_clean -purge
select -assert-none p:* {t:$dlatch} {t:$_DLATCH_*}
check -assert
