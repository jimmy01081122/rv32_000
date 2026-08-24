#!/usr/bin/env python3
"""
scripts/parse_synth_log.py — Parse Yosys Synthesis Log and Output Machine-Readable Statistics
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def parse_synth_log(log_path: str) -> dict:
    if not Path(log_path).exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")

    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()

    inferred_latches = 0
    combinational_loops = 0

    # Check for warnings/assertions
    for line in content.splitlines():
        if "Warning: Latch inferred" in line or "inferred latch" in line.lower():
            inferred_latches += 1
        if "Warning: Found logic loop" in line or "combinational loop" in line.lower():
            combinational_loops += 1

    # Extract all stat sections from the log
    stat_sections = []
    current_section = None
    for line in content.splitlines():
        if "=== design hierarchy ===" in line or "=== rv32_ooo_core ===" in line or "Printing statistics" in line:
            current_section = {}
            stat_sections.append(current_section)
        if current_section is not None:
            m = re.match(r"\s+([A-Za-z0-9_\\$]+)\s+(\d+)", line)
            if m:
                cell_name = m.group(1).strip()
                count = int(m.group(2))
                if cell_name == "Number of cells:":
                    current_section["_total"] = count
                elif cell_name == "Number of processes:":
                    current_section["_processes"] = count
                elif not cell_name.startswith("Number") and not cell_name.startswith("Chip") and not cell_name.startswith("=== "):
                    current_section[cell_name] = count

    def extract_metrics(section: dict) -> tuple[dict, int, int]:
        cells = {k: v for k, v in section.items() if not k.startswith("_")}
        total = section.get("_total", sum(cells.values()))
        procs = section.get("_processes", 0)
        return cells, total, procs

    proc_lowered_cells: dict = {}
    proc_lowered_total: int = 0
    proc_lowered_procs: int = 0
    post_synth_cells: dict = {}
    post_synth_total: int = 0
    post_synth_procs: int = 0

    if len(stat_sections) >= 2:
        proc_lowered_cells, proc_lowered_total, proc_lowered_procs = extract_metrics(stat_sections[-2])
        post_synth_cells, post_synth_total, post_synth_procs = extract_metrics(stat_sections[-1])
    elif len(stat_sections) == 1:
        proc_lowered_cells, proc_lowered_total, proc_lowered_procs = extract_metrics(stat_sections[0])
        post_synth_cells, post_synth_total, post_synth_procs = proc_lowered_cells, proc_lowered_total, proc_lowered_procs

    dff_count = sum(cnt for name, cnt in post_synth_cells.items() if "DFF" in name or "dff" in name)
    macro_cells = {name: cnt for name, cnt in post_synth_cells.items() if name in ("$mul", "$div", "$mod", "$memrd", "$memwr", "$mem")}
    logic_cell_count = post_synth_total - dff_count

    return {
        "synthesis_tool": "Yosys 0.9",
        "top_module": "rv32_ooo_core",
        "total_generic_cells": post_synth_total,
        "post_synth_cells": post_synth_total,
        "process_lowered_cells": proc_lowered_total,
        "sequential_dff_cells": dff_count,
        "combinational_logic_cells": logic_cell_count,
        "macro_cells": macro_cells,
        "unelaborated_processes": post_synth_procs,
        "inferred_latches": inferred_latches,
        "combinational_loops": combinational_loops,
        "synthesis_clean": (inferred_latches == 0 and combinational_loops == 0 and post_synth_procs == 0 and post_synth_total > 0),
        "detailed_cells": post_synth_cells,
        "detailed_cells_post_synth": post_synth_cells,
        "detailed_cells_process_lowered": proc_lowered_cells,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse Yosys synthesis log")
    parser.add_argument("log_file", help="Path to synth.log")
    parser.add_argument("--output", "-o", default=None, help="Path to output JSON")
    args = parser.parse_args()

    stats = parse_synth_log(args.log_file)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        print(f"Synthesis summary written to {args.output}")

    print(f"Process-Lowered Cells : {stats['process_lowered_cells']}")
    print(f"Post-Synth Cells      : {stats['post_synth_cells']} (total_generic_cells alias)")
    print(f"  DFF                 : {stats['sequential_dff_cells']}")
    print(f"  Comb Logic          : {stats['combinational_logic_cells']}")
    print(f"Macro Cells (Mul/Mem) : {sum(stats['macro_cells'].values())} {stats['macro_cells']}")
    print(f"Unelaborated Processes: {stats['unelaborated_processes']} (Required: 0)")
    print(f"Inferred Latches      : {stats['inferred_latches']}")
    print(f"Comb Loops            : {stats['combinational_loops']}")
    print(f"Synthesis Status      : {'PASS (Clean)' if stats['synthesis_clean'] else 'FAIL'}")

    return 0 if stats["synthesis_clean"] else 1


if __name__ == "__main__":
    sys.exit(main())
