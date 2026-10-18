# Inspect the same global-route database at explicitly tested clock periods.
set platform /OpenROAD-flow-scripts/flow/platforms/asap7
set suffix $::env(RV32_CORNER)
if {$suffix ni {TT SS FF}} { error "RV32_CORNER must be TT, SS or FF" }
# Each corner is analyzed in a fresh OpenSTA process. Cross-corner XOR arcs in
# this PDK do not all match a shared reference timing graph (STA-1111).
# Match the five libraries selected by the pinned platform config exactly.
# A glob also selects experimental FAKE DFF views and a second FF SIMPLE lib.
foreach template {
  asap7sc7p5t_AO_RVT_%s_nldm_211120.lib.gz
  asap7sc7p5t_INVBUF_RVT_%s_nldm_220122.lib.gz
  asap7sc7p5t_OA_RVT_%s_nldm_211120.lib.gz
  asap7sc7p5t_SIMPLE_RVT_%s_nldm_211120.lib.gz
  asap7sc7p5t_SEQ_RVT_%s_nldm_220123.lib
} {
  set file $platform/lib/NLDM/[format $template $suffix]
  read_liberty $file
}

report_units
exit
