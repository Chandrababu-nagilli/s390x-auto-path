Example: integrating into build.sh (append before cmake call)
-----------------------------------------------------------
# generate env
s390x-auto-path env generate build_env.sh aws-lc aws-c-common
source build_env.sh

# now run cmake
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=ON \
  -DUSE_OPENSSL=OFF \
  -DCMAKE_PREFIX_PATH="$CMAKE_PREFIX_PATH" \
  -DCMAKE_LIBRARY_PATH="$LDFLAGS" \
  -DCMAKE_INCLUDE_PATH="$CFLAGS"
