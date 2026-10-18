"""Frozen post-LSU input identities; incomplete sets never become valid scores."""
import hashlib
import json
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'baselines/ap5b-post-lsu-v1/manifest.json'
FP=('fir','iir','fft','pid','gemm','bicg','cholesky','svm')
EM=('aha-mont64','crc32','cubic','edn','huffbench','matmult-int','minver','nbody','nettle-aes','nettle-sha256','nsichneu','picojpeg','qrduino','sglib-combined','slre','st','statemate','ud','wikisort')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path=MANIFEST):return json.loads(path.read_text())
def validate(manifest):
    rows=manifest['workloads'];keys=[(r['family'],r['name']) for r in rows]
    expected={('embench',n) for n in EM}|{('fp32',n) for n in FP}
    if len(keys)!=27 or set(keys)!=expected:raise ValueError('expected complete unique Embench19 + FP32 eight set')
    if manifest['memory']['policy']!='fixed_absolute_time':raise ValueError('memory time policy changed')
    for row in rows:
        if row['reference_cycles']<=0 or len(row['elf_sha256'])!=64:raise ValueError('invalid baseline metric/identity')
        if row['family']=='fp32' and row['group']!=('dsp' if row['name'] in FP[:4] else 'matrix_ml'):raise ValueError('FP32 group changed')
    if sum(r.get('checked_values',0) for r in rows)!=3629:raise ValueError('FP32 output denominator changed')
    return rows

def check_rtl(manifest):
    files=[p for p in (ROOT/'sim/scripts/rv32_ooo_core.f').read_text().splitlines() if p.strip() and not p.startswith('#')]
    if set(files)!=set(manifest['rtl_files_sha256']):raise ValueError('RTL file set changed')
    for name,expected in manifest['rtl_files_sha256'].items():
        if sha(ROOT/name)!=expected:raise ValueError('baseline RTL changed: '+name)

def image_end(elf):
    data=elf.read_bytes()
    if data[:7]!=b'\x7fELF\x01\x01\x01':raise ValueError('expected little-endian ELF32')
    offset=struct.unpack_from('<I',data,28)[0];size,count=struct.unpack_from('<HH',data,42)
    ends=[]
    for i in range(count):
        ptype,_,vaddr,_,_,memsz,_,_=struct.unpack_from('<8I',data,offset+i*size)
        if ptype==1:ends.append(vaddr+memsz)
    if not ends:raise ValueError('ELF has no loadable segments')
    return max(ends)
