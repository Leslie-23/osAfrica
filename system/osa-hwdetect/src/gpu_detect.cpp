#include <array>
#include <cstdio>
#include <memory>
#include <sstream>
#include <string>

struct GpuInfo {
    std::string vendor;
    std::string name;
    int vram_mb = 0;
    std::string driver;
};

static std::string exec_command(const std::string& cmd) {
    std::array<char, 256> buffer;
    std::string result;
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd.c_str(), "r"), pclose);
    if (!pipe) return "";
    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    return result;
}

GpuInfo detect_nvidia_gpu() {
    GpuInfo info;

    std::string output = exec_command(
        "nvidia-smi --query-gpu=name,memory.total,driver_version "
        "--format=csv,noheader,nounits 2>/dev/null"
    );

    if (output.empty()) return info;

    std::istringstream iss(output);
    std::string line;
    if (std::getline(iss, line)) {
        info.vendor = "nvidia";
        // Parse CSV: name, memory, driver
        std::istringstream csv(line);
        std::string token;

        if (std::getline(csv, token, ',')) {
            auto start = token.find_first_not_of(" ");
            info.name = start != std::string::npos ? token.substr(start) : token;
        }
        if (std::getline(csv, token, ',')) {
            try {
                info.vram_mb = std::stoi(token);
            } catch (...) {}
        }
        if (std::getline(csv, token, ',')) {
            auto start = token.find_first_not_of(" ");
            info.driver = start != std::string::npos ? token.substr(start) : token;
        }
    }

    return info;
}
