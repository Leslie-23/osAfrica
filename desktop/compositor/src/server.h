/*
 * osa-compositor — AI-native Wayland compositor for osAfrica.
 * Based on wlroots, inspired by labwc/tinywl.
 */

#ifndef OSA_SERVER_H
#define OSA_SERVER_H

#include <wayland-server-core.h>
#include <wlr/backend.h>
#include <wlr/render/allocator.h>
#include <wlr/render/wlr_renderer.h>
#include <wlr/types/wlr_compositor.h>
#include <wlr/types/wlr_cursor.h>
#include <wlr/types/wlr_keyboard.h>
#include <wlr/types/wlr_output.h>
#include <wlr/types/wlr_output_layout.h>
#include <wlr/types/wlr_scene.h>
#include <wlr/types/wlr_seat.h>
#include <wlr/types/wlr_subcompositor.h>
#include <wlr/types/wlr_xcursor_manager.h>
#include <wlr/types/wlr_xdg_shell.h>
#include <xkbcommon/xkbcommon.h>

struct osa_server {
    struct wl_display *wl_display;
    struct wlr_backend *backend;
    struct wlr_renderer *renderer;
    struct wlr_allocator *allocator;
    struct wlr_scene *scene;
    struct wlr_scene_output_layout *scene_layout;

    struct wlr_xdg_shell *xdg_shell;
    struct wl_listener new_xdg_toplevel;
    struct wl_listener new_xdg_popup;
    struct wl_list toplevels;

    struct wlr_cursor *cursor;
    struct wlr_xcursor_manager *cursor_mgr;
    struct wl_listener cursor_motion;
    struct wl_listener cursor_motion_absolute;
    struct wl_listener cursor_button;
    struct wl_listener cursor_axis;
    struct wl_listener cursor_frame;

    struct wlr_seat *seat;
    struct wl_listener new_input;
    struct wl_listener request_cursor;
    struct wl_listener request_set_selection;
    struct wl_list keyboards;

    struct wlr_output_layout *output_layout;
    struct wl_list outputs;
    struct wl_listener new_output;

    /* AI panel state */
    int ai_panel_visible;
    struct wlr_scene_tree *ai_panel_tree;
};

struct osa_output {
    struct wl_list link;
    struct osa_server *server;
    struct wlr_output *wlr_output;
    struct wl_listener frame;
    struct wl_listener request_state;
    struct wl_listener destroy;
};

struct osa_toplevel {
    struct wl_list link;
    struct osa_server *server;
    struct wlr_xdg_toplevel *xdg_toplevel;
    struct wlr_scene_tree *scene_tree;

    struct wl_listener map;
    struct wl_listener unmap;
    struct wl_listener commit;
    struct wl_listener destroy;
    struct wl_listener request_move;
    struct wl_listener request_resize;
    struct wl_listener request_maximize;
    struct wl_listener request_fullscreen;
};

struct osa_keyboard {
    struct wl_list link;
    struct osa_server *server;
    struct wlr_keyboard *wlr_keyboard;
    struct wl_listener modifiers;
    struct wl_listener key;
    struct wl_listener destroy;
};

/* server.c */
int osa_server_init(struct osa_server *server);
void osa_server_run(struct osa_server *server);
void osa_server_destroy(struct osa_server *server);

/* output.c */
void osa_output_init(struct osa_server *server);

/* input.c */
void osa_input_init(struct osa_server *server);

/* view.c */
void osa_view_init(struct osa_server *server);
void osa_focus_toplevel(struct osa_toplevel *toplevel);

/* ai_panel.c */
void osa_ai_panel_init(struct osa_server *server);
void osa_ai_panel_toggle(struct osa_server *server);

#endif /* OSA_SERVER_H */
