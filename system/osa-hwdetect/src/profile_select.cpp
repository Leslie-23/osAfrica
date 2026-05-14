#include <string>
#include <sys/statvfs.h>

struct RamInfo {
    long total_mb = 0;
    long available_mb = 0;
};

struct GpuInfo {
    std::string vendor;
    std::string name;
    int vram_mb = 0;
    std::string driver;
};

struct HardwareProfile {
    RamInfo ram;
    int cpu_cores = 0;
    std::string cpu_model;
    GpuInfo gpu;
    long disk_free_gb = 0;
    std::string tier;
};

std::string select_tier(const HardwareProfile& profile) {
    if (profile.gpu.vendor == "nvidia" && profile.gpu.vram_mb >= 8000) {
        return "gpu-nvidia";
    }
    if (profile.ram.total_mb >= 28000) {
        return "32gb";
    }
    if (profile.ram.total_mb >= 14000) {
        return "16gb";
    }
    return "8gb";
}

long detect_disk_free(const std::string& path) {
    struct statvfs stat;
    if (statvfs(path.c_str(), &stat) != 0) {
        return 0;
    }
    return static_cast<long>(stat.f_bavail) * stat.f_frsize / (1024L * 1024L * 1024L);
}
