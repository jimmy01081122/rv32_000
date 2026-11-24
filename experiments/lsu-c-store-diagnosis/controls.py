"""Check store timestamps against VCD from the original C binary, including faults."""
import argparse
from collections import Counter
import csv
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
from run import C, EVIDENCE, ROOT, counts, require, sha

CORE = "TOP.rv32_ooo_core."
FIELDS = dict(clk="TOP.clk", rst="TOP.rst", commit="TOP.commit_trace",
              head=CORE+"u_rob.head_entry", authorize=CORE+"u_lsu.head_store_send",
              agu=CORE+"u_lsu.agu_valid", agu_req=CORE+"u_lsu.agu_req", flush=CORE+"flush_valid",
              tag=CORE+"u_lsu.in_flight_rob_tag", inflight=CORE+"u_lsu.in_flight_valid",
              store=CORE+"u_lsu.in_flight_is_store", ack=CORE+"sq_retire_ack",
              valid="TOP.dmem_req_valid", write="TOP.dmem_req_wen", ready="TOP.dmem_req_ready",
              rsp="TOP.dmem_rsp_valid", rsp_ready="TOP.dmem_rsp_ready", error="TOP.dmem_rsp_error",
              addr="TOP.dmem_req_addr", data="TOP.dmem_req_wdata", mask="TOP.dmem_req_byte_en")
FIELDS.update({f"iq{i}":CORE+f"u_int_iq.entries({i})" for i in range(8)})


def wave(path):
    scope, symbols, values = [], {}, {}
    with gzip.open(path, "rt") as f:
        for line in f:
            words = line.split()
            if not words:
                continue
            if words[0] == "$scope":
                scope.append(words[2])
            elif words[0] == "$upscope":
                scope.pop()
            elif words[0] == "$var":
                symbols[".".join([*scope, words[4]])] = words[3]
            elif words[0] == "$enddefinitions":
                break
        ids = {k:symbols[v] for k,v in FIELDS.items()}
        wanted = set(ids.values())
        timestamp = None
        for line in f:
            if line.startswith("#"):
                if timestamp is not None:
                    yield {k:values[v] for k,v in ids.items()}
                timestamp = int(line[1:])
            elif line.startswith("b"):
                v, code = line[1:].split()
                if code in wanted:
                    values[code] = int(v,2)
            elif line[:1] in ("0","1") and line[1:].strip() in wanted:
                values[line[1:].strip()] = int(line[0])
        if timestamp is not None:
            yield {k:values[v] for k,v in ids.items()}


def check_wave(path, rows):
    frames = [f for f in wave(path) if not f["rst"]]
    require(len(frames) % 2 == 0, "unpaired waveform")
    low, high = frames[::2], frames[1::2]
    require(all(f["clk"] == 0 for f in low) and all(f["clk"] == 1 for f in high), "unexpected edges")
    events = Counter()
    for lo, hi in zip(low, high):
        write = lo["valid"] and lo["ready"] and lo["write"]
        response = lo["rsp"] and lo["rsp_ready"] and lo["inflight"] and lo["store"]
        if write: events["write"] += 1
        if response:
            events["response_error" if lo["error"] else "response_ok"] += 1
            require(lo["ack"] != lo["error"], "response/ack polarity")
        if hi["commit"] >> 343 and (hi["commit"] >> 214 & 127) in (0x23, 0x27):
            events["stores"] += 1
    for r in rows:
        tag, pc, last = r["tag"], r["pc"], r["retire_or_trap"]
        matches = {k:[] for k in ("base_operand_ready","data_operand_ready","agu_capture","first_head",
                                  "first_authorized","request","response")}
        for edge, lo in enumerate(low[:last+1]):
            for i in range(8):
                slot = lo[f"iq{i}"]
                if slot >> 307 and (slot >> 190 & 65535) == tag and (slot >> 275 & 0xffffffff) == pc:
                    if slot & 2: matches["base_operand_ready"].append(edge)
                    if slot & 1: matches["data_operand_ready"].append(edge)
            h = lo["head"]
            head = h >> 244 and (h >> 195 & 0xffffffff) == pc and (h >> 227 & 65535) == tag
            req = lo["agu_req"]
            if lo["agu"] and not lo["flush"] and (req >> 284 & 65535) == tag and (req >> 369 & 0xffffffff) == pc:
                matches["agu_capture"].append(edge)
            if head:
                matches["first_head"].append(edge)
                if lo["authorize"]: matches["first_authorized"].append(edge)
                if lo["valid"] and lo["ready"] and lo["write"]:
                    require((lo["addr"],lo["data"],lo["mask"])==(r["addr"] & ~3,r["data"],r["mask"]), "request payload")
                    matches["request"].append(edge)
            if lo["rsp"] and lo["rsp_ready"] and lo["inflight"] and lo["store"] and lo["tag"] == tag:
                matches["response"].append(edge)
        for name, ticks in matches.items():
            require(ticks and ticks[0] == r[name], f"wave differs for {name}, store {tag}")
        trace = high[last]["commit"]
        fault = r["kind"] == "access_fault"
        require((trace >> 342) == (1 if fault else 2) and (trace >> 246 & 0xffffffff) == pc, "commit identity")
        require(bool(low[r["response"]]["error"]) == fault, "recorded fault status")
        if fault:
            require((trace >> 37 & 0xffffffff) == 7 and (trace >> 5 & 0xffffffff) == r["addr"], "fault details")
        else:
            require((trace >> 137 & 1) and (trace >> 105 & 0xffffffff)==r["addr"] and
                    (trace >> 69 & 0xffffffff)==r["data"] and (trace >> 101 & 15)==r["mask"], "committed write")
    return events


