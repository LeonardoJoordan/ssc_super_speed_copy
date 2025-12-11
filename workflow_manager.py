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
    
def _copiar_um_arquivo(dados):
    """
    Versão revertida para shutil.copy2.
    Motivo: A implementação interna em C do Python provou ser mais rápida 
    que loops de leitura/escrita manuais para este cenário.
    """
    origem, destino = dados
    try:
        # copy2 é a ferramenta mais otimizada que temos.
        # Ela preserva os metadados (importante para suas fotos) e roda em baixo nível.
        shutil.copy2(origem, destino)
        return True
    except Exception as e:
        print(f"Erro ao copiar {origem}: {e}")
        return False
    
def _copiar_arquivos(caminho_origem, caminho_destino, callback_progresso, callback_log=None):
    """
    Copia arquivos em paralelo, calculando tamanho total e velocidade média.
    """
    print("Iniciando cópia paralela com monitoramento de volume...")
    if callback_log: callback_log("Iniciando cópia paralela...")
    
    try:
        # Passo 1: Listar e Calcular Tamanho Total
        if callback_log: callback_log("Calculando volume total dos arquivos...")
        
        lista_tarefas = []
        bytes_totais_fluxo = 0
        
        for pasta_raiz, _, nomes_arquivos in os.walk(caminho_origem):
            for nome_arquivo in nomes_arquivos:
                caminho_completo_origem = os.path.join(pasta_raiz, nome_arquivo)
                caminho_completo_destino = os.path.join(caminho_destino, nome_arquivo)
                
                # Obtém o tamanho do arquivo para as estatísticas
                tamanho_arquivo = os.path.getsize(caminho_completo_origem)
                bytes_totais_fluxo += tamanho_arquivo
                
                # Guarda origem, destino e tamanho na tarefa
                lista_tarefas.append((caminho_completo_origem, caminho_completo_destino, tamanho_arquivo))
        
        total_arquivos = len(lista_tarefas)
        mb_total = bytes_totais_fluxo / (1024 * 1024)
        print(f"Total: {total_arquivos} arquivos | {mb_total:.1f} MB")
        if callback_log: callback_log(f"Volume total encontrado: {mb_total:.1f} MB")

        # Passo 2: Execução Paralela
        arquivos_copiados = 0
        bytes_copiados = 0
        inicio_copia = time.time()
        
        # max_workers=8 para saturar o UHS-II sem travar o controlador
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Mapeia futures para (caminho_origem, tamanho)
            futures = {
                executor.submit(_copiar_um_arquivo, (t[0], t[1])): (t[0], t[2]) 
                for t in lista_tarefas
            }
            
            for future in concurrent.futures.as_completed(futures):
                origem, tamanho = futures[future]
                
                # Se a cópia foi sucesso (o future retorna True/False da função _copiar_um_arquivo)
                if future.result():
                    arquivos_copiados += 1
                    bytes_copiados += tamanho
                    
                    nome_arquivo = os.path.basename(origem)
                    if callback_progresso:
                        # Passamos agora os bytes atuais e totais
                        callback_progresso(arquivos_copiados, total_arquivos, nome_arquivo, bytes_copiados, bytes_totais_fluxo)

        # Passo 3: Relatório Final de Velocidade
        tempo_total = time.time() - inicio_copia
        velocidade_media = (bytes_copiados / (1024 * 1024)) / tempo_total if tempo_total > 0 else 0
        
        msg_final = f"✓ Cópia concluída! Média: {velocidade_media:.1f} MB/s em {tempo_total:.1f}s"
        print(msg_final)
        if callback_log: callback_log(msg_final)
        
        return True

    except Exception as e:
        print(f"ERRO CRÍTICO: {e}")
        if callback_log: callback_log(f"ERRO: {e}")
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

def executar_fluxo_de_trabalho(caminho_origem, caminho_destino, callback_progresso=None, callback_log=None):
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

    if not _copiar_arquivos(caminho_origem, caminho_destino, callback_progresso, callback_log):
        return False
    
    if not _abrir_lightroom(caminho_destino, callback_log):
        return False

    print("-----------------------------------------")
    print("Fluxo concluído com sucesso.")
    if callback_log: callback_log("🎉 Fluxo concluído com sucesso.")
    return True