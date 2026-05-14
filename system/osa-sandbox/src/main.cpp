/*
 * osa-sandbox — Wraps bubblewrap to provide AI-command sandboxing.
 *
 * Usage: osa-sandbox [--allow-net] [--writable PATH] -- COMMAND [ARGS...]
 *
 * Default policy: read-only root, writable $HOME and /tmp, no network.
 */

#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
#include <unistd.h>
#include <sys/wait.h>

struct SandboxConfig {
    bool allow_network = false;
    std::vector<std::string> writable_paths;
    std::vector<std::string> command;
};

/* Forward declarations */
std::vector<std::string> build_bwrap_args(const SandboxConfig &config);
bool check_policy(const std::string &command);

static SandboxConfig parse_args(int argc, char *argv[]) {
    SandboxConfig config;

    const char *home = getenv("HOME");
    if (home) config.writable_paths.push_back(home);
    config.writable_paths.push_back("/tmp");

    int i = 1;
    for (; i < argc; i++) {
        if (strcmp(argv[i], "--") == 0) {
            i++;
            break;
        }
        if (strcmp(argv[i], "--allow-net") == 0) {
            config.allow_network = true;
        } else if (strcmp(argv[i], "--writable") == 0 && i + 1 < argc) {
            config.writable_paths.push_back(argv[++i]);
        }
    }

    for (; i < argc; i++) {
        config.command.push_back(argv[i]);
    }

    return config;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: osa-sandbox [--allow-net] [--writable PATH] -- COMMAND [ARGS...]\n";
        return 1;
    }

    SandboxConfig config = parse_args(argc, argv);

    if (config.command.empty()) {
        std::cerr << "Error: no command specified after --\n";
        return 1;
    }

    std::string cmd_str;
    for (const auto &arg : config.command) {
        if (!cmd_str.empty()) cmd_str += " ";
        cmd_str += arg;
    }

    if (!check_policy(cmd_str)) {
        std::cerr << "BLOCKED: command violates security policy\n";
        return 1;
    }

    auto bwrap_args = build_bwrap_args(config);

    std::vector<char *> exec_args;
    for (auto &arg : bwrap_args) {
        exec_args.push_back(arg.data());
    }
    exec_args.push_back(nullptr);

    execvp(exec_args[0], exec_args.data());
    perror("execvp failed");
    return 127;
}
