cmake_minimum_required(VERSION 3.20)
project(osa-updater VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(osa-updater
    src/main.cpp
    src/updater.cpp
)

install(TARGETS osa-updater DESTINATION bin)
