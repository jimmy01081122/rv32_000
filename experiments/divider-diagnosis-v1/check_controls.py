#!/usr/bin/env python3
"""Actual DIV/DIVU/REM/REMU instructions, oracle checks and observer identity."""
import argparse, collections, hashlib, json, struct, subprocess
from pathlib import Path
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,msg):
    if not ok:raise ValueError(msg)
def signed(v):return v if v<2**31 else v-2**32
def oracle(a,b,op):
    x,y=(signed(a),signed(b)) if op in (4,6) else (a,b)
    if not y:return a if op>=6 else 0xffffffff
    q=abs(x)//abs(y)
    if (x<0)!=(y<0):q=-q
    return (x-q*y if op>=6 else q)&0xffffffff
def li(reg,value):
    value&=0xffffffff
    return [(((value+0x800)>>12)&0xfffff)<<12|reg<<7|0x37,
            (value&0xfff)<<20|reg<<15|reg<<7|0x13]
def program():
    words=li(7,0)+[0xc00022f3];rows=[]
    pairs=[(-7,3),(-7,-3),(7,-3),(5,9),(0,7),(17,1),
           (0x80000000,-1),(17,4),(0xf0000000,0xfffffff0),
           (0x7fffffff,0),(0x123456,13),(1,0x80000000)]
    for op in range(4,8):
        for a,b in pairs:
            a&=0xffffffff;b&=0xffffffff;value=oracle(a,b,op)
            words+=li(1,a)+li(2,b)+li(4,value)
            pc=0x80000000+4*len(words)
            words += [1<<25|2<<20|1<<15|op<<12|3<<7|0x33,
                      4<<20|3<<15|4<<12|3<<7|0x33,
                      3<<20|7<<15|6<<12|7<<7|0x33]
            rows.append(dict(op=op,a=a,b=b,result=value,pc=pc,
                             latency=1 if b==0 or (op in (4,6) and a==0x80000000 and b==0xffffffff) else 33))
    words += [0xc00022f3,0x10000237,7<<20|4<<15|2<<12|4<<7|0x23,0x10500073]
    payload=struct.pack('<'+'I'*len(words),*words)
    ident=b'\x7fELF'+bytes([1,1,1])+bytes(9)
    header=struct.pack('<16sHHIIIIIHHHHHH',ident,2,243,1,0x80000000,52,0,0,52,32,1,0,0,0)
    phdr=struct.pack('<IIIIIIII',1,256,0x80000000,0x80000000,len(payload),len(payload),5,4)
    return (header+phdr).ljust(256,b'\0')+payload,rows
def main():
    p=argparse.ArgumentParser();p.add_argument('--observer',type=Path,required=True);p.add_argument('--original',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    require(not a.out.exists(),'fresh output required');a.out.mkdir(parents=True)
    elf,rows=program();(a.out/'input.elf').write_bytes(elf);(a.out/'vectors.json').write_text(json.dumps(rows,indent=2)+'\n')
    records=[]
    for mode,exe in [('original',a.original),('off',a.observer),('on',a.observer)]:
        out=a.out/mode;out.mkdir()
        cmd=[str(exe),f'+elf={a.out}/input.elf','+max-cycles=10000','+core-period-ps=10000',
             '+imem-response-ps=10000','+imem-interval-ps=10000','+dmem-response-ps=10000',
             f'+profile-core-roi={out}/profile.json',f'+trace={out}/trace.log']
        if mode=='on':cmd.append(f'+observe-div={out}/observer.json')
        with (out/'dut.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
        require(r.returncode==0 and 'Exit status    : PASS (0)' in (out/'dut.log').read_text(),'control result failed')
        require('TRAP' not in (out/'dut.log').read_text(),'control trap')
        records.append(dict(mode=mode,command=cmd,returncode=r.returncode,
                            outputs_sha256={p.name:sha(p) for p in out.iterdir()}))
    for file in ['profile.json','trace.log']:
        require(len({sha(a.out/m/file) for m in ['original','off','on']})==1,'observer changed '+file)
    normalized=[]
    for mode in ['original','off','on']:
        text=(a.out/mode/'dut.log').read_text()
        line='[Simulator] Commit trace logging enabled: '+str(a.out/mode/'trace.log')
        require(text.count(line+'\n')==1,'unexpected trace-path log line')
        normalized.append(text.replace(line,'[Simulator] Commit trace logging enabled: <verified trace>',1))
    require(len(set(normalized))==1,'observer changed log after exact trace-path normalization')
    obs=json.loads((a.out/'on/observer.json').read_text())
    require(obs['counts']['accepted_issues']==48 and obs['counts']['issued_in_roi_completed_in_roi']==48,'control issue count')
    require(all(obs['counts']['opcode_'+str(op)]==12 for op in range(4,8)),'control opcodes')
    expected={str(k):v for k,v in collections.Counter(r['latency'] for r in rows).items()}
    require(obs['histograms']['issue_to_first_valid']==expected and obs['histograms']['issue_to_grant']==expected,'control latency')
    require(obs['counts'].get('completion_blocked_cycles',0)==0,'divider completion should have highest priority')
    # Each disjoint operand category must be exercised by real instructions.
    require(all(obs['counts'].get('operands_'+k,0)>0 for k in ['existing_zero','existing_overflow','abs_divisor_one','abs_dividend_less','remaining_power_two','general']),'missing operand control')
    report=dict(passed=True,scope='48 instruction hardware controls; original/off/on ordered traces and profiles identical',
                observer_sha256=sha(a.observer),original_sha256=sha(a.original),source_sha256=sha(Path(__file__)),
                elf_sha256=sha(a.out/'input.elf'),vectors_sha256=sha(a.out/'vectors.json'),records=records,observer=obs)
    (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print('DIV hardware controls PASS',expected)
if __name__=='__main__':main()
