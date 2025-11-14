# s390x-auto-path v2

Upgraded version adds env generation that writes a `build_env.sh` you can `source` before building.

Usage examples:

  s390x-auto-path scan aws-lc aws-c-common
  s390x-auto-path env generate build_env.sh aws-lc aws-c-common
  source build_env.sh
  sh build.sh

