/*
 * osa-terminal — AI-integrated terminal emulator for osAfrica.
 * GTK4 + VTE terminal with an AI assistant sidebar.
 */

#include <gtk/gtk.h>

/* Forward declarations */
GtkWidget *osa_terminal_new(GtkApplication *app);

static void activate(GtkApplication *app, gpointer user_data) {
    GtkWidget *window = osa_terminal_new(app);
    gtk_window_present(GTK_WINDOW(window));
}

int main(int argc, char *argv[]) {
    GtkApplication *app = gtk_application_new(
        "org.osafrica.terminal", G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect(app, "activate", G_CALLBACK(activate), NULL);

    int status = g_application_run(G_APPLICATION(app), argc, argv);
    g_object_unref(app);
    return status;
}
