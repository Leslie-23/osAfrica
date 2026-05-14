/*
 * Core compositor server — backend, scene graph, and display initialization.
 */

#include <stdlib.h>
#include <wlr/backend.h>
#include <wlr/render/allocator.h>
#include <wlr/render/wlr_renderer.h>
#include <wlr/types/wlr_compositor.h>
#include <wlr/types/wlr_data_device.h>
#include <wlr/types/wlr_output_layout.h>
#include <wlr/types/wlr_scene.h>
#include <wlr/types/wlr_subcompositor.h>
#include <wlr/types/wlr_xdg_shell.h>
#include "server.h"

int osa_server_init(struct osa_server *server) {
    server->wl_display = wl_display_create();
    if (!server->wl_display) {
        return -1;
    }

    server->backend = wlr_backend_autocreate(
        wl_display_get_event_loop(server->wl_display), NULL);
    if (!server->backend) {
        return -1;
    }

    server->renderer = wlr_renderer_autocreate(server->backend);
    if (!server->renderer) {
        return -1;
    }
    wlr_renderer_init_wl_display(server->renderer, server->wl_display);

    server->allocator = wlr_allocator_autocreate(server->backend, server->renderer);
    if (!server->allocator) {
        return -1;
    }

    wlr_compositor_create(server->wl_display, 5, server->renderer);
    wlr_subcompositor_create(server->wl_display);
    wlr_data_device_manager_create(server->wl_display);

    server->scene = wlr_scene_create();
    server->output_layout = wlr_output_layout_create(server->wl_display);
    server->scene_layout = wlr_scene_attach_output_layout(
        server->scene, server->output_layout);

    wl_list_init(&server->toplevels);
    wl_list_init(&server->keyboards);
    wl_list_init(&server->outputs);

    osa_output_init(server);
    osa_input_init(server);
    osa_view_init(server);
    osa_ai_panel_init(server);

    return 0;
}

void osa_server_run(struct osa_server *server) {
    wl_display_run(server->wl_display);
}

void osa_server_destroy(struct osa_server *server) {
    wl_display_destroy_clients(server->wl_display);
    wlr_scene_node_destroy(&server->scene->tree.node);
    wlr_xcursor_manager_destroy(server->cursor_mgr);
    wlr_cursor_destroy(server->cursor);
    wlr_allocator_destroy(server->allocator);
    wlr_renderer_destroy(server->renderer);
    wlr_backend_destroy(server->backend);
    wl_display_destroy(server->wl_display);
}
