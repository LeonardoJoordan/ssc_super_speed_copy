#include <iostream>
#include <fstream>
#include <filesystem>
#include <vector>
#include <chrono>
#include <iomanip>

// Namespace para encurtar os comandos de sistema de arquivos
namespace fs = std::filesystem;

// Configuração: Buffer de 16MB (A Estratégia do "Caminhão Grande")
const size_t BUFFER_SIZE = 16 * 1024 * 1024;

// Função para formatar bytes em MB
double to_mb(uintmax_t bytes) {
    return static_cast<double>(bytes) / (1024.0 * 1024.0);
}

void copiar_arquivo_turbo(const fs::path& origem, const fs::path& destino, std::vector<char>& buffer) {
    // Abre arquivos em modo binário bruto
    std::ifstream input(origem, std::ios::binary);
    std::ofstream output(destino, std::ios::binary);

    if (!input || !output) {
        std::cerr << "[ERRO] Falha ao abrir: " << origem << "\n";
        return;
    }

    // Loop de Cópia Manual com Buffer Gigante
    while (input) {
        input.read(buffer.data(), BUFFER_SIZE);
        std::streamsize bytes_lidos = input.gcount();
        if (bytes_lidos > 0) {
            output.write(buffer.data(), bytes_lidos);
        }
    }
    
    // Copia metadados (Data de modificação, etc) - Importante para fotos!
    try {
        fs::last_write_time(destino, fs::last_write_time(origem));
    } catch (...) {
        // Ignora erro de data se acontecer, foco é a cópia
    }
}

int main(int argc, char* argv[]) {
    // O programa espera receber: turbo_copy.exe "ORIGEM" "DESTINO"
    if (argc < 3) {
        std::cout << "Uso: turbo_copy.exe <pasta_origem> <pasta_destino>\n";
        return 1;
    }

    fs::path pasta_origem = argv[1];
    fs::path pasta_destino = argv[2];

    if (!fs::exists(pasta_origem) || !fs::exists(pasta_destino)) {
        std::cerr << "[ERRO] Pastas invalidas.\n";
        return 1;
    }

    std::cout << "=== TURBO COPY V1 (C++ ENGINE) ===\n";
    std::cout << "Origem: " << pasta_origem << "\n";
    std::cout << "Destino: " << pasta_destino << "\n";
    std::cout << "Buffer: 16 MB\n";

    // Aloca memória RAM uma única vez para reutilizar
    std::vector<char> buffer(BUFFER_SIZE);
    
    auto inicio = std::chrono::high_resolution_clock::now();
    uintmax_t bytes_totais = 0;
    int arquivos_copiados = 0;

    // Varredura da pasta
    for (const auto& entrada : fs::recursive_directory_iterator(pasta_origem)) {
        if (entrada.is_regular_file()) {
            fs::path caminho_origem = entrada.path();
            // Calcula caminho de destino relativo
            fs::path caminho_relativo = fs::relative(caminho_origem, pasta_origem);
            fs::path caminho_final = pasta_destino / caminho_relativo.filename(); // Flat copy (tudo na raiz)

            // Copia
            copiar_arquivo_turbo(caminho_origem, caminho_final, buffer);
            
            bytes_totais += entrada.file_size();
            arquivos_copiados++;
            
            // Log simples a cada 100 arquivos para não travar o terminal
            if (arquivos_copiados % 100 == 0) {
                 std::cout << "\rCopiados: " << arquivos_copiados << " arquivos..." << std::flush;
            }
        }
    }

    auto fim = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> duracao = fim - inicio;

    double mb_total = to_mb(bytes_totais);
    double velocidade = mb_total / duracao.count();

    std::cout << "\n\n=== RELATORIO DE MISSAO ===\n";
    std::cout << "Arquivos: " << arquivos_copiados << "\n";
    std::cout << "Volume: " << std::fixed << std::setprecision(1) << mb_total << " MB\n";
    std::cout << "Tempo: " << duracao.count() << "s\n";
    std::cout << "VELOCIDADE: " << velocidade << " MB/s\n";

    return 0;
}