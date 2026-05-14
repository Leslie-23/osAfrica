#include <fstream>
#include <sstream>
#include <string>

struct RamInfo {
    long total_mb = 0;
    long available_mb = 0;
};

RamInfo detect_ram() {
    RamInfo info;
    std::ifstream meminfo("/proc/meminfo");
    if (!meminfo.is_open()) return info;

    std::string line;
    while (std::getline(meminfo, line)) {
        std::istringstream iss(line);
        std::string key;
        long value;
        iss >> key >> value;

        if (key == "MemTotal:") {
            info.total_mb = value / 1024;
        } else if (key == "MemAvailable:") {
            info.available_mb = value / 1024;
        }
    }
    return info;
}

int detect_cpu_cores() {
    int cores = 0;
    std::ifstream cpuinfo("/proc/cpuinfo");
    if (!cpuinfo.is_open()) return 1;

    std::string line;
    while (std::getline(cpuinfo, line)) {
        if (line.find("processor") == 0) {
            cores++;
        }
    }
    return cores > 0 ? cores : 1;
}

std::string detect_cpu_model() {
    std::ifstream cpuinfo("/proc/cpuinfo");
    if (!cpuinfo.is_open()) return "unknown";

    std::string line;
    while (std::getline(cpuinfo, line)) {
        if (line.find("model name") == 0) {
            auto pos = line.find(':');
            if (pos != std::string::npos) {
                std::string model = line.substr(pos + 1);
                // trim leading spaces
                auto start = model.find_first_not_of(" \t");
                return start != std::string::npos ? model.substr(start) : model;
            }
        }
    }
    return "unknown";
}
