/*
 * osa-panel — Top panel / taskbar for osAfrica desktop.
 * Uses GTK4 + gtk4-layer-shell for Wayland layer surface positioning.
 */

#include <gtk/gtk.h>
#include <gtk4-layer-shell.h>
#include "panel_window.h"

static void activate(GtkApplication *app, gpointer user_data) {
    GtkWidget *window = osa_panel_window_new(app);
    gtk_window_present(GTK_WINDOW(window));
}

int main(int argc, char *argv[]) {
    GtkApplication *app = gtk_application_new(
        "org.osafrica.panel", G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect(app, "activate", G_CALLBACK(activate), NULL);

    int status = g_application_run(G_APPLICATION(app), argc, argv);
    g_object_unref(app);
    return status;
}
