#!/usr/bin/env python3
"""Real instruction-level positive controls; hand-encoded RV32IF diagnostic ELFs."""
import argparse, json, struct, subprocess
from pathlib import Path
from analyze_retained import require, sha
def fp(f7,rd,rs1,rs2=0):return f7<<25|rs2<<20|rs1<<15|rd<<7|0x53
def program(nops):
    # f1=f10=2, f2=1. FDIV and a dependent FMUL chain both return exactly 2.
    code=[0x400000b7,fp(0x78,1,1),fp(0x78,10,1),0x3f8000b7,fp(0x78,2,1),0xc00022f3,
          fp(12,3,1,2),*[0x13]*nops,*[fp(8,10,10,2)]*24,
          fp(0x70,6,10),fp(0x70,7,3),0x400000b7,
          (1<<20)|(6<<15)|(4<<12)|(6<<7)|0x33, # xor x6,x6,x1
          (1<<20)|(7<<15)|(4<<12)|(7<<7)|0x33, # xor x7,x7,x1
          (7<<20)|(6<<15)|(6<<12)|(6<<7)|0x33, # or x6,x6,x7
          (6<<20)|(3<<12)|(6<<7)|0x33,        # sltu x6,x0,x6
          0xc00022f3,0x10000237,              # closing marker; MMIO base x4
          (6<<20)|(4<<15)|(2<<12)|(4<<7)|0x23, # sw x6,4(x4)
          0x10500073]
    payload=struct.pack('<'+'I'*len(code),*code)
    ident=b'\x7fELF'+bytes([1,1,1])+bytes(9)
    header=struct.pack('<16sHHIIIIIHHHHHH',ident,2,243,1,0x80000000,52,0,0,52,32,1,0,0,0)
    phdr=struct.pack('<IIIIIIII',1,256,0x80000000,0x80000000,len(payload),len(payload),5,4)
    return (header+phdr).ljust(256,b'\0')+payload,code
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--observer',type=Path,required=True);ap.add_argument('--original',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    require(not a.output.exists(),'fresh control output required');a.output.mkdir(parents=True);records=[]
    for n in range(6):
        case=a.output/str(n);case.mkdir();elf,words=program(n);(case/'input.elf').write_bytes(elf)
        (case/'instructions.json').write_text(json.dumps([{'pc':hex(0x80000000+4*i),'word':hex(w)} for i,w in enumerate(words)],indent=2)+'\n')
        commands={}
        for mode,exe in [('original',a.original),('off',a.observer),('on',a.observer)]:
            out=case/mode;out.mkdir()
            cmd=[str(exe),f'+elf={case}/input.elf','+max-cycles=5000','+core-period-ps=10000',
                '+imem-response-ps=10000','+imem-interval-ps=10000','+dmem-response-ps=10000',
                f'+profile-core-roi={out}/profile.json',f'+trace={out}/trace.log']
            if mode=='on':cmd.append(f'+observe-fp={out}/observer.json')
            with (out/'dut.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
            require(r.returncode==0 and 'Exit status    : PASS (0)' in (out/'dut.log').read_text(),'diagnostic failed '+str(out))
            require('TRAP' not in (out/'dut.log').read_text(),'unexpected trap')
            commands[mode]=cmd
        for name in ['profile.json','trace.log']:
            require(len({sha(case/m/name) for m in ['original','off','on']})==1,'observer changed ordered trace/profile')
        p=json.loads((case/'on/observer.json').read_text())
        records.append(dict(nops=n,commands=commands,elf_sha256=sha(case/'input.elf'),observer=p,
            trace_sha256=sha(case/'on/trace.log'),ordered_trace_and_profile_identical=True))
    # Positive hardware control must exercise arbitration blocking, not merely
    # a synthetic Snapshot that may be unreachable in this core.
    contention=sum(r['observer']['counts'].get('divsqrt_completion_blocked',0) for r in records)
    require(contention>0,'no positive completion contention control exercised')
    report=dict(scope='Diagnostic programs only, no benchmark score; exact FMUL/FDIV results checked by program',
        observer_sha256=sha(a.observer),original_sha256=sha(a.original),records=records,
        divsqrt_completion_blocked_cycles=contention,passed=True)
    (a.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print('hardware contention controls PASS',contention)
if __name__=='__main__':main()
