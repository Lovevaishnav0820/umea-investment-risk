"""Writing JSON, CSV and NumPy files, with SHA-256 hashes of files and raw array bytes."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from .scenarios import raw_hash

def json_default(x):
    if isinstance(x,np.ndarray):return x.tolist()
    if isinstance(x,np.generic):return x.item()
    if isinstance(x,Path):return str(x)
    raise TypeError(type(x).__name__)

def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,default=json_default,allow_nan=False)+'\n')

def write_csv(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=keys);w.writeheader();w.writerows(rows)

def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while block:=f.read(1024*1024):h.update(block)
    return h.hexdigest()

def save_arrays(path,**arrays):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(path,**arrays)
    return dict(file=str(path),file_sha256=file_hash(path),arrays={k:dict(shape=list(np.asarray(a).shape),
        dtype=str(np.asarray(a).dtype),raw_sha256=raw_hash(a)) for k,a in arrays.items()})
