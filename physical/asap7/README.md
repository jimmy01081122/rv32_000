# RV32 OoO Core — ASAP7 1.0 GHz Physical Implementation Flow

## Overview
This directory contains the physical design platform setup, constraints, scripts, and results for implementing `rv32_ooo_core` on the **ASAP7 predictive 7nm FinFET** standard-cell library using **OpenROAD Flow Scripts (ORFS)**.

## Project Structure
```text
physical/asap7/
├── config.mk               # Primary ORFS design configuration
├── constraint.sdc          # 1.000 ns (1.0 GHz) SDC timing constraints
├── constraint_notes.md     # Detailed documentation of I/O budgets and timing assumptions
├── pin_order.cfg           # Physical IO pin boundary placement configuration
├── toolchain.lock          # Cryptographically pinned tool versions and PDK files
├── baseline_manifest.json  # Pre-physical optimization baseline record
├── README.md               # Flow documentation and execution guide
├── scripts/                # Extraction, STA reporting, and DSE automation scripts
│   ├── run_asap7_flow.sh   # Master automated execution script via Docker
│   ├── parse_asap7_sta.py  # OpenSTA timing report parser & critical path classifier
│   └── run_fmax_sweep.py   # Automated clock period / Fmax binary sweep script
└── results/                # Physical implementation deliverables keyed by commit SHA
```

## Target Criteria
- **PDK / Standard Cells:** ASAP7 7.5T (`asap7sc7p5t`)
- **Target Clock:** `1.000 ns` (`1.0 GHz`)
- **Primary Acceptance:** Post-route $F_{\max} \ge 1.0\text{ GHz}$, $\text{CoreMark/MHz} \ge 0.8$
- **Phase AP0 Rule:** Baseline physical characterization only. **No RTL microarchitecture changes.**
