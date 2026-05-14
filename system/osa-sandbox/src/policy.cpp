#include <string>
#include <regex>
#include <vector>

static const std::vector<std::regex> BLOCKED_PATTERNS = {
    std::regex(R"(rm\s+-rf\s+/\s*$)"),
    std::regex(R"(dd\s+.*of=/dev/sd[a-z])"),
    std::regex(R"(dd\s+.*of=/dev/nvme)"),
    std::regex(R"(mkfs\.\w+\s+/dev/sd[a-z])"),
    std::regex(R"(>\s*/dev/sd[a-z])"),
    std::regex(R"(:\(\)\s*\{)"),
    std::regex(R"(chmod\s+-R\s+777\s+/\s*$)"),
};

bool check_policy(const std::string &command) {
    for (const auto &pattern : BLOCKED_PATTERNS) {
        if (std::regex_search(command, pattern)) {
            return false;
        }
    }
    return true;
}
