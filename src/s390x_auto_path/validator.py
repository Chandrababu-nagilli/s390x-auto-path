import subprocess, zipfile, tempfile
from pathlib import Path

def _extract_if_wheel(target):
    p = Path(target)
    if p.suffix == '.whl':
        tmp = Path(tempfile.mkdtemp(prefix='s390x_validate_'))
        with zipfile.ZipFile(str(p),'r') as zf:
            zf.extractall(tmp)
        return tmp
    return p

def run_validate(target):
    base = _extract_if_wheel(target)
    print(f'[INFO] validating: {base}')
    issues = 0
    for so in base.rglob('*.so*'):
        try:
            out = subprocess.check_output(['ldd', str(so)], stderr=subprocess.STDOUT, text=True)
        except subprocess.CalledProcessError as e:
            out = e.output
        if 'not found' in out:
            print(f'[MISSING] {so} -> {out.strip()}'); issues += 1
        for line in out.splitlines():
            if '=>' in line:
                parts = line.split('=>',1)[1].strip().split()
                if parts:
                    libpath = parts[0]
                    if libpath.startswith('/lib/') and not libpath.startswith('/lib64/'):
                        print(f'[WARN] {so} links to non-lib64: {libpath}'); issues += 1
    if issues==0: print('[OK] No obvious issues')
    else: print(f'[RESULT] {issues} issues detected')
