def build_env_flags(all_paths):
    include_paths = all_paths.get('include', [])
    lib_paths = (all_paths.get('lib', []) or []) + (all_paths.get('lib64', []) or [])
    pkgconfig_paths = all_paths.get('pkgconfig', [])
    cmake_paths = all_paths.get('cmake', [])
    env={}
    if include_paths:
        env['CFLAGS'] = ' '.join(f'-I{x}' for x in include_paths)
        env['CXXFLAGS'] = env['CFLAGS']
    if lib_paths:
        env['LDFLAGS'] = ' '.join(f'-L{x}' for x in lib_paths)
        env['LD_LIBRARY_PATH'] = ':'.join(lib_paths)
    if pkgconfig_paths:
        env['PKG_CONFIG_PATH'] = ':'.join(pkgconfig_paths)
    if cmake_paths:
        env['CMAKE_PREFIX_PATH'] = ':'.join(cmake_paths)
    return env
