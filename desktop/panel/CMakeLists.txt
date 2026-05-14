cmake_minimum_required(VERSION 3.20)
project(osa-panel VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)

pkg_check_modules(GTK4 REQUIRED gtk4)
pkg_check_modules(LAYER_SHELL REQUIRED gtk4-layer-shell-0)

add_executable(osa-panel
    src/main.cpp
    src/panel_window.cpp
    src/ai_indicator.cpp
    src/app_launcher.cpp
)

target_include_directories(osa-panel PRIVATE
    ${GTK4_INCLUDE_DIRS}
    ${LAYER_SHELL_INCLUDE_DIRS}
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(osa-panel
    ${GTK4_LIBRARIES}
    ${LAYER_SHELL_LIBRARIES}
)

install(TARGETS osa-panel DESTINATION bin)
