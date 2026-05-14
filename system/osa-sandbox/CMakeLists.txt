cmake_minimum_required(VERSION 3.20)
project(osa-sandbox VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(osa-sandbox
    src/main.cpp
    src/sandbox.cpp
    src/policy.cpp
)

install(TARGETS osa-sandbox DESTINATION bin)
