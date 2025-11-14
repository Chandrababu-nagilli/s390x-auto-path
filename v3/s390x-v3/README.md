# s390x-auto-path v3

This v3 improves CMake module discovery (deep scan), so special layouts like
`wheel_payload/lib64/aws-c-common/cmake` are detected automatically.

Usage:

  pip install -e .
  s390x-auto-path env generate build_env.sh aws-lc aws-c-common
  source build_env.sh
  sh build.sh

This will auto-populate CMAKE_PREFIX_PATH with directories that actually contain the AWS cmake modules.
