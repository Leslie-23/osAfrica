/*
 * View (window/toplevel) management for osa-compositor.
 */

#include <stdlib.h>
#include <wlr/types/wlr_scene.h>
#include <wlr/types/wlr_xdg_shell.h>
#include "server.h"

static void toplevel_map(struct wl_listener *listener, void *data) {
    struct osa_toplevel *toplevel = wl_container_of(listener, toplevel, map);
    wl_list_insert(&toplevel->server->toplevels, &toplevel->link);
    osa_focus_toplevel(toplevel);
}

static void toplevel_unmap(struct wl_listener *listener, void *data) {
    struct osa_toplevel *toplevel = wl_container_of(listener, toplevel, unmap);
    if (toplevel == wl_container_of(
            toplevel->server->toplevels.next, toplevel, link)) {
        /* If the focused toplevel is being unmapped, focus the next one */
        if (!wl_list_empty(&toplevel->server->toplevels)) {
            struct osa_toplevel *next =
                wl_container_of(toplevel->link.next, next, link);
            if (&next->link != &toplevel->server->toplevels) {
                osa_focus_toplevel(next);
            }
        }
    }
    wl_list_remove(&toplevel->link);
}

static void toplevel_commit(struct wl_listener *listener, void *data) {
    struct osa_toplevel *toplevel = wl_container_of(listener, toplevel, commit);
    if (toplevel->xdg_toplevel->base->initial_commit) {
        wlr_xdg_toplevel_set_size(toplevel->xdg_toplevel, 0, 0);
    }
}

static void toplevel_destroy(struct wl_listener *listener, void *data) {
    struct osa_toplevel *toplevel = wl_container_of(listener, toplevel, destroy);
    wl_list_remove(&toplevel->map.link);
    wl_list_remove(&toplevel->unmap.link);
    wl_list_remove(&toplevel->commit.link);
    wl_list_remove(&toplevel->destroy.link);
    wl_list_remove(&toplevel->request_move.link);
    wl_list_remove(&toplevel->request_resize.link);
    wl_list_remove(&toplevel->request_maximize.link);
    wl_list_remove(&toplevel->request_fullscreen.link);
    free(toplevel);
}

static void toplevel_request_move(struct wl_listener *listener, void *data) {
    /* TODO: Implement interactive move */
}

static void toplevel_request_resize(struct wl_listener *listener, void *data) {
    /* TODO: Implement interactive resize */
}

static void toplevel_request_maximize(struct wl_listener *listener, void *data) {
    struct osa_toplevel *toplevel =
        wl_container_of(listener, toplevel, request_maximize);
    if (toplevel->xdg_toplevel->base->surface->mapped) {
        wlr_xdg_toplevel_set_maximized(toplevel->xdg_toplevel,
            !toplevel->xdg_toplevel->current.maximized);
    }
}

static void toplevel_request_fullscreen(struct wl_listener *listener, void *data) {
    struct osa_toplevel *toplevel =
        wl_container_of(listener, toplevel, request_fullscreen);
    if (toplevel->xdg_toplevel->base->surface->mapped) {
        wlr_xdg_toplevel_set_fullscreen(toplevel->xdg_toplevel,
            !toplevel->xdg_toplevel->current.fullscreen);
    }
}

static void new_xdg_toplevel(struct wl_listener *listener, void *data) {
    struct osa_server *server =
        wl_container_of(listener, server, new_xdg_toplevel);
    struct wlr_xdg_toplevel *xdg_toplevel = data;

    struct osa_toplevel *toplevel = calloc(1, sizeof(*toplevel));
    toplevel->server = server;
    toplevel->xdg_toplevel = xdg_toplevel;
    toplevel->scene_tree = wlr_scene_xdg_surface_create(
        &server->scene->tree, xdg_toplevel->base);
    toplevel->scene_tree->node.data = toplevel;
    xdg_toplevel->base->data = toplevel->scene_tree;

    toplevel->map.notify = toplevel_map;
    wl_signal_add(&xdg_toplevel->base->surface->events.map, &toplevel->map);

    toplevel->unmap.notify = toplevel_unmap;
    wl_signal_add(&xdg_toplevel->base->surface->events.unmap, &toplevel->unmap);

    toplevel->commit.notify = toplevel_commit;
    wl_signal_add(&xdg_toplevel->base->surface->events.commit, &toplevel->commit);

    toplevel->destroy.notify = toplevel_destroy;
    wl_signal_add(&xdg_toplevel->events.destroy, &toplevel->destroy);

    toplevel->request_move.notify = toplevel_request_move;
    wl_signal_add(&xdg_toplevel->events.request_move, &toplevel->request_move);

    toplevel->request_resize.notify = toplevel_request_resize;
    wl_signal_add(&xdg_toplevel->events.request_resize, &toplevel->request_resize);

    toplevel->request_maximize.notify = toplevel_request_maximize;
    wl_signal_add(&xdg_toplevel->events.request_maximize, &toplevel->request_maximize);

    toplevel->request_fullscreen.notify = toplevel_request_fullscreen;
    wl_signal_add(&xdg_toplevel->events.request_fullscreen, &toplevel->request_fullscreen);
}

void osa_focus_toplevel(struct osa_toplevel *toplevel) {
    if (!toplevel) return;
    struct osa_server *server = toplevel->server;
    struct wlr_seat *seat = server->seat;
    struct wlr_surface *prev_surface = seat->keyboard_state.focused_surface;
    struct wlr_surface *surface = toplevel->xdg_toplevel->base->surface;

    if (prev_surface == surface) return;

    if (prev_surface) {
        struct wlr_xdg_toplevel *prev_toplevel =
            wlr_xdg_toplevel_try_from_wlr_surface(prev_surface);
        if (prev_toplevel) {
            wlr_xdg_toplevel_set_activated(prev_toplevel, false);
        }
    }

    wlr_scene_node_raise_to_top(&toplevel->scene_tree->node);
    wl_list_remove(&toplevel->link);
    wl_list_insert(&server->toplevels, &toplevel->link);
    wlr_xdg_toplevel_set_activated(toplevel->xdg_toplevel, true);

    struct wlr_keyboard *keyboard = wlr_seat_get_keyboard(seat);
    if (keyboard) {
        wlr_seat_keyboard_notify_enter(seat, surface,
            keyboard->keycodes, keyboard->num_keycodes,
            &keyboard->modifiers);
    }
}

void osa_view_init(struct osa_server *server) {
    server->xdg_shell = wlr_xdg_shell_create(server->wl_display, 3);

    server->new_xdg_toplevel.notify = new_xdg_toplevel;
    wl_signal_add(&server->xdg_shell->events.new_toplevel,
        &server->new_xdg_toplevel);
}
