Example usage with aws-c-cal:

1. Install s390x-auto-path
2. Generate env: s390x-auto-path env generate build_env.sh aws-lc aws-c-common
3. source build_env.sh
4. Run your build.sh (which now picks right lib/lib64 and CMake modules)