def controls(out):
    root = out / "controls"
    root.mkdir()
    pinned = {r["path"]:r["sha256"] for r in json.loads((EVIDENCE/"inventory.json").read_text())["records"]}
    result = {}
    specs = [("success", ROOT/"build/tests/store_forwarding.elf",1,1,False),
             ("sw-fault", C/"qualification-v1/interface/sw.elf",1,1,True),
             ("fsw-fault", C/"qualification-v1/interface/fsw.elf",1,1,True),
             ("slow-blocked", ROOT/"build/tests/store_forwarding.elf",4,4,False),
             ("slow-fault", C/"qualification-v1/interface/sw.elf",4,4,True)]
    for name, elf, delay, ready, fault in specs:
        require(sha(elf)==pinned[str(elf.relative_to(ROOT))], "directed ELF differs")
        case = root/name
        for mode in ("control","observer"):
            d = case/mode
            d.mkdir(parents=True)
            cmd = [out/mode, "+elf="+str(elf), "+max-cycles=100000", "+core-period-ps=10000",
                   "+imem-response-ps=10000", "+imem-interval-ps=10000", f"+dmem-response-ps={delay*10000}",
                   f"+dmem-ready-period={ready}", "+trace=commit.trace", "+memory-audit=memory.json"]
            if fault: cmd.append("+dmem-fault-store=0x80000124")
            if mode == "control": cmd.append("+vcd=control.vcd")
            with (d/"dut.log").open("w") as log:
                subprocess.run(cmd,cwd=d,env=dict(os.environ, STORE_EDGES_OUT=str(d), STORE_EDGES_WHOLE="1"),
                               stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
        obs, old = case/"observer", case/"control"
        line = "[Simulator] VCD tracing enabled: control.vcd\n"
        stdout = (old/"dut.log").read_text()
        require(stdout.count(line)==1 and stdout.replace(line,"")==(obs/"dut.log").read_text(), "directed stdout drift")
        for filename in ("commit.trace","memory.json"):
            require(sha(old/filename)==sha(obs/filename),"directed "+filename+" drift")
        with (old/"control.vcd").open("rb") as src, gzip.GzipFile(str(old/"control.vcd.gz"),"wb",mtime=0) as dst:
            shutil.copyfileobj(src,dst)
        with (obs/"examples.csv").open() as f:
            rows = [{k:v if k=="kind" else int(v) for k,v in r.items()} for r in csv.DictReader(f)]
        c = counts(obs/"counts.csv")
        events = check_wave(old/"control.vcd.gz", rows)
        require(all(events[k] == c.get(k,0) for k in ("stores","write","response_ok","response_error")), "wave totals")
        require(events["stores"]>0 and c.get("fault_traps",0)==int(fault)==events["response_error"] and
                c["request_to_response_cycles"]==delay*events["stores"] and c["response_to_retire_cycles"]==0,
                "control latency or precise fault")
        if name=="slow-blocked": require(c.get("wait_request_backpressure",0)>0, "backpressure not exercised")
        changed = [dict(r) for r in rows]
        changed[0]["request"] += 1
        try:
            check_wave(old/"control.vcd.gz", changed)
        except ValueError as exc:
            require("wave differs for request" in str(exc), "wrong negative control")
        else:
            raise ValueError("one-edge corruption accepted")
        result[name]=dict(stores=events["stores"],faults=events["response_error"],samples=len(rows),
                          fault_response_to_trap=c.get("fault_response_to_trap_cycles",0),
                          blocked_cycles=c.get("wait_request_backpressure",0),sha256_wave=sha(old/"control.vcd.gz"),
                          rejected_shifted_request=True)
    (root/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture",type=Path)
    print(json.dumps(controls(parser.parse_args().capture.resolve()),indent=2))
