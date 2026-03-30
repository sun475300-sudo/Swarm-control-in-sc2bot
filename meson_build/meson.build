# Meson build file for SC2 Zerg Bot – cross-platform C/C++ modules
# Builds: combat_sim shared library, pathfinder, and CLI test harness
# Usage: meson setup builddir && cd builddir && ninja

project('sc2_zerg_bot_cpp', 'cpp',
  version          : '1.0.0',
  default_options  : ['cpp_std=c++20', 'warning_level=2', 'optimization=2'],
  license          : 'MIT',
)

# ── Dependencies ─────────────────────────────────────────────────────────────
thread_dep = dependency('threads')
pybind11_dep = dependency('pybind11', required : false)

# ── Include directories ──────────────────────────────────────────────────────
inc = include_directories('include')

# ── Combat simulator shared library ──────────────────────────────────────────
combat_sim_lib = shared_library(
  'combat_sim',
  sources : [
    'src/combat_sim.cpp',
    'src/unit_stats.cpp',
    'src/damage_model.cpp',
  ],
  include_directories : inc,
  dependencies        : [thread_dep],
  install             : true,
)

# ── Pathfinder (influence-map A* for Zerg movement) ─────────────────────────
pathfinder_lib = static_library(
  'pathfinder',
  sources : ['src/pathfinder.cpp', 'src/threat_map.cpp'],
  include_directories : inc,
)

# ── CLI test harness ─────────────────────────────────────────────────────────
executable(
  'sc2_sim_cli',
  sources : ['src/main_cli.cpp'],
  link_with           : [combat_sim_lib, pathfinder_lib],
  include_directories : inc,
  dependencies        : [thread_dep],
  install             : true,
)

# ── Unit tests (using Catch2) ─────────────────────────────────────────────────
catch2_dep = dependency('catch2-with-main', required : get_option('tests'))

if catch2_dep.found()
  test_exe = executable(
    'sc2_cpp_tests',
    sources : [
      'tests/test_combat_sim.cpp',
      'tests/test_pathfinder.cpp',
    ],
    link_with           : [combat_sim_lib, pathfinder_lib],
    include_directories : inc,
    dependencies        : [catch2_dep],
  )
  test('sc2 cpp unit tests', test_exe)
endif
