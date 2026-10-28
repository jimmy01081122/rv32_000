# Reuse the pinned ORFS environment for an explicit post-route TT repair stage.
include $(FLOW_HOME)/Makefile

.PHONY: baseline-grt-eco
baseline-grt-eco: $(OBJECTS_DIR)/copyright.txt
	mkdir -p $(LOG_DIR) $(REPORTS_DIR) $(RESULTS_DIR)
	$(OPENROAD_CMD) -log $(LOG_DIR)/5_2_grt_eco.log -metrics $(LOG_DIR)/5_2_grt_eco.json $(RV32_ROOT)/physical/asap7/baseline/repair.tcl
