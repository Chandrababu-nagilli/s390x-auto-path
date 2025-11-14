#!/usr/bin/env python3
import argparse
from . import libfix, envgen, validator
from pathlib import Path

def main():
    p = argparse.ArgumentParser(prog='s390x-auto-path')
    sub = p.add_subparsers(dest='cmd', required=True)

    scan = sub.add_parser('scan', help='Scan installed packages (pip show pkg) and print paths')
    scan.add_argument('packages', nargs='+')

    env = sub.add_parser('env', help='Generate environment flags for installed packages')
    env.add_argument('packages', nargs='+')

    fix = sub.add_parser('fix', help='Fix installed package dirs or wheels')
    fix.add_argument('targets', nargs='+')
    fix.add_argument('--rewrite-cmake', action='store_true')

    validate = sub.add_parser('validate', help='Validate .so links')
    validate.add_argument('targets', nargs='+')

    patch = sub.add_parser('patch-rpath', help='Patch rpath using patchelf')
    patch.add_argument('targets', nargs='+')
    patch.add_argument('--rpath', default='')

    inject = sub.add_parser('inject-sitecustomize', help='Inject sitecustomize into venv')
    inject.add_argument('venv')

    args = p.parse_args()

    if args.cmd == 'scan':
        for pkg in args.packages:
            base = libfix.get_installed_package_path(pkg)
            print(f"{pkg}: {base}")
    elif args.cmd == 'env':
        combined = {'include': [], 'lib': [], 'lib64': [], 'pkgconfig': [], 'cmake': [], 'bin': []}
        for pkg in args.packages:
            base = libfix.get_installed_package_path(pkg)
            if not base:
                print(f"[WARN] package not found: {pkg}")
                continue
            libfix.fix_lib_layout(base)
            parts = libfix.find_subdirs(base)
            for k,v in parts.items():
                combined[k].extend(v)
        env = envgen.build_env_flags(combined)
        for k,v in env.items():
            print(f"export {k}='{v}'")
    elif args.cmd == 'fix':
        for t in args.targets:
            libfix.fix_target(t, rewrite_cmake=args.rewrite_cmake)
    elif args.cmd == 'validate':
        for t in args.targets:
            validator.run_validate(t)
    elif args.cmd == 'patch-rpath':
        for t in args.targets:
            libfix.patch_rpath_target(t, args.rpath)
    elif args.cmd == 'inject-sitecustomize':
        libfix.inject_sitecustomize_into_venv(Path(args.venv))
