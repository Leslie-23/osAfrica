/*
 * Terminal widget — VTE-based terminal with osa-shell as default shell.
 */

#include <gtk/gtk.h>
#include <vte/vte.h>
#include <cstdlib>

/* Forward declaration from ai_sidebar.cpp */
GtkWidget *osa_ai_sidebar_new();

static void on_child_exited(VteTerminal *terminal, gint status, gpointer user_data) {
    GtkWindow *window = GTK_WINDOW(user_data);
    gtk_window_close(window);
}

GtkWidget *osa_terminal_new(GtkApplication *app) {
    GtkWidget *window = gtk_application_window_new(app);
    gtk_window_set_title(GTK_WINDOW(window), "osAfrica Terminal");
    gtk_window_set_default_size(GTK_WINDOW(window), 900, 600);

    /* Horizontal paned: terminal | AI sidebar */
    GtkWidget *paned = gtk_paned_new(GTK_ORIENTATION_HORIZONTAL);
    gtk_window_set_child(GTK_WINDOW(window), paned);

    /* Terminal widget */
    GtkWidget *vte = vte_terminal_new();
    vte_terminal_set_font_scale(VTE_TERMINAL(vte), 1.0);
    vte_terminal_set_scrollback_lines(VTE_TERMINAL(vte), 10000);
    vte_terminal_set_cursor_blink_mode(VTE_TERMINAL(vte), VTE_CURSOR_BLINK_OFF);

    /* Color scheme — dark theme matching osAfrica branding */
    GdkRGBA fg = {0.79, 0.82, 0.85, 1.0};  /* #c9d1d9 */
    GdkRGBA bg = {0.05, 0.07, 0.09, 0.95}; /* #0d1117 */
    GdkRGBA palette[16] = {
        {0.19, 0.20, 0.25, 1.0}, /* black */
        {0.96, 0.30, 0.30, 1.0}, /* red */
        {0.24, 0.65, 0.36, 1.0}, /* green - #3da44e */
        {0.85, 0.65, 0.22, 1.0}, /* yellow */
        {0.35, 0.53, 0.80, 1.0}, /* blue - #5987cc */
        {0.65, 0.40, 0.80, 1.0}, /* magenta */
        {0.25, 0.70, 0.70, 1.0}, /* cyan */
        {0.79, 0.82, 0.85, 1.0}, /* white */
        {0.30, 0.32, 0.38, 1.0}, /* bright black */
        {1.00, 0.45, 0.45, 1.0}, /* bright red */
        {0.35, 0.80, 0.50, 1.0}, /* bright green */
        {1.00, 0.80, 0.35, 1.0}, /* bright yellow */
        {0.45, 0.65, 0.95, 1.0}, /* bright blue */
        {0.80, 0.55, 0.95, 1.0}, /* bright magenta */
        {0.40, 0.85, 0.85, 1.0}, /* bright cyan */
        {0.92, 0.93, 0.95, 1.0}, /* bright white */
    };
    vte_terminal_set_colors(VTE_TERMINAL(vte), &fg, &bg, palette, 16);

    /* Spawn osa-shell (fallback to bash) */
    const char *shell = "/usr/bin/osa-shell";
    if (access(shell, X_OK) != 0) {
        shell = g_getenv("SHELL");
        if (!shell) shell = "/bin/bash";
    }

    char *argv[] = {(char *)shell, nullptr};
    vte_terminal_spawn_async(VTE_TERMINAL(vte),
        VTE_PTY_DEFAULT,
        nullptr,     /* working directory */
        argv,
        nullptr,     /* envv */
        G_SPAWN_DEFAULT,
        nullptr, nullptr, nullptr,
        -1,          /* timeout */
        nullptr,     /* cancellable */
        nullptr,     /* callback */
        nullptr);    /* user data */

    g_signal_connect(vte, "child-exited", G_CALLBACK(on_child_exited), window);

    gtk_widget_set_hexpand(vte, TRUE);
    gtk_widget_set_vexpand(vte, TRUE);
    gtk_paned_set_start_child(GTK_PANED(paned), vte);

    /* AI sidebar (collapsible) */
    GtkWidget *sidebar = osa_ai_sidebar_new();
    gtk_paned_set_end_child(GTK_PANED(paned), sidebar);
    gtk_paned_set_position(GTK_PANED(paned), 620);

    return window;
}
