"""Run using pinned openroad -python; inspect OpenDB without changing it."""
from pathlib import Path
import gzip, hashlib, json
import odb
root=Path('/workspace');out=root/'build/experiments/lsu-b-diagnosis-v1'
records=[]
for candidate in ('baseline','A','B'):
    source=out/'replays'/f'{candidate}-synthesis.odb'
    dest=out/f'{candidate}-synthesis-connectivity.jsonl.gz'
    assert not dest.exists()
    db=odb.dbDatabase.create()
    odb.read_db(db,str(source))
    block=db.getChip().getBlock()
    count=0
    with gzip.open(dest,'xt') as f:
        for inst in block.getInsts():
            pins={}
            for pin in inst.getITerms():
                if str(pin.getSigType()) in ('POWER','GROUND'):continue
                net=pin.getNet()
                if net is not None:pins[pin.getMTerm().getName()]=net.getName()
            f.write(json.dumps([inst.getName(),inst.getMaster().getName(),pins],separators=(',',':'))+'\n')
            count+=1
    records.append(dict(candidate=candidate,odb_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),export=str(dest.relative_to(root)),export_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),instances=count))
    odb.dbDatabase.destroy(db)
    print(candidate,count,flush=True)
(out/'synthesis-connectivity-export.json').write_text(json.dumps(dict(read_only=True,records=records),indent=2)+'\n')
