/*
 * AI model status indicator — shows which model is active
 * and inference status (idle/thinking/streaming).
 *
 * Connects to osa-routerd via Unix socket to poll status.
 */

#include <gtk/gtk.h>
#include <cstdio>
#include <cstring>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

static const char *ROUTER_SOCKET = "/run/osa/router.sock";

struct AiIndicator {
    GtkWidget *label;
    GtkWidget *status_dot;
    char current_model[64];
    bool connected;
};

static AiIndicator indicator = {};

static gboolean poll_router_status(gpointer data) {
    int fd = socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK, 0);
    if (fd < 0) {
        indicator.connected = false;
        gtk_label_set_text(GTK_LABEL(indicator.label), "AI: offline");
        return G_SOURCE_CONTINUE;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, ROUTER_SOCKET, sizeof(addr.sun_path) - 1);

    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) == 0) {
        indicator.connected = true;
        gtk_label_set_text(GTK_LABEL(indicator.label), "AI: ready");
    } else {
        indicator.connected = false;
        gtk_label_set_text(GTK_LABEL(indicator.label), "AI: offline");
    }

    close(fd);
    return G_SOURCE_CONTINUE;
}

GtkWidget *osa_ai_indicator_new() {
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4);

    indicator.label = gtk_label_new("AI: starting...");
    gtk_widget_add_css_class(indicator.label, "ai-status");
    gtk_box_append(GTK_BOX(box), indicator.label);

    strncpy(indicator.current_model, "llama3-8b", sizeof(indicator.current_model));
    indicator.connected = false;

    g_timeout_add_seconds(5, poll_router_status, nullptr);

    return box;
}
