#include <iostream>
#include <fstream>
#include <filesystem>
#include <vector>
#include <chrono>
#include <iomanip>
#include <thread>
#include <string>

namespace fs = std::filesystem;

// Variável global para o buffer (será definida no main)
size_t TAMANHO_BUFFER = 16 * 1024 * 1024; // Padrão 16MB

void copiar_arquivo_turbo(const fs::path& origem, const fs::path& destino, std::vector<char>& buffer) {
    std::ifstream input(origem, std::ios::binary);
    std::ofstream output(destino, std::ios::binary);

    if (!input || !output) return;

    while (input) {
        input.read(buffer.data(), TAMANHO_BUFFER);
        if (input.gcount() > 0) {
            output.write(buffer.data(), input.gcount());
        }
    }
    
    try {
        fs::last_write_time(destino, fs::last_write_time(origem));
    } catch (...) {}
}

int main(int argc, char* argv[]) {
    // Agora aceitamos um 3º argumento opcional (buffer)
    if (argc < 3) {
        std::cout << "Uso: turbo_copy.exe <origem> <destino> [buffer_mb]\n";
        return 1;
    }

    fs::path pasta_origem = argv[1];
    fs::path pasta_destino = argv[2];

    // Lógica para ler o Buffer do argumento
    if (argc >= 4) {
        try {
            int mb = std::stoi(argv[3]);
            // Proteção (Clamping)
            if (mb < 1) mb = 1;
            if (mb > 1024) mb = 1024;
            
            TAMANHO_BUFFER = static_cast<size_t>(mb) * 1024 * 1024;
        } catch (...) {
            // Se der erro na conversão, mantém 16MB
            TAMANHO_BUFFER = 16 * 1024 * 1024;
        }
    }

    // Feedback visual do buffer escolhido
    std::cout << "CONFIG_BUFFER: " << (TAMANHO_BUFFER / (1024*1024)) << " MB\n";

    if (!fs::exists(pasta_origem) || !fs::exists(pasta_destino)) return 1;

    // --- FASE 1: PRÉ-SCAN ---
    uintmax_t total_arquivos = 0;
    uintmax_t total_bytes = 0;

    for (const auto& entrada : fs::recursive_directory_iterator(pasta_origem)) {
        if (entrada.is_regular_file()) {
            total_arquivos++;
            total_bytes += entrada.file_size();
        }
    }
    
    std::cout << "TOTAL_INFO: " << total_arquivos << " " << total_bytes << "\n" << std::flush;

    // --- FASE 2: EXECUÇÃO ---
    std::vector<char> buffer(TAMANHO_BUFFER);
    int copiados = 0;
    uintmax_t bytes_copiados = 0;

    for (const auto& entrada : fs::recursive_directory_iterator(pasta_origem)) {
        if (entrada.is_regular_file()) {
            fs::path origem = entrada.path();
            uintmax_t tamanho_atual = entrada.file_size();

            fs::path relativo = fs::relative(origem, pasta_origem);
            fs::path destino = pasta_destino / relativo.filename();

            copiar_arquivo_turbo(origem, destino, buffer);
            
            copiados++;
            bytes_copiados += tamanho_atual;

            std::cout << "PROGRESSO: " << copiados << " " << bytes_copiados << "\n" << std::flush;
        }
    }

    return 0;
}