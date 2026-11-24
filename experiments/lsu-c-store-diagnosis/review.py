"""Reconcile per-store measurements with the published C ROI and program results."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
from controls import check_wave
from run import EVIDENCE, ROOT, REF, counts, require, sha

PARENT = "db4f41c8a3f0fb2828756f0deb2c8e256c81ccf9"


def samples(path):
    with path.open() as f:
        return [{k:v if k=="kind" else int(v) for k,v in row.items()} for row in csv.DictReader(f)]


def verify_case(c, p):
    phases = p["cycle_partition"]
    stores = sum(p["retired_classes"].get(kind,0) for kind in ("int_store","fp_store"))
    w = phases.get("store_ack_wait",0)
    pre = sum(phases.get(kind,0) for kind in ("head_wait_int_store","head_wait_fp_store"))
    require(all(v>=0 for v in c.values()) and c["cycles"]==p["cycles"], "ROI bounds")
    require(sum(v for k,v in c.items() if k.startswith("pre_")) == pre == c["head_to_authorized_cycles"],
            "pre-authorization store lifetimes differ from ROI")
    require(sum(v for k,v in c.items() if k.startswith("wait_")) == w ==
            c["authorized_to_request_cycles"]+c["request_to_response_cycles"]+c["response_to_retire_cycles"],
            "ack wait lifetimes differ from ROI")
    require(sum(v for k,v in c.items() if k.startswith("unmarked_")) == p["store_ack_wait_phases"].get("mark_pending",0),
            "first marking accounting")
    require(c["stores"]==stores==p["overlapping_events"]["dmem_write_accepted"]==c["write"]==
            c["response_ok"]==c["wait_issue_write"]==c["request_to_response_cycles"], "store/response counts")
    require(c["response_to_retire_cycles"]==c["response_error"]==c["fault_traps"]==0,"unexpected delay or fault")
    require(c["base_first"]+c["data_first"]+c["operands_together"]==stores==
            c["first_edge_request"]+c["delayed_request"], "store denominator")
    require(c["unmarked_issue_write"]==c["first_edge_request"] and
            c["wait_load_response_edge"]==c["unmarked_load_response_edge"]+c["wait_yield_new_read"] and
            c["delayed_request"]==c["unmarked_load_response_edge"]+c["unmarked_yield_new_read"],
            "unexpected fixed-service arbitration sequence")
    require(c["head_capture_port_free"]<=c["pre_agu_capture"], "idle AGU/head opportunity")
    return w,pre


def review(out):
    reference = json.loads((EVIDENCE/"review.json").read_text())
    require(sha(EVIDENCE/"review.json")==hashlib.sha256(subprocess.check_output(
        ["git","show",PARENT+":docs/evidence/lsu-c-head-v1/review.json"],cwd=ROOT)).hexdigest(),"C evidence drift")
    require(sha(REF/"summary.json")==reference["measurement_sha256"],"C summary drift")
    build = json.loads((out/"build.json").read_text())
    require(sha(out/"observer")==build["observer_sha256"] and
            sha(out/"control")==build["control_sha256"]==reference["provenance"]["normal_simulator_sha256"], "binary binding")
    require(sha(out/"sim_main.cpp")==build["generated_harness_sha256"], "generated harness binding")
    for p,h in build["inputs"].items():
        path = ROOT/p
        require(sha(path)==h, "observer link or source input differs "+p)
    results = []
    refs = json.loads((REF/"summary.json").read_text())["records"]
    require(len(refs)==27 and len({(r["family"],r["name"]) for r in refs})==27, "incomplete corpus")
    for r in refs:
        d = out/r["family"]/r["name"]
        for f,h in [("dut.log",r["execution"]["log_sha256"]),("profile.json",r["profile_sha256"]),
                    ("memory.json",r["memory_audit_sha256"])]:
            require(sha(d/f)==h, "replay differs for "+str(d/f))
        c = Counter(counts(d/"counts.csv"))
        p = json.loads((d/"profile.json").read_text())
        w,pre = verify_case(c,p)
        for sample in samples(d/"examples.csv"):
            require(max(sample["base_operand_ready"],sample["data_operand_ready"]) < sample["agu_capture"]
                    < sample["first_authorized"] <= sample["request"] < sample["response"] == sample["retire_or_trap"],
                    "successful store edge order")
        results.append(dict(family=r["family"],name=r["name"],wait_cycles=w,pre_authorization_cycles=pre,
                            counters=dict(c),sample_sha256=sha(d/"examples.csv"),counts_sha256=sha(d/"counts.csv")))
    groups={}
    for family, size in (("embench",19),("fp32",8)):
        rows=[r for r in results if r["family"]==family]
        require(len(rows)==size, family+" count")
        total=Counter()
        for r in rows: total.update(r["counters"])
        def fraction(fn):
            return statistics.mean(fn(Counter(r["counters"]))/r["counters"]["cycles"] for r in rows)
        groups[family]=dict(workloads=len(rows),total=dict(sorted(total.items())),
            mean_roi_percent={k:100*fraction(fn) for k,fn in {
                "store_ack_wait":lambda c:sum(v for k,v in c.items() if k.startswith("wait_")),
                "request_edge":lambda c:c["wait_issue_write"], "direct_yield":lambda c:c["wait_yield_new_read"]+c["wait_yield_held_read"],
                "load_response_edge":lambda c:c["wait_load_response_edge"],
                "already_inflight_on_first_edge":lambda c:c["unmarked_load_response_edge"],
                "pre_authorization":lambda c:c["head_to_authorized_cycles"],
                "head_capture_port_free":lambda c:c["head_capture_port_free"],
                "head_data_only_missing":lambda c:c["pre_data_missing"],
                "head_base_only_missing":lambda c:c["pre_base_missing"],
                "head_both_missing":lambda c:c["pre_both_missing"],
                "unmarked_issue_write":lambda c:c["unmarked_issue_write"]}.items()},
            immediate_request_fraction=total["first_edge_request"]/total["stores"])
    control = json.loads((out/"controls/summary.json").read_text())
    require(set(control)=={"success","sw-fault","fsw-fault","slow-blocked","slow-fault"},"missing control")
    for name,rec in control.items():
        case = out/"controls"/name
        old,obs = case/"control",case/"observer"
        require(sha(old/"control.vcd.gz")==rec["sha256_wave"] and sha(old/"commit.trace")==sha(obs/"commit.trace") and
                sha(old/"memory.json")==sha(obs/"memory.json"),"directed artifacts drift")
        rows=samples(obs/"examples.csv")
        wave_events=check_wave(old/"control.vcd.gz",rows)
        c=Counter(counts(obs/"counts.csv"))
        fault=name.endswith("fault")
        delay=4 if name.startswith("slow") else 1
        require(len(rows)==rec["samples"] and wave_events["stores"]==rec["stores"]==c["stores"]
                and wave_events["write"]==c["write"] and wave_events["response_ok"]==c["response_ok"]
                and wave_events["response_error"]==rec["faults"]==c["fault_traps"]==int(fault)
                and c["request_to_response_cycles"]==delay*c["stores"] and c["response_to_retire_cycles"]==0
                and c["fault_response_to_trap_cycles"]==rec["fault_response_to_trap"]
                and c["wait_request_backpressure"]==rec["blocked_cycles"] and rec["rejected_shifted_request"],
                "control review")
        altered=[dict(row) for row in rows]
        altered[0]["request"]+=1
        try:
            check_wave(old/"control.vcd.gz",altered)
        except ValueError as e:
            require("wave differs for request" in str(e),"wrong waveform negative control")
        else:
            raise ValueError("shifted request accepted during review")
    # Mutate a real handshake count; verify that the independent ROI rejects it.
    case = results[0]
    bad = Counter(case["counters"])
    bad["wait_issue_write"] += 1
    try:
        verify_case(bad,json.loads((out/case["family"]/case["name"]/"profile.json").read_text()))
    except ValueError as e:
        require("ack wait lifetimes" in str(e),"wrong negative control")
    else:
        raise ValueError("added wait edge accepted")
    return dict(passed=True, cpu_source_commit=reference["source_commit"], cpu_and_memory_period_ps=10000,
                verified_workloads=len(results), family=groups, controls=control, rejected_added_wait_edge=True,
                workload=results)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    result=review(args.capture.resolve())
    with args.output.open("x") as f: json.dump(result,f,indent=2); f.write("\n")
