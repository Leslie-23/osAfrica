cmake_minimum_required(VERSION 3.20)
project(osa-terminal VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)

pkg_check_modules(GTK4 REQUIRED gtk4)
pkg_check_modules(VTE REQUIRED vte-2.91-gtk4)
pkg_check_modules(LAYER_SHELL REQUIRED gtk4-layer-shell-0)

add_executable(osa-terminal
    src/main.cpp
    src/terminal.cpp
    src/ai_sidebar.cpp
)

target_include_directories(osa-terminal PRIVATE
    ${GTK4_INCLUDE_DIRS}
    ${VTE_INCLUDE_DIRS}
    ${LAYER_SHELL_INCLUDE_DIRS}
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(osa-terminal
    ${GTK4_LIBRARIES}
    ${VTE_LIBRARIES}
    ${LAYER_SHELL_LIBRARIES}
)

install(TARGETS osa-terminal DESTINATION bin)
