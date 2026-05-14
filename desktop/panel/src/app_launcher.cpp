/*
 * AI-powered application launcher.
 *
 * Phase 2: Reads .desktop files from /usr/share/applications,
 * provides fuzzy search, and routes natural language queries
 * ("open a text editor") through the AI router.
 */

#include <gtk/gtk.h>
#include <cstdlib>
#include <cstring>
#include <dirent.h>

struct AppEntry {
    char name[128];
    char exec[256];
    char icon[128];
    char comment[256];
};

static AppEntry apps[512];
static int app_count = 0;

static void scan_desktop_files() {
    const char *dirs[] = {
        "/usr/share/applications",
        "/usr/local/share/applications",
        nullptr,
    };

    app_count = 0;

    for (int d = 0; dirs[d] && app_count < 512; d++) {
        DIR *dir = opendir(dirs[d]);
        if (!dir) continue;

        struct dirent *entry;
        while ((entry = readdir(dir)) && app_count < 512) {
            if (!strstr(entry->d_name, ".desktop")) continue;

            char path[512];
            snprintf(path, sizeof(path), "%s/%s", dirs[d], entry->d_name);

            FILE *f = fopen(path, "r");
            if (!f) continue;

            AppEntry *app = &apps[app_count];
            memset(app, 0, sizeof(*app));

            char line[512];
            while (fgets(line, sizeof(line), f)) {
                if (strncmp(line, "Name=", 5) == 0 && app->name[0] == '\0') {
                    strncpy(app->name, line + 5, sizeof(app->name) - 1);
                    app->name[strcspn(app->name, "\n")] = '\0';
                } else if (strncmp(line, "Exec=", 5) == 0) {
                    strncpy(app->exec, line + 5, sizeof(app->exec) - 1);
                    app->exec[strcspn(app->exec, "\n")] = '\0';
                    /* Strip field codes like %f %u %F %U */
                    char *pct = strstr(app->exec, " %");
                    if (pct) *pct = '\0';
                } else if (strncmp(line, "Icon=", 5) == 0) {
                    strncpy(app->icon, line + 5, sizeof(app->icon) - 1);
                    app->icon[strcspn(app->icon, "\n")] = '\0';
                } else if (strncmp(line, "Comment=", 8) == 0) {
                    strncpy(app->comment, line + 8, sizeof(app->comment) - 1);
                    app->comment[strcspn(app->comment, "\n")] = '\0';
                }
            }
            fclose(f);

            if (app->name[0] && app->exec[0]) {
                app_count++;
            }
        }
        closedir(dir);
    }
}

void osa_app_launcher_init() {
    scan_desktop_files();
}

int osa_app_launcher_search(const char *query, AppEntry **results, int max_results) {
    int count = 0;
    for (int i = 0; i < app_count && count < max_results; i++) {
        if (strcasestr(apps[i].name, query) ||
            strcasestr(apps[i].comment, query)) {
            results[count++] = &apps[i];
        }
    }
    return count;
}

void osa_app_launcher_launch(const AppEntry *app) {
    if (!app || !app->exec[0]) return;

    char cmd[512];
    snprintf(cmd, sizeof(cmd), "%s &", app->exec);
    system(cmd);
}
