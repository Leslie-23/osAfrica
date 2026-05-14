/*
 * osa-compositor — Entry point for the osAfrica Wayland compositor.
 *
 * A wlroots-based stacking compositor with an integrated AI command palette.
 * Users press Super+Space to summon the AI panel overlay.
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <wlr/util/log.h>
#include "server.h"

int main(int argc, char *argv[]) {
    wlr_log_init(WLR_DEBUG, NULL);

    struct osa_server server = {0};

    if (osa_server_init(&server) != 0) {
        fprintf(stderr, "Failed to initialize osa-compositor\n");
        return 1;
    }

    const char *socket = wl_display_add_socket_auto(server.wl_display);
    if (!socket) {
        fprintf(stderr, "Failed to create Wayland socket\n");
        osa_server_destroy(&server);
        return 1;
    }

    if (!wlr_backend_start(server.backend)) {
        fprintf(stderr, "Failed to start wlr backend\n");
        osa_server_destroy(&server);
        return 1;
    }

    setenv("WAYLAND_DISPLAY", socket, true);
    setenv("XDG_CURRENT_DESKTOP", "osAfrica", true);

    printf("osAfrica compositor running on WAYLAND_DISPLAY=%s\n", socket);
    printf("Press Super+Space for AI panel, Super+Return for terminal\n");

    /* Launch panel and terminal */
    if (fork() == 0) {
        execl("/usr/bin/osa-panel", "osa-panel", NULL);
        _exit(1);
    }

    osa_server_run(&server);
    osa_server_destroy(&server);

    return 0;
}
