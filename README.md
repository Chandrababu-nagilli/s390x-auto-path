# s390x-auto-path

`s390x-auto-path` is a utility to automatically resolve, fix and validate shared library layouts (`lib` vs `lib64`) on s390x systems and similar platforms. It helps packaging workflows and build systems (CMake, autotools, pip wheels, etc.) by creating compatibility symlinks, generating environment flags, validating `.so` dependencies, optionally patching rpaths, and injecting sitecustomize logic into virtualenvs.

## Features

* Detect `lib` vs `lib64` and choose best fit (prefers real .so presence).
* Create compatibility symlinks when packages use mixed layouts.
* Generate recommended environment variables: `CFLAGS`, `LDFLAGS`, `LD_LIBRARY_PATH`, `PKG_CONFIG_PATH`, `CMAKE_PREFIX_PATH`.
* Validate `.so` dependencies using `ldd` and warn about missing or non-`/lib64` absolute links.
* Optional `patchelf`-based rpath patching.
* Inject `sitecustomize.py` to propagate `LIBDIR` detection inside virtualenvs.
* CLI: `scan`, `env`, `fix`, `validate`, `patch-rpath`, `inject-sitecustomize`.

## Quick start

```bash
# Editable install (development)
git clone <repo>
cd s390x-auto-path
pip install -e .

# Scan installed packages
s390x-auto-path scan aws-lc aws-c-common

# Fix installed packages or wheel files
s390x-auto-path fix /path/to/aws_lc
s390x-auto-path fix /path/to/aws_c_common-1.0.0-py3-none-any.whl --rewrite-cmake

# Generate env flags to export before building
s390x-auto-path env aws-lc aws-c-common

# Validate a package/wheel
s390x-auto-path validate /path/to/package_or_wheel

# Inject sitecustomize into a virtualenv
s390x-auto-path inject-sitecustomize /path/to/venv
```

## CI integration

Add `pip install s390x-auto-path` to your base image or CI toolchain and run `s390x-auto-path fix ...` before building your CMake/autotools projects to ensure consistent library layout.

## License

Apache-2.0 (see LICENSE)
