/*
 * osa-hwdetect — Hardware detection daemon for osAfrica.
 * Detects RAM, CPU, GPU and selects the appropriate model quantization profile.
 * Writes result to /etc/osa/hardware-profile.json at boot.
 */

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

// Forward declarations (implemented in separate TUs)
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

RamInfo detect_ram();
int detect_cpu_cores();
std::string detect_cpu_model();
GpuInfo detect_nvidia_gpu();
long detect_disk_free(const std::string& path = "/");
std::string select_tier(const HardwareProfile& profile);

static void write_json(const HardwareProfile& p, const std::string& path) {
    std::filesystem::create_directories(std::filesystem::path(path).parent_path());
    std::ofstream out(path);
    if (!out.is_open()) {
        std::cerr << "Error: cannot write to " << path << std::endl;
        return;
    }

    out << "{\n"
        << "  \"ram_total_mb\": " << p.ram.total_mb << ",\n"
        << "  \"ram_available_mb\": " << p.ram.available_mb << ",\n"
        << "  \"cpu_cores\": " << p.cpu_cores << ",\n"
        << "  \"cpu_model\": \"" << p.cpu_model << "\",\n"
        << "  \"gpu_vendor\": \"" << p.gpu.vendor << "\",\n"
        << "  \"gpu_name\": \"" << p.gpu.name << "\",\n"
        << "  \"gpu_vram_mb\": " << p.gpu.vram_mb << ",\n"
        << "  \"gpu_driver\": \"" << p.gpu.driver << "\",\n"
        << "  \"disk_free_gb\": " << p.disk_free_gb << ",\n"
        << "  \"tier\": \"" << p.tier << "\"\n"
        << "}\n";

    std::cout << "Hardware profile written to " << path << " (tier: " << p.tier << ")" << std::endl;
}

int main(int argc, char* argv[]) {
    std::string output_path = "/etc/osa/hardware-profile.json";
    if (argc > 1) {
        output_path = argv[1];
    }

    HardwareProfile profile;
    profile.ram = detect_ram();
    profile.cpu_cores = detect_cpu_cores();
    profile.cpu_model = detect_cpu_model();
    profile.gpu = detect_nvidia_gpu();
    profile.disk_free_gb = detect_disk_free();
    profile.tier = select_tier(profile);

    std::cout << "=== osAfrica Hardware Detection ===" << std::endl;
    std::cout << "RAM: " << profile.ram.total_mb << " MB total, "
              << profile.ram.available_mb << " MB available" << std::endl;
    std::cout << "CPU: " << profile.cpu_cores << " cores (" << profile.cpu_model << ")" << std::endl;
    if (!profile.gpu.vendor.empty()) {
        std::cout << "GPU: " << profile.gpu.name << " (" << profile.gpu.vram_mb << " MB VRAM)" << std::endl;
    } else {
        std::cout << "GPU: None detected" << std::endl;
    }
    std::cout << "Disk: " << profile.disk_free_gb << " GB free" << std::endl;
    std::cout << "Selected tier: " << profile.tier << std::endl;

    write_json(profile, output_path);
    return 0;
}
