cmake_minimum_required(VERSION 3.20)
project(osa-compositor VERSION 0.1.0 LANGUAGES C)

find_package(PkgConfig REQUIRED)

pkg_check_modules(WLROOTS REQUIRED wlroots-0.18)
pkg_check_modules(WAYLAND_SERVER REQUIRED wayland-server)
pkg_check_modules(WAYLAND_PROTOCOLS REQUIRED wayland-protocols)
pkg_check_modules(XKBCOMMON REQUIRED xkbcommon)
pkg_check_modules(PIXMAN REQUIRED pixman-1)

add_executable(osa-compositor
    src/main.c
    src/server.c
    src/output.c
    src/input.c
    src/view.c
    src/ai_panel.c
    src/config.c
)

target_include_directories(osa-compositor PRIVATE
    ${WLROOTS_INCLUDE_DIRS}
    ${WAYLAND_SERVER_INCLUDE_DIRS}
    ${XKBCOMMON_INCLUDE_DIRS}
    ${PIXMAN_INCLUDE_DIRS}
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(osa-compositor
    ${WLROOTS_LIBRARIES}
    ${WAYLAND_SERVER_LIBRARIES}
    ${XKBCOMMON_LIBRARIES}
    ${PIXMAN_LIBRARIES}
)

target_compile_definitions(osa-compositor PRIVATE
    WLR_USE_UNSTABLE
    _POSIX_C_SOURCE=200809L
)

target_compile_options(osa-compositor PRIVATE -Wall -Wextra -Wno-unused-parameter)

install(TARGETS osa-compositor DESTINATION bin)
