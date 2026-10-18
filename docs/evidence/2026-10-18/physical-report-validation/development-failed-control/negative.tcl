source physical/asap7/baseline/report.tcl
unset_input_delay [get_ports A]
save_report $directory/missing-input-delay.rpt {check_setup -verbose}
set_load 10000 [all_outputs]
save_report $directory/excess-load.rpt {report_check_types -max_slew -max_capacitance -violators}
