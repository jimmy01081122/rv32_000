"""Bind full RTL proof to the exact common mapped Verilog used by physical cores."""
from pathlib import Path
import gzip,hashlib,json,sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'experiments/fpu-mapping-v1'));from compare_mapped import canonical_graph,MODULE
from link_shared import modules
BASE=ROOT/'build/experiments/lsu-b-validation-v2';FPU=ROOT/'build/experiments/fpu-mapping-v1';sha=lambda b:hashlib.sha256(b).hexdigest()
def raw(p):return p.read_bytes() if p.exists() else gzip.decompress(Path(str(p)+'.gz').read_bytes())
def guest(p):return ROOT/Path(p).relative_to('/workspace')
class Source:
 def __init__(self,b):self.b=b
 def read_bytes(self):return self.b
contract=ROOT/'experiments/lsu-b-validation-v2/contract-hold40.json';policy=json.loads(contract.read_text());linkpath=ROOT/policy['shared_link_manifest']['path'];assert sha(linkpath.read_bytes())==policy['shared_link_manifest']['sha256'];link=json.loads(linkpath.read_text());proof=json.loads((BASE/'fpu-state-relation-v1/proof-summary.json').read_text());unit=FPU/'shared-unit-v1';native=json.loads((unit/'run.json').read_text());assert native['flow_completed'] and native['returncode']==0 and native['input_identities_unchanged'] and sha(raw(unit/'make.log'))==native['log_sha256'];job=json.loads((unit/'job.json').read_text());assert all(sha(raw(guest(p)))==h for p,h in job['inputs'].items())
source=unit/'fp-source.v';source_body=modules(source)[MODULE];assert sha(source_body)==native['fpu_body_sha256'];origins={}
for name,p in [('baseline',ROOT/'build/baseline-setup/rtl_lowered.v'),('A',ROOT/'build/experiments/lsu-a-v1/rtl_lowered.v'),('B',ROOT/'build/experiments/lsu-b-v1/rtl_lowered.v')]:
 data=raw(p);body=modules(Source(data))[MODULE];assert body==source_body;origins[name]=dict(lowered_source_sha256=sha(data),FPU_body_sha256=sha(body))
mapped=unit/'results/asap7/rv32_post_lsu_v1/base/fp_mapped.rtlil.json';mapping=json.loads(raw(mapped))['modules'][MODULE];graph,graph_sha=canonical_graph(mapping);assert graph_sha==policy['shared_fpu_graph_sha256']==link['shared_fpu_graph_sha256'];assert proof['inputs']['/workspace/'+str(mapped.relative_to(ROOT))]==sha(raw(mapped));assert proof['inputs']['/workspace/'+str(source.relative_to(ROOT))]==sha(raw(source))
readback=FPU/'unit-from-verilog.json';_,rsha=canonical_graph(json.loads(raw(readback))['modules'][MODULE]);assert rsha==graph_sha;repeat=FPU/'shared-unit-repeat-v1/results/asap7/rv32_post_lsu_v1/base/fp_mapped.rtlil.json';_,rsha2=canonical_graph(json.loads(raw(repeat))['modules'][MODULE]);assert rsha2==graph_sha
unit_verilog=ROOT/link['unit_netlist'];assert sha(raw(unit_verilog))==link['unit_netlist_sha256'];body=modules(Source(raw(unit_verilog)))[MODULE];assert sha(body)==link['shared_fpu_body_sha256'];cores={}
for name,row in link['variants'].items():
 p=ROOT/row['linked_netlist'];data=raw(p);parsed=modules(Source(data));assert sha(data)==row['linked_sha256'] and parsed[MODULE]==body and sha(parsed['rv32_ooo_core'])==row['core_body_sha256'];cores[name]=dict(linked_netlist_sha256=sha(data),core_body_sha256=sha(parsed['rv32_ooo_core']),shared_FPU_body_sha256=sha(parsed[MODULE]))
report=dict(passed=True,contract_sha256=sha(contract.read_bytes()),proof_summary_sha256=sha((BASE/'fpu-state-relation-v1/proof-summary.json').read_bytes()),link_manifest_sha256=sha(linkpath.read_bytes()),shared_graph_sha256=graph_sha,actual_mapped_json_sha256=sha(raw(mapped)),actual_Verilog_readback_json_sha256=sha(raw(readback)),standalone_repeat_json_sha256=sha(raw(repeat)),original_FPU_body_sha256=sha(source_body),source_origins=origins,linked_cores=cores,reviewer_sha256=sha(Path(__file__).read_bytes()));out=BASE/'formal-to-physical-link-review.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
