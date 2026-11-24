"""Recheck all 27 frozen C runs and compare their clock cycles to ROOM and baseline."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from collections import Counter
import statistics
import subprocess
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "scripts/baseline_contract.py").exists())
sys.path.insert(0, str(ROOT / "scripts"))
from baseline_contract import sha
from experiment_contract import load_experiment
from experiment_provenance import measurement_command, retired_work, review_provenance
from measure_post_lsu_baseline import check_result

BASE = ROOT / "build/experiments/lsu-c-head-v1"
PARENT = ROOT / "docs/evidence/2026-11-18/lsu-rob-room-functional/common-clock-review.json"
PARENT_SHA = "50b308fee546808898f385ad79ec87eb893da22163a94508afe1f99dfa20f992"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def group_scores(rows, key):
    def score(subset):
        return statistics.geometric_mean(r[key] / r["candidate_cycles"] for r in subset)
    embedded = score(r for r in rows if r["family"] == "embench")
    dsp = score(r for r in rows if r["group"] == "dsp")
    matrix = score(r for r in rows if r["group"] == "matrix_ml")
    return dict(embench=embedded, fp32=math.sqrt(dsp * matrix), dsp=dsp, matrix_ml=matrix)


def review():
    path = ROOT / "experiments/lsu-c-head-v1/manifest.json"
    experiment, baseline = load_experiment(path)
    measured = BASE / "measurement-10000ps-v1"
    report = json.loads((measured / "summary.json").read_text())
    require(report["passed"] and report["start"] == report["end"] and not report["start"]["status"] and
            report["experiment_id"] == experiment["experiment_id"] and report["experiment_manifest_sha256"] == sha(path)
            and report["core_period_ps"] == report["memory_ps"] == 10000, "incomplete or mixed measurement")
    source = report["start"]["commit"]
    build, qualification = (BASE / "build-v1/summary.json", BASE / "qualification-v1/summary.json")
    require(all(json.loads(p.read_text())["start"] == report["start"] for p in (build, qualification)),
            "build and qualification must share the measurement commit")
    for item, digest in {str(path.relative_to(ROOT)): sha(path), **experiment["candidate_rtl_files_sha256"],
                         **experiment["physical_inputs_sha256"], **experiment["simulation_inputs_sha256"]}.items():
        data = subprocess.check_output(["git", "show", source + ":" + item], cwd=ROOT)
        require(hashlib.sha256(data).hexdigest() == digest, "source commit differs " + item)
    provenance, normal = review_provenance(path, experiment, report, build, qualification)
    require(report["result_checker_sha256"] == sha(ROOT / "scripts/measure_post_lsu_baseline.py"), "checker changed")
    original = ROOT / baseline["measurement"]["formal_evidence"]
    require(sha(original / "summary.json") == report["baseline_summary_sha256"] ==
            baseline["measurement"]["formal_summary_sha256"], "baseline changed")
    require(sha(PARENT) == PARENT_SHA, "published ROOM results changed")
    parent = json.loads(PARENT.read_text())
    require(parent["passed"] and parent["period_ps"] == parent["memory_ps"] == 10000, "incompatible parent")
    parent_data = ROOT / parent["measurement"]
    require(sha(parent_data / "summary.json") == parent["measurement_summary_sha256"], "ROOM raw results changed")
    workloads = baseline["workloads"]
    expected = [(r["family"], r["name"]) for r in workloads]
    inputs = [report["records"], parent["records"], json.loads((parent_data / "summary.json").read_text())["records"],
              json.loads((original / "summary.json").read_text())["records"]]
    for records in inputs:
        require(len(expected) == 27 and [(r["family"], r["name"]) for r in records] == expected,
                "missing or reordered workload")
    rows = []
    count = 0
    partition_changes = {}
    family_shares = {}
    for workload, new, old, raw_old, ref in zip(workloads, *inputs):
        family, name = workload["family"], workload["name"]
        case = measured / family / name
        log, audit, profile, elf = [case / f for f in ("dut.log", "memory.json", "profile.json", "input.elf")]
        measurement_command(new, normal, case, 10000)
        require(new["passed"] and new["execution"]["returncode"] == 0 and sha(elf) == workload["elf_sha256"]
                and sha(log) == new["execution"]["log_sha256"] and sha(audit) == new["memory_audit_sha256"]
                and sha(profile) == new["profile_sha256"], "raw measurement mismatch " + name)
        counters = json.loads(profile.read_text())
        checked = check_result(workload, log.read_text(), json.loads(audit.read_text()), 10000, 10000, elf,
                               counters, require_reference_cycles=False)
        require(not checked["problems"] and checked["cycles"] == new["cycles"], "score verification " + name)
        if checked["numeric"]:
            count += checked["numeric"]["checked_values"]
        for directory, record in [(original, ref), (parent_data, raw_old)]:
            previous = directory / family / name / "profile.json"
            require(sha(previous) == record["profile_sha256"], "reference profile changed " + name)
            earlier = json.loads(previous.read_text())
            require(retired_work(earlier) == retired_work(counters) and earlier["retired_classes"] == counters["retired_classes"],
                    "retired work differs " + name)
        delta = partition_changes.setdefault(family, Counter())
        before, after = earlier["cycle_partition"], counters["cycle_partition"]
        shares = family_shares.setdefault(family, Counter())
        shares.update({reason: cycles / counters["cycles"] for reason, cycles in after.items()})
        for reason in set(before) | set(after):
            delta[reason] += after.get(reason, 0) - before.get(reason, 0)
        require(old["baseline_cycles"] == workload["reference_cycles"] and old["candidate_cycles"] == raw_old["cycles"],
                "reference cycles mismatch " + name)
        rows.append(dict(family=family, name=name, group=workload.get("group"),
                         baseline_cycles=workload["reference_cycles"], room_cycles=old["candidate_cycles"],
                         candidate_cycles=checked["cycles"], cycles_saved=old["candidate_cycles"]-checked["cycles"],
                         room_buffer_head_wait=earlier["load_head_wait_phases"].get("own_response_buffer", 0),
                         candidate_buffer_head_wait=counters["load_head_wait_phases"].get("own_response_buffer", 0)))
    for family, differences in partition_changes.items():
        require(sum(differences.values()) == -sum(r["cycles_saved"] for r in rows if r["family"] == family),
                "cycle partition does not reconcile " + family)
    require(count == 3629, "incomplete FP32 numerical comparison")
    return dict(passed=True, source_commit=source, period_ps=10000, memory_ps=10000, physical_qualified=False,
                provenance=provenance, parent_review_sha256=PARENT_SHA, measurement_sha256=sha(measured / "summary.json"),
                per_pc_retire_work_matches_both_references=True, numeric_values=count, records=rows,
                mean_cycle_fraction_by_family={
                    family: {reason: fraction / sum(r["family"] == family for r in rows)
                             for reason, fraction in sorted(shares.items())}
                    for family, shares in family_shares.items()},
                cycle_partition_candidate_minus_room={k: dict(sorted(v.items())) for k, v in partition_changes.items()},
                relative_to_original=group_scores(rows, "baseline_cycles"), relative_to_room=group_scores(rows, "room_cycles"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output
    result = review()
    with output.open("x") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    print(json.dumps({k: result[k] for k in ("relative_to_original", "relative_to_room")}, indent=2))
