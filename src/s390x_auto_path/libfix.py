import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
import glob
import shutil

def get_installed_package_path(pkg_name):
    try:
        out = subprocess.check_output(['pip','show',pkg_name], text=True)
        for line in out.splitlines():
            if line.startswith('Location:'):
                loc = line.split(':',1)[1].strip()
                return Path(loc) / pkg_name.replace('-', '_')
    except subprocess.CalledProcessError:
        return None

def find_subdirs(base_dir: Path):
    paths = {'include': [], 'lib': [], 'lib64': [], 'pkgconfig': [], 'cmake': [], 'bin': []}
    base = Path(base_dir)
    if not base.exists():
        return paths
    for root, dirs, _ in os.walk(base):
        for d in dirs:
            full = Path(root) / d
            name = d.lower()
            if name == 'include':
                paths['include'].append(str(full))
                for subroot, subdirs, _ in os.walk(full):
                    for sd in subdirs:
                        paths['include'].append(str(Path(subroot)/sd))
            elif name == 'lib':
                paths['lib'].append(str(full))
            elif name == 'lib64':
                paths['lib64'].append(str(full))
            elif name == 'pkgconfig':
                paths['pkgconfig'].append(str(full))
            elif 'cmake' in name:
                paths['cmake'].append(str(full))
            elif name == 'bin':
                paths['bin'].append(str(full))
    # dedupe preserving order
    for k in paths:
        seen=set(); paths[k]=[p for p in paths[k] if not (p in seen or seen.add(p))]
    return paths

def _link_if_missing(src: Path, dst: Path):
    try:
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to(src)
    except Exception:
        pass

def fix_lib_layout(base_path):
    base = Path(base_path)
    # if it's a wheel file path, extract temporarily
    if base.is_file() and base.suffix == '.whl':
        tmp = Path(tempfile.mkdtemp(prefix='s390x_whl_'))
        with zipfile.ZipFile(base, 'r') as zf:
            zf.extractall(tmp)
        base = tmp

    lib = base / 'lib'
    lib64 = base / 'lib64'

    if lib.exists() and lib64.exists():
        # cross-link missing so files
        for so in lib.rglob('*.so*'):
            target = lib64 / so.relative_to(lib)
            _link_if_missing(so, target)
        for so in lib64.rglob('*.so*'):
            target = lib / so.relative_to(lib64)
            _link_if_missing(so, target)
        return base

    if lib.exists() and not lib64.exists():
        for so in lib.rglob('*.so*'):
            dst = lib64 / so.relative_to(lib)
            _link_if_missing(so, dst)
        return base

    if lib64.exists() and not lib.exists():
        for so in lib64.rglob('*.so*'):
            dst = lib / so.relative_to(lib64)
            _link_if_missing(so, dst)
        return base

    return base

def extract_wheel_to_temp(whl_path):
    tmp = Path(tempfile.mkdtemp(prefix='s390x_whl_'))
    with zipfile.ZipFile(str(whl_path),'r') as zf:
        zf.extractall(tmp)
    return tmp

def repack_wheel(extracted_dir: Path, original_whl_path):
    out_whl = Path(original_whl_path)
    tmpname = out_whl.parent / (out_whl.name + '.fixed')
    with zipfile.ZipFile(tmpname, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(extracted_dir.rglob('*')):
            arc = f.relative_to(extracted_dir)
            if f.is_file():
                zf.write(f, arc)
    tmpname.replace(out_whl)

def rewrite_cmake_paths(base_dir: Path):
    for cm in base_dir.rglob('*.cmake'):
        try:
            text = cm.read_text()
            if '/lib/' in text and '/lib64/' not in text:
                if (base_dir / 'lib64').exists():
                    new = text.replace('/lib/', '/lib64/')
                    cm.write_text(new)
        except Exception:
            pass

def fix_target(target, rewrite_cmake=False):
    p = Path(target)
    if p.suffix == '.whl':
        base = extract_wheel_to_temp(p)
        fix_lib_layout(base)
        if rewrite_cmake:
            rewrite_cmake_paths(base)
        repack_wheel(base, p)
    else:
        fix_lib_layout(p)
        if rewrite_cmake:
            rewrite_cmake_paths(p)

def _has_patchelf():
    try:
        subprocess.check_output(['patchelf','--version'], stderr=subprocess.STDOUT)
        return True
    except Exception:
        return False

def _patch_rpath_file(file_path: Path, rpath: str):
    if not _has_patchelf():
        print('[WARN] patchelf not available; skipping')
        return
    try:
        subprocess.check_call(['patchelf','--set-rpath', rpath, str(file_path)])
        print(f'[OK] set-rpath {rpath} -> {file_path}')
    except Exception as e:
        print(f'[ERR] patchelf failed for {file_path}: {e}')

def patch_rpath_target(target, rpath=''):
    p = Path(target)
    if p.suffix == '.whl':
        base = extract_wheel_to_temp(p)
        if not rpath:
            rpath = '/usr/lib64'
        for so in base.rglob('*.so*'):
            _patch_rpath_file(so, rpath)
        repack_wheel(base, p)
    else:
        base = p
        if not rpath:
            rpath = '/usr/lib64'
        for so in base.rglob('*.so*'):
            _patch_rpath_file(so, rpath)

SITE_CUSTOMIZE = r"""import sysconfig, os, glob
vars = sysconfig._CONFIG_VARS
default_libdir = vars.get('LIBDIR', '/usr/lib')
lib_candidates = [default_libdir, default_libdir.replace('/lib','/lib64')]
selected = None
for candidate in lib_candidates:
    if os.path.exists(candidate):
        so_files = glob.glob(os.path.join(candidate, '**', '*.so*'), recursive=True)
        if so_files:
            selected = candidate
            break
if not selected:
    for candidate in lib_candidates:
        if os.path.exists(candidate):
            selected = candidate
            break
if not selected:
    selected = default_libdir
vars['LIBDIR'] = selected
os.environ['LIBDIR'] = selected
"""

def inject_sitecustomize_into_venv(venv_path: Path):
    pybin = venv_path / 'bin' / 'python'
    if not pybin.exists():
        print('[ERR] python not found in venv')
        return
    ver = subprocess.check_output([str(pybin), '-c', "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"], text=True).strip()
    dest = venv_path / 'lib64' / f'python{ver}' / 'site-packages'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / 'sitecustomize.py').write_text(SITE_CUSTOMIZE)
    print(f'[OK] injected sitecustomize.py into {dest}')
