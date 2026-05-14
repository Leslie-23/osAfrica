#include <string>
#include <vector>
#include <cstdlib>
#include <sys/stat.h>

struct SandboxConfig {
    bool allow_network = false;
    std::vector<std::string> writable_paths;
    std::vector<std::string> command;
};

static bool path_exists(const std::string &path) {
    struct stat st;
    return stat(path.c_str(), &st) == 0;
}

std::vector<std::string> build_bwrap_args(const SandboxConfig &config) {
    std::vector<std::string> args;
    args.push_back("bwrap");

    args.push_back("--ro-bind"); args.push_back("/"); args.push_back("/");
    args.push_back("--dev"); args.push_back("/dev");
    args.push_back("--proc"); args.push_back("/proc");
    args.push_back("--tmpfs"); args.push_back("/tmp");

    for (const auto &path : config.writable_paths) {
        if (path_exists(path)) {
            args.push_back("--bind");
            args.push_back(path);
            args.push_back(path);
        }
    }

    if (!config.allow_network) {
        args.push_back("--unshare-net");
    }

    args.push_back("--unshare-pid");
    args.push_back("--die-with-parent");

    const char *cwd = getenv("PWD");
    if (cwd) {
        args.push_back("--chdir");
        args.push_back(cwd);
    }

    args.push_back("--");

    for (const auto &part : config.command) {
        args.push_back(part);
    }

    return args;
}
