/*
 * Panel window — a horizontal bar anchored to the top of the screen.
 * Shows: AI status indicator, app launcher button, clock, system tray.
 */

#include <gtk/gtk.h>
#include <gtk4-layer-shell.h>
#include <ctime>
#include <cstring>
#include "panel_window.h"

static GtkWidget *clock_label = nullptr;

static gboolean update_clock(gpointer data) {
    if (!clock_label) return G_SOURCE_REMOVE;

    time_t now = time(nullptr);
    struct tm *local = localtime(&now);
    char buf[64];
    strftime(buf, sizeof(buf), "%a %b %d  %H:%M", local);
    gtk_label_set_text(GTK_LABEL(clock_label), buf);
    return G_SOURCE_CONTINUE;
}

static void on_ai_button_clicked(GtkButton *button, gpointer user_data) {
    /* TODO: Send toggle signal to compositor AI panel via IPC */
    g_print("AI panel toggle requested\n");
}

static void on_launcher_clicked(GtkButton *button, gpointer user_data) {
    /* Launch foot terminal as a quick action */
    GError *error = nullptr;
    g_spawn_command_line_async("foot", &error);
    if (error) {
        g_warning("Failed to launch terminal: %s", error->message);
        g_error_free(error);
    }
}

GtkWidget *osa_panel_window_new(GtkApplication *app) {
    GtkWidget *window = gtk_application_window_new(app);
    gtk_window_set_title(GTK_WINDOW(window), "osAfrica Panel");
    gtk_window_set_default_size(GTK_WINDOW(window), 0, 32);

    /* Layer shell setup — anchor to top, span full width */
    gtk_layer_init_for_window(GTK_WINDOW(window));
    gtk_layer_set_layer(GTK_WINDOW(window), GTK_LAYER_SHELL_LAYER_TOP);
    gtk_layer_set_anchor(GTK_WINDOW(window), GTK_LAYER_SHELL_EDGE_TOP, TRUE);
    gtk_layer_set_anchor(GTK_WINDOW(window), GTK_LAYER_SHELL_EDGE_LEFT, TRUE);
    gtk_layer_set_anchor(GTK_WINDOW(window), GTK_LAYER_SHELL_EDGE_RIGHT, TRUE);
    gtk_layer_set_margin(GTK_WINDOW(window), GTK_LAYER_SHELL_EDGE_TOP, 0);
    gtk_layer_auto_exclusive_zone_enable(GTK_WINDOW(window));

    /* Main horizontal box */
    GtkWidget *hbox = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_set_margin_start(hbox, 8);
    gtk_widget_set_margin_end(hbox, 8);
    gtk_window_set_child(GTK_WINDOW(window), hbox);

    /* Left: AI button + app launcher */
    GtkWidget *ai_btn = gtk_button_new_with_label("⬡ AI");
    gtk_widget_add_css_class(ai_btn, "ai-button");
    g_signal_connect(ai_btn, "clicked", G_CALLBACK(on_ai_button_clicked), nullptr);
    gtk_box_append(GTK_BOX(hbox), ai_btn);

    GtkWidget *launcher_btn = gtk_button_new_with_label("Terminal");
    g_signal_connect(launcher_btn, "clicked", G_CALLBACK(on_launcher_clicked), nullptr);
    gtk_box_append(GTK_BOX(hbox), launcher_btn);

    /* Center spacer */
    GtkWidget *spacer = gtk_label_new("");
    gtk_widget_set_hexpand(spacer, TRUE);
    gtk_box_append(GTK_BOX(hbox), spacer);

    /* Right: AI model indicator + clock */
    GtkWidget *model_label = gtk_label_new("llama3");
    gtk_widget_add_css_class(model_label, "model-indicator");
    gtk_box_append(GTK_BOX(hbox), model_label);

    clock_label = gtk_label_new("");
    gtk_widget_add_css_class(clock_label, "clock");
    gtk_box_append(GTK_BOX(hbox), clock_label);

    update_clock(nullptr);
    g_timeout_add_seconds(30, update_clock, nullptr);

    /* CSS styling */
    GtkCssProvider *css = gtk_css_provider_new();
    gtk_css_provider_load_from_string(css,
        "window { background: rgba(13, 17, 23, 0.92); }"
        "label { color: #c9d1d9; font-family: 'Noto Sans Mono'; font-size: 13px; }"
        ".ai-button { background: #238636; color: white; border-radius: 4px; "
        "  padding: 2px 12px; font-weight: bold; }"
        ".ai-button:hover { background: #2ea043; }"
        ".model-indicator { color: #58a6ff; margin-right: 16px; }"
        ".clock { color: #8b949e; }"
        "button { background: transparent; color: #c9d1d9; border: none; "
        "  padding: 2px 8px; }"
        "button:hover { background: rgba(255,255,255,0.1); border-radius: 4px; }"
    );
    gtk_style_context_add_provider_for_display(
        gdk_display_get_default(),
        GTK_STYLE_PROVIDER(css),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(css);

    return window;
}
