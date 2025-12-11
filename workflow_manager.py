import os
import shutil
import subprocess
import concurrent.futures
import time


# workflow_manager.py

# Adicione esta função
def _limpar_diretorio(caminho_pasta, callback_log=None):
    """
    Verifica se um diretório existe. Se sim, apaga todo o seu conteúdo
    e o recria vazio.
    """
    print(f"Verificando e limpando o diretório: {caminho_pasta}")
    if callback_log: callback_log(f"Limpando o diretório: {caminho_pasta}...")
    try:
        if os.path.exists(caminho_pasta):
            shutil.rmtree(caminho_pasta)
            print(f"Diretório '{caminho_pasta}' removido com sucesso.")
        
        os.makedirs(caminho_pasta)
        print(f"Diretório '{caminho_pasta}' recriado vazio.")
        if callback_log: callback_log("✓ Diretório limpo e recriado com sucesso.")
        return True
    
    except OSError as e:
        print(f"ERRO: Não foi possível limpar o diretório '{caminho_pasta}'.")
        if callback_log: callback_log(f"ERRO: Não foi possível limpar o diretório '{caminho_pasta}'.")
        print(f"Motivo: {e}")
        return False
        
def _copiar_arquivos(caminho_origem, caminho_destino, buffer_mb, callback_progresso, callback_log=None):
    """
    Delega a cópia para o executável externo turbo_copy.exe e monitora o progresso em tempo real.
    """
    print("Iniciando motor de cópia C++...")
    if callback_log: callback_log("Iniciando motor turbo_copy.exe...")
    
    # Detecta onde o script está rodando (seja .py ou .exe descompactado)
    base_path = os.path.dirname(os.path.abspath(__file__))
    caminho_executavel = os.path.join(base_path, "turbo_copy.exe")
    
    if not os.path.exists(caminho_executavel):
        msg = f"ERRO: Executável '{caminho_executavel}' não encontrado."
        print(msg)
        if callback_log: callback_log(msg)
        return False

    try:
        # Marca o início real da cópia
        inicio_copia = time.time()

        processo = subprocess.Popen(
            [caminho_executavel, caminho_origem, caminho_destino, str(buffer_mb)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1 
        )
        
        # Variáveis de estado
        arquivos_copiados = 0
        total_arquivos = 0
        bytes_totais = 0
        bytes_atuais = 0
        
        while True:
            linha = processo.stdout.readline()
            if not linha and processo.poll() is not None:
                break 
            
            if linha:
                linha = linha.strip()
                
                if linha.startswith("TOTAL_INFO:"):
                    try:
                        partes = linha.split()
                        total_arquivos = int(partes[1])
                        bytes_totais = int(partes[2])
                    except ValueError:
                        pass

                elif linha.startswith("PROGRESSO:"):
                    try:
                        partes = linha.split()
                        arquivos_copiados = int(partes[1])
                        bytes_atuais = int(partes[2])
                        
                        if callback_progresso:
                            callback_progresso(
                                arquivos_copiados, 
                                total_arquivos, 
                                "Copiando...", 
                                bytes_atuais, 
                                bytes_totais
                            )
                    except ValueError:
                        pass
        
        codigo_retorno = processo.poll()
        
        if codigo_retorno == 0:
            # --- CÁLCULO DO RESUMO FINAL ---
            tempo_total = time.time() - inicio_copia
            if tempo_total <= 0: tempo_total = 0.001 # Evita divisão por zero
            
            mb_total = bytes_totais / (1024 * 1024)
            velocidade_media = mb_total / tempo_total
            
            relatorio = (
                f"=== RELATÓRIO FINAL ===\n"
                f"Total de Arquivos: {total_arquivos}\n"
                f"Volume Total: {mb_total:.2f} MB\n"
                f"Tempo Total: {tempo_total:.2f} segundos\n"
                f"Velocidade Média: {velocidade_media:.2f} MB/s\n"
                f"======================="
            )
            
            print(relatorio)
            if callback_log: callback_log(relatorio)
            
            # Garante que a barra mostre 100%
            if callback_progresso:
                callback_progresso(total_arquivos, total_arquivos, "Finalizado", bytes_totais, bytes_totais)
            return True
        else:
            erro = processo.stderr.read()
            msg_erro = f"ERRO no motor C++: {erro}"
            print(msg_erro)
            if callback_log: callback_log(msg_erro)
            return False

    except Exception as e:
        print(f"ERRO CRÍTICO ao chamar subprocesso: {e}")
        if callback_log: callback_log(f"ERRO CRÍTICO: {e}")
        return False


def _abrir_lightroom(caminho_para_importar, callback_log=None):
    """
    Encontra e abre o Adobe Lightroom Classic, instruindo-o a importar
    da pasta especificada.
    """
    print("Tentando abrir o Adobe Lightroom Classic...")
    if callback_log: callback_log("Tentando abrir o Adobe Lightroom Classic...")
    
    # Caminho padrão de instalação do Lightroom Classic no Windows.
    # Pode precisar de ajuste se o usuário instalou em outro lugar.
    caminho_lightroom_exe = "C:\\Program Files\\Adobe\\Adobe Lightroom Classic\\lightroom.exe"

    if not os.path.exists(caminho_lightroom_exe):
        print(f"ERRO: Executável do Lightroom não encontrado em '{caminho_lightroom_exe}'.")
        print("Verifique se o Lightroom está instalado no caminho padrão.")
        if callback_log: callback_log(f"ERRO: Executável do Lightroom não encontrado.")
        return False

    try:
        # O comando para o Lightroom importar é --import <caminho>
        comando = [caminho_lightroom_exe, "--import", caminho_para_importar]
        print(f"Executando comando: {' '.join(comando)}")
        
        # subprocess.Popen inicia o processo e não espera ele terminar.
        subprocess.Popen(comando)
        
        print("Comando para abrir o Lightroom enviado com sucesso.")
        if callback_log: callback_log("✓ Comando para abrir o Lightroom enviado com sucesso.")
        return True
    
    except Exception as e:
        print(f"ERRO: Falha ao tentar abrir o Lightroom.")
        print(f"Motivo: {e}")
        if callback_log: callback_log(f"ERRO: Falha ao tentar abrir o Lightroom.")
        return False

def executar_fluxo_de_trabalho(caminho_origem, caminho_destino, buffer_mb=16, callback_progresso=None, callback_log=None):
    """
    Função principal que orquestra todo o fluxo de trabalho.
    Agora aceita um callback para reportar progresso.
    """
    print(f"Fluxo iniciado!")
    print(f"Origem: {caminho_origem}")
    print(f"Destino: {caminho_destino}")
    print("-----------------------------------------")

    # 1. Limpar o diretório de destino
    if not _limpar_diretorio(caminho_destino, callback_log):
        return False

    if not _copiar_arquivos(caminho_origem, caminho_destino, buffer_mb, callback_progresso, callback_log):
        return False
    
    if not _abrir_lightroom(caminho_destino, callback_log):
        return False

    print("-----------------------------------------")
    print("Fluxo concluído com sucesso.")
    if callback_log: callback_log("🎉 Fluxo concluído com sucesso.")
    return True