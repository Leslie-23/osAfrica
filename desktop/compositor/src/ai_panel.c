/*
 * AI command palette overlay for osa-compositor.
 *
 * Toggle with Super+Space. Renders as a centered overlay on top of
 * all windows. Communicates with osa-routerd via Unix socket.
 *
 * Phase 2 implementation: This is a placeholder that will be replaced
 * with a proper GTK4 layer-shell surface in the full implementation.
 * For now, it sets a flag that the panel process can query.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "server.h"

void osa_ai_panel_init(struct osa_server *server) {
    server->ai_panel_visible = 0;
    server->ai_panel_tree = wlr_scene_tree_create(&server->scene->tree);
    wlr_scene_node_set_enabled(&server->ai_panel_tree->node, false);
}

void osa_ai_panel_toggle(struct osa_server *server) {
    server->ai_panel_visible = !server->ai_panel_visible;
    wlr_scene_node_set_enabled(&server->ai_panel_tree->node,
        server->ai_panel_visible);

    if (server->ai_panel_visible) {
        printf("[AI Panel] Opened — waiting for input\n");
        wlr_scene_node_raise_to_top(&server->ai_panel_tree->node);
    } else {
        printf("[AI Panel] Closed\n");
    }
}
