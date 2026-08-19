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

    cells = {}
    total_cells = 0
    inferred_latches = 0
    combinational_loops = 0

    # Check for warnings/assertions
    for line in content.splitlines():
        if "Warning: Latch inferred" in line or "inferred latch" in line.lower():
            inferred_latches += 1
        if "Warning: Found logic loop" in line or "combinational loop" in line.lower():
            combinational_loops += 1

    # Extract cell statistics section
    stat_section = False
    for line in content.splitlines():
        if "=== design hierarchy ===" in line or "=== rv32_ooo_core ===" in line or "Printing statistics" in line:
            stat_section = True
        if stat_section:
            m = re.match(r"\s+([A-Za-z0-9_\\$]+)\s+(\d+)", line)
            if m:
                cell_name = m.group(1).strip()
                count = int(m.group(2))
                if cell_name == "Number of cells:":
                    total_cells = count
                elif not cell_name.startswith("Number") and not cell_name.startswith("Chip") and not cell_name.startswith("=== "):
                    cells[cell_name] = count

    if total_cells == 0 and cells:
        total_cells = sum(cells.values())

    dff_count = sum(cnt for name, cnt in cells.items() if "DFF" in name or "dff" in name)
    logic_cell_count = total_cells - dff_count

    return {
        "synthesis_tool": "Yosys 0.9",
        "top_module": "rv32_ooo_core",
        "total_generic_cells": total_cells,
        "sequential_dff_cells": dff_count,
        "combinational_logic_cells": logic_cell_count,
        "inferred_latches": inferred_latches,
        "combinational_loops": combinational_loops,
        "synthesis_clean": (inferred_latches == 0 and combinational_loops == 0 and total_cells > 0),
        "detailed_cells": cells
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

    print(f"Total Generic Cells: {stats['total_generic_cells']} (DFF: {stats['sequential_dff_cells']}, Comb: {stats['combinational_logic_cells']})")
    print(f"Inferred Latches   : {stats['inferred_latches']}")
    print(f"Comb Loops         : {stats['combinational_loops']}")
    print(f"Synthesis Status   : {'PASS (Clean)' if stats['synthesis_clean'] else 'FAIL'}")

    return 0 if stats["synthesis_clean"] else 1


if __name__ == "__main__":
    sys.exit(main())
