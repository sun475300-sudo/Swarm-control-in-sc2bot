cmake_minimum_required(VERSION 3.22)
project(sc2_accel VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ── Options ──────────────────────────────────────────────────────────────────
option(SC2_ACCEL_ENABLE_TESTS "Build unit tests" ON)
option(SC2_ACCEL_ENABLE_ASAN  "Enable AddressSanitizer in Debug"  OFF)

# ── Dependencies ─────────────────────────────────────────────────────────────
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 REQUIRED)
find_package(Threads REQUIRED)

# ── Source files ─────────────────────────────────────────────────────────────
set(ACCEL_SOURCES
    src/combat_sim.cpp       # Fast combat damage calculation
    src/pathfinder.cpp       # Influence-map pathfinding for Zerg swarm
    src/resource_model.cpp   # Mineral/gas harvest rate prediction
    src/threat_map.cpp       # Enemy threat zone computation
)

# ── Shared library (loaded by Python via pybind11) ────────────────────────────
pybind11_add_module(sc2_accel ${ACCEL_SOURCES} src/bindings.cpp)

target_include_directories(sc2_accel PRIVATE include/)

target_compile_options(sc2_accel PRIVATE
    $<$<CONFIG:Release>:-O3 -march=native -DNDEBUG>
    $<$<CONFIG:Debug>:-g -Wall -Wextra>
)

if(SC2_ACCEL_ENABLE_ASAN AND CMAKE_BUILD_TYPE STREQUAL "Debug")
    target_compile_options(sc2_accel PRIVATE -fsanitize=address)
    target_link_options(sc2_accel PRIVATE -fsanitize=address)
endif()

target_link_libraries(sc2_accel PRIVATE Threads::Threads)

# ── Tests ─────────────────────────────────────────────────────────────────────
if(SC2_ACCEL_ENABLE_TESTS)
    enable_testing()
    find_package(GTest REQUIRED)
    add_executable(sc2_accel_tests
        tests/test_combat_sim.cpp
        tests/test_pathfinder.cpp
        ${ACCEL_SOURCES}
    )
    target_include_directories(sc2_accel_tests PRIVATE include/)
    target_link_libraries(sc2_accel_tests PRIVATE GTest::gtest_main Threads::Threads)
    include(GoogleTest)
    gtest_discover_tests(sc2_accel_tests)
endif()

# ── Install ───────────────────────────────────────────────────────────────────
install(TARGETS sc2_accel LIBRARY DESTINATION ${Python3_SITEARCH}/sc2_accel)
