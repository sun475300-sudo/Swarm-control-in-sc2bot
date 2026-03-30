cmake_minimum_required(VERSION 3.20)
project(WickedZerg)

set(CMAKE_CXX_STANDARD 17)

add_executable(bot_sim src/bot_sim.cpp)
target_link_libraries(bot_sim pthread)

find_package(OpenSSL REQUIRED)
