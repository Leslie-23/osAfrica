/*
 * AI assistant sidebar for the terminal.
 * Shows AI suggestions, command explanations, and quick actions.
 * Communicates with osa-routerd to provide contextual help.
 */

#include <gtk/gtk.h>

static GtkWidget *chat_view = nullptr;
static GtkWidget *input_entry = nullptr;

static void on_send_clicked(GtkButton *button, gpointer user_data) {
    if (!input_entry) return;

    const char *text = gtk_editable_get_text(GTK_EDITABLE(input_entry));
    if (!text || text[0] == '\0') return;

    /* Append user message to chat view */
    GtkTextBuffer *buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(chat_view));
    GtkTextIter end;
    gtk_text_buffer_get_end_iter(buffer, &end);

    char msg[1024];
    snprintf(msg, sizeof(msg), "\nYou: %s\n", text);
    gtk_text_buffer_insert(buffer, &end, msg, -1);

    /* TODO: Send to osa-routerd via Unix socket, stream response back */
    gtk_text_buffer_get_end_iter(buffer, &end);
    gtk_text_buffer_insert(buffer, &end,
        "AI: (Connect to osa-routerd for responses)\n", -1);

    gtk_editable_set_text(GTK_EDITABLE(input_entry), "");
}

static void on_entry_activate(GtkEntry *entry, gpointer user_data) {
    on_send_clicked(nullptr, nullptr);
}

GtkWidget *osa_ai_sidebar_new() {
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_widget_set_size_request(box, 280, -1);

    /* Header */
    GtkWidget *header = gtk_label_new("AI Assistant");
    gtk_widget_add_css_class(header, "sidebar-header");
    gtk_box_append(GTK_BOX(box), header);

    GtkWidget *sep = gtk_separator_new(GTK_ORIENTATION_HORIZONTAL);
    gtk_box_append(GTK_BOX(box), sep);

    /* Chat view */
    GtkWidget *scroll = gtk_scrolled_window_new();
    gtk_widget_set_vexpand(scroll, TRUE);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll),
        GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);

    chat_view = gtk_text_view_new();
    gtk_text_view_set_wrap_mode(GTK_TEXT_VIEW(chat_view), GTK_WRAP_WORD_CHAR);
    gtk_text_view_set_editable(GTK_TEXT_VIEW(chat_view), FALSE);
    gtk_text_view_set_cursor_visible(GTK_TEXT_VIEW(chat_view), FALSE);
    gtk_widget_add_css_class(chat_view, "chat-view");

    GtkTextBuffer *buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(chat_view));
    gtk_text_buffer_set_text(buffer,
        "Welcome to osAfrica AI Assistant.\n"
        "Ask questions about commands, code, or your system.\n\n"
        "Examples:\n"
        "  - What does this error mean?\n"
        "  - How do I find large files?\n"
        "  - Write a script to backup my home dir\n", -1);

    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scroll), chat_view);
    gtk_box_append(GTK_BOX(box), scroll);

    /* Input area */
    GtkWidget *input_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4);
    gtk_widget_set_margin_start(input_box, 4);
    gtk_widget_set_margin_end(input_box, 4);
    gtk_widget_set_margin_bottom(input_box, 4);

    input_entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(input_entry), "Ask AI...");
    gtk_widget_set_hexpand(input_entry, TRUE);
    g_signal_connect(input_entry, "activate", G_CALLBACK(on_entry_activate), nullptr);
    gtk_box_append(GTK_BOX(input_box), input_entry);

    GtkWidget *send_btn = gtk_button_new_with_label("Send");
    g_signal_connect(send_btn, "clicked", G_CALLBACK(on_send_clicked), nullptr);
    gtk_box_append(GTK_BOX(input_box), send_btn);

    gtk_box_append(GTK_BOX(box), input_box);

    /* Styling */
    GtkCssProvider *css = gtk_css_provider_new();
    gtk_css_provider_load_from_string(css,
        ".sidebar-header { font-weight: bold; padding: 8px; color: #58a6ff; "
        "  font-size: 14px; }"
        ".chat-view { font-family: 'Noto Sans Mono'; font-size: 12px; "
        "  color: #c9d1d9; background: #161b22; padding: 8px; }"
    );
    gtk_style_context_add_provider_for_display(
        gdk_display_get_default(),
        GTK_STYLE_PROVIDER(css),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(css);

    return box;
}
