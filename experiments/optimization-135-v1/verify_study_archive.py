#!/usr/bin/env python3
"""Verify stored/decoded files and independently compare archived observer runs."""
import argparse,gzip,hashlib,json
from pathlib import Path
def require(ok,msg):
    if not ok:raise ValueError(msg)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('archive',type=Path);a=ap.parse_args();root=a.archive
    inv=json.loads((root/'copy-inventory.json').read_text());index={}
    for r in inv['records']:
        p=root/r['destination'];require(p.resolve().is_relative_to(root.resolve()),'unsafe inventory path')
        raw=p.read_bytes();require(sha(raw)==r['stored_sha256'] and len(raw)==r['stored_bytes'],'stored payload changed')
        decoded=gzip.decompress(raw) if r['encoding']=='gzip' else raw
        require(sha(decoded)==r['source_sha256'] and len(decoded)==r['source_bytes'],'decoded payload changed')
        require(r['destination'] not in index,'duplicate destination');index[r['destination']]=decoded
    def data(name):return index.get(name,index.get(name+'.gz'))
    def js(name):return json.loads(data(name))
    aliases=json.loads((root/'input-aliases.json').read_text())
    for variant,run in [('baseline','observer-v2'),('A','observer-v2'),('B','observer-v1')]:
        prefix='runs/'+run+'/'+variant;summary=js('references/'+variant+'/summary.json');build=js(prefix+'/build.json')
        require(sha(data(prefix+'/observer'))==build['simulator_sha256'],'observer binary changed')
        for p,h in build['inputs_sha256'].items():require(sha(data(aliases[p]))==h,'observer source mismatch')
        require(summary['passed'] and len(summary['records'])==27,'incomplete reference suite')
        for r in summary['records']:
            ref='references/'+variant+'/'+r['family']+'/'+r['name']
            for name,field in [('input.elf','elf_sha256'),('dut.log',None),('profile.json','profile_sha256'),('memory.json','memory_audit_sha256')]:
                require(sha(data(ref+'/'+name))==(r[field] if field else r['execution']['log_sha256']),'changed frozen reference')
            if r['family']!='fp32' and r['name']!='minver':continue
            case=prefix+'/'+r['name'];old_elf=next(x[5:] for x in r['execution']['command'] if x.startswith('+elf='))
            comparison=js(case+'/comparison.json')
            for mode in ['off','on']:
                require(data(case+'/'+mode+'/profile.json')==data(ref+'/profile.json'),'changed profile')
                require(data(case+'/'+mode+'/memory.json')==data(ref+'/memory.json'),'changed memory audit')
                command=comparison['modes'][mode]['command'];elf=next(x[5:] for x in command if x.startswith('+elf='))
                old_line='  ELF binary     : '+old_elf+'\n';new_line='  ELF binary     : '+elf+'\n'
                old=data(ref+'/dut.log').decode();new=data(case+'/'+mode+'/dut.log').decode()
                require(old.count(old_line)==1 and new.count(new_line)==1,'ELF path identity line missing')
                require(old.replace(old_line,'<ELF>\n',1)==new.replace(new_line,'<ELF>\n',1),'changed numerical/cycle output')
            require(data(case+'/off/dut.log')==data(case+'/on/dut.log'),'observer off/on differs')
    review=js('runs/study-review.json');require(review['passed'] and review['observer_case_pairs']==27 and review['retained_profiles_checked']==81,'incomplete diagnostic review')
    for r in review['records']:
        run='observer-v1' if r['variant']=='B' else 'observer-v2'
        p='runs/'+run+'/'+r['variant']+'/'+r['name']+'/on/observer.json'
        require(sha(data(p))==r['observer_sha256'],'review bound to different observer result')
    controls=js('runs/controls-v1/summary.json');total=0
    for r in controls['records']:
        case='runs/controls-v1/'+str(r['nops']);require(sha(data(case+'/input.elf'))==r['elf_sha256'],'control ELF changed')
        for mode in ['original','off','on']:
            require(sha(data(case+'/'+mode+'/trace.log'))==r['trace_sha256'],'control ordered trace differs')
            require(b'Exit status    : PASS (0)' in data(case+'/'+mode+'/dut.log'),'control failed')
        require(js(case+'/on/observer.json')==r['observer'],'control counts changed')
        total+=r['observer']['counts'].get('divsqrt_completion_blocked',0)
    require(total>0 and total==review['hardware_contention_cycles'],'no actual contention control')
    print(json.dumps(dict(passed=True,stored_and_decoded_files=len(index),reference_cases=81,observer_pairs=27,hardware_controls=6,physical_A_qualified=False),indent=2))
if __name__=='__main__':main()
