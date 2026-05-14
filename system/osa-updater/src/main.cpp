/*
 * osa-updater — System update manager for osAfrica.
 *
 * Handles:
 * - System package updates (apt)
 * - AI model updates (new GGUF versions)
 * - osAfrica component updates
 *
 * Usage: osa-updater [--check | --update | --update-models]
 */

#include <cstring>
#include <iostream>

/* Forward declarations */
int check_updates();
int apply_updates();
int update_models();

int main(int argc, char *argv[]) {
    if (argc < 2) {
        std::cout << "osAfrica System Updater v0.1.0\n\n"
                  << "Usage:\n"
                  << "  osa-updater --check          Check for available updates\n"
                  << "  osa-updater --update         Apply system updates\n"
                  << "  osa-updater --update-models  Update AI models\n";
        return 0;
    }

    if (strcmp(argv[1], "--check") == 0) {
        return check_updates();
    } else if (strcmp(argv[1], "--update") == 0) {
        return apply_updates();
    } else if (strcmp(argv[1], "--update-models") == 0) {
        return update_models();
    }

    std::cerr << "Unknown option: " << argv[1] << "\n";
    return 1;
}
