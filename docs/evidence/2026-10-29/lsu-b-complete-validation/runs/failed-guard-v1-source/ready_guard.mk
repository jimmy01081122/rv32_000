include $(FLOW_HOME)/Makefile
.PHONY: ready-hold-guard
ready-hold-guard: $(OBJECTS_DIR)/copyright.txt
	mkdir -p $(LOG_DIR) $(REPORTS_DIR) $(RESULTS_DIR)
	$(OPENROAD_CMD) -log $(LOG_DIR)/5_3_ready_guard.log -metrics $(LOG_DIR)/5_3_ready_guard.json $(RV32_ROOT)/experiments/lsu-b-validation-v2/ready_guard.tcl
