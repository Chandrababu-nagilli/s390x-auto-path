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
    if base is None:
        return base
    if base.is_file() and base.suffix == '.whl':
        tmp = Path(tempfile.mkdtemp(prefix='s390x_whl_'))
        with zipfile.ZipFile(base, 'r') as zf:
            zf.extractall(tmp)
        base = tmp

    lib = base / 'lib'
    lib64 = base / 'lib64'

    if lib.exists() and lib64.exists():
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
if not selected:
    for candidate in lib_candidates:
        if os.path.exists(candidate):
            selected = candidate
if not selected:
    selected = default_libdir
vars['LIBDIR'] = selected
os.environ['LIBDIR'] = selected
"""

def find_deep_cmake_dirs_from_packages(pkg_paths):
    """Search deeper inside package folders for cmake directories, including nonstandard locations like
    wheel_payload/lib64/aws-c-common/cmake. Returns list of cmake dirs to add to CMAKE_PREFIX_PATH."""
    found=[]
    for p in (pkg_paths or []):
        if not p:
            continue
        base = Path(p)
        # look for cmake dirs under lib and lib64 recursively, include wheel_payload
        candidates = list(base.rglob('**/cmake'))
        for c in candidates:
            # prefer directories that contain AwsCFlags.cmake or AwsFindPackage.cmake
            names = [x.name for x in c.iterdir() if x.is_file()]
            if any(n.lower().startswith('awscflags') or n.lower().startswith('awsfindpackage') or 'aws' in n.lower() for n in names):
                found.append(str(c))
            else:
                # keep reasonable cmake dirs too
                found.append(str(c))
    # dedupe preserving order
    seen=set(); out=[]
    for x in found:
        if x not in seen:
            seen.add(x); out.append(x)
    return out
