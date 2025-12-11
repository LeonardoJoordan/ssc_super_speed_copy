# main.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import json
import workflow_manager
import threading
import time
from datetime import datetime, timedelta


# --- Configurações de Persistência ---
# Construímos o caminho para o nosso arquivo de configurações na pasta temporária do Windows.
# Usar 'os.path.join' garante que o caminho seja montado corretamente.
PASTA_TEMP = os.environ.get('TEMP', '.') # Pega a pasta TEMP, ou o diretório atual se não encontrar.
ARQUIVO_CONFIG = os.path.join(PASTA_TEMP, "expo_facil_config.json")
# Nossa variável para controlar o tempo de início de cada operação de cópia
tempo_inicio_copia = None

# --- Funções de Persistência (Salvar/Carregar JSON) ---
def salvar_caminhos(origem, destino):
    """Salva os caminhos de origem e destino em um arquivo JSON."""
    config_data = {'origem': origem, 'destino': destino}
    try:
        with open(ARQUIVO_CONFIG, 'w') as f:
            json.dump(config_data, f)
    except IOError as e:
        print(f"Erro ao salvar configurações: {e}")

def carregar_caminhos():
    """Carrega os caminhos do arquivo JSON, se ele existir."""
    if not os.path.exists(ARQUIVO_CONFIG):
        return None, None # Retorna None se o arquivo ainda não existe
    try:
        with open(ARQUIVO_CONFIG, 'r') as f:
            config_data = json.load(f)
            return config_data.get('origem'), config_data.get('destino')
    except (IOError, json.JSONDecodeError) as e:
        print(f"Erro ao carregar configurações: {e}")
        return None, None
    
def log_message(message):
    """Adiciona uma mensagem ao painel de log da interface."""
    log_text.config(state="normal")
    log_text.insert(tk.END, message + "\n")
    log_text.config(state="disabled")
    log_text.see(tk.END) # Auto-scroll para a última mensagem
    janela.update_idletasks()

# --- Funções da Interface ---
def atualizar_progresso(progresso_atual, progresso_total, nome_arquivo, bytes_atuais=0, bytes_totais=0):
    """
    Atualiza a UI com layout vertical de 4 linhas (Dashboard).
    Foco: Métricas claras e tempo formatado (HH:MM:SS).
    """
    global tempo_inicio_copia

    if tempo_inicio_copia is None and progresso_atual > 0:
        tempo_inicio_copia = time.time()

    if progresso_total > 0:
        percentual = (progresso_atual / progresso_total) * 100
        barra_progresso['value'] = percentual

        # --- Cálculos ---
        velocidade_mb_s = 0.0
        mb_atuais = bytes_atuais / (1024 * 1024)
        mb_totais = bytes_totais / (1024 * 1024)
        mb_restantes = mb_totais - mb_atuais
        
        str_tempo_restante = "--:--:--"

        if tempo_inicio_copia and bytes_atuais > 0:
            tempo_decorrido = time.time() - tempo_inicio_copia
            
            if tempo_decorrido > 0:
                velocidade_mb_s = mb_atuais / tempo_decorrido

            if velocidade_mb_s > 0:
                segundos_restantes = mb_restantes / velocidade_mb_s
                # Formata segundos para HH:MM:SS usando timedelta
                str_tempo_restante = str(timedelta(seconds=int(segundos_restantes)))

        # --- Montagem Visual (4 Linhas) ---
        
        # Linha 1: Quantidade de Arquivos
        linha_1 = f"Arquivos: {progresso_atual} de {progresso_total}"

        # Linha 2: Tempo Restante (Formatado)
        linha_2 = f"Tempo Restante: {str_tempo_restante}"

        # Linha 3: Volume de Dados (Copiados | Restantes)
        linha_3 = f"Dados: {mb_atuais:.0f} MB copiados | {mb_restantes:.0f} MB restam"

        # Linha 4: Velocidade
        linha_4 = f"Velocidade: {velocidade_mb_s:.1f} MB/s"

        # Unindo com quebras de linha
        label_progresso_texto.set(f"{linha_1}\n{linha_2}\n{linha_3}\n{linha_4}")
        janela.update_idletasks()

def verificar_estado_botao_iniciar():
    """Ativa o botão 'Iniciar' apenas se ambas as pastas foram selecionadas."""
    if caminho_origem.get() and caminho_destino.get():
        botao_iniciar.config(state=tk.NORMAL, bg="#4CAF50")
    else:
        botao_iniciar.config(state=tk.DISABLED, bg="#A0A0A0")

def selecionar_pasta(variavel_caminho, label_texto):
    """Função genérica para selecionar uma pasta e atualizar a UI."""
    caminho_selecionado = filedialog.askdirectory(title=f"Selecione a {label_texto}")
    if caminho_selecionado:
        variavel_caminho.set(caminho_selecionado)
        salvar_caminhos(caminho_origem.get(), caminho_destino.get())
        verificar_estado_botao_iniciar()

# ADICIONE ESTA NOVA VERSÃO DA FUNÇÃO
def iniciar_processo():
    """
    Função chamada pelo botão 'Iniciar'.
    Valida os caminhos e inicia o fluxo de trabalho em uma thread separada.
    """
    origem = caminho_origem.get()
    destino = caminho_destino.get()

    confirmar = messagebox.askyesno(
        "Confirmar Início",
        f"Você está prestes a iniciar o fluxo:\n\n"
        f"1. A pasta '{destino}' será permanentemente esvaziada.\n"
        f"2. Os arquivos de '{origem}' serão copiados para lá.\n"
        f"3. O Lightroom será aberto.\n\n"
        f"Deseja continuar?"
    )
    if not confirmar:
        log_message("Operação cancelada pelo usuário.")
        return

    # Desabilita o botão para evitar cliques múltiplos
    botao_iniciar.config(state="disabled", text="Executando...")

    # Define a função que rodará na thread
    def _executar_em_thread():
        # Reseta nosso cronômetro global para esta execução
        global tempo_inicio_copia
        tempo_inicio_copia = None
        try:
            print("Chamando o workflow_manager a partir da thread...")
            label_progresso_texto.set("Iniciando...")
            barra_progresso['value'] = 0
            janela.update_idletasks()

            sucesso = workflow_manager.executar_fluxo_de_trabalho(
                origem, destino, atualizar_progresso, log_message
            )

            if sucesso:
                label_progresso_texto.set("Cópia Concluída!")
                messagebox.showinfo("Concluído", "O fluxo de trabalho foi executado com sucesso.")
            else:
                label_progresso_texto.set("Ocorreu um erro!")
                messagebox.showerror("Erro", "A operação falhou. Verifique o log para mais detalhes.")
        except Exception as e:
            # Captura qualquer exceção inesperada dentro da thread
            log_message(f"ERRO CRÍTICO NA THREAD: {e}")
            messagebox.showerror("Erro Crítico", f"Ocorreu uma falha inesperada:\n{e}")
        finally:
            # Garante que o botão seja reabilitado, não importa o que aconteça
            botao_iniciar.config(state="normal", text="Iniciar Fluxo")

    # Cria e inicia a thread
    thread = threading.Thread(target=_executar_em_thread)
    thread.daemon = True  # Permite que a janela feche mesmo se a thread estiver rodando
    thread.start()

# --- Construção da Interface Gráfica ---
janela = tk.Tk()
janela.title("Expo Fácil")
janela.geometry("500x500")
janela.minsize(500, 500)

# Variáveis para armazenar os caminhos selecionados
caminho_origem = tk.StringVar()
caminho_destino = tk.StringVar()

# Layout usando um Frame principal
frame = tk.Frame(janela, padx=10, pady=10)
frame.pack(fill="both", expand=True)

# --- Seção Origem ---
frame_origem = tk.LabelFrame(frame, text="Pasta de Origem (Cartão)", padx=5, pady=5)
frame_origem.pack(fill="x", expand=True, pady=5)

label_origem = tk.Label(frame_origem, textvariable=caminho_origem, fg="blue")
label_origem.pack(side="left", fill="x", expand=True)

botao_origem = tk.Button(frame_origem, text="Selecionar...", command=lambda: selecionar_pasta(caminho_origem, "Pasta de Origem"))
botao_origem.pack(side="right")

# --- Seção Destino ---
frame_destino = tk.LabelFrame(frame, text="Pasta de Destino (Para o Lightroom)", padx=5, pady=5)
frame_destino.pack(fill="x", expand=True, pady=5)

label_destino = tk.Label(frame_destino, textvariable=caminho_destino, fg="blue")
label_destino.pack(side="left", fill="x", expand=True)

botao_destino = tk.Button(frame_destino, text="Selecionar...", command=lambda: selecionar_pasta(caminho_destino, "Pasta de Destino"))
botao_destino.pack(side="right")

# --- Botão Iniciar ---
botao_iniciar = tk.Button(
    frame,
    text="Iniciar Fluxo",
    command=iniciar_processo,
    font=("Arial", 12, "bold"),
    pady=10
)
botao_iniciar.pack(pady=20, fill="x", expand=True)

# --- Barra de Progresso ---
frame_progresso = tk.Frame(frame, pady=10)
frame_progresso.pack(fill="x", expand=True)

label_progresso_texto = tk.StringVar(value="Aguardando início...")
label_status = tk.Label(frame_progresso, textvariable=label_progresso_texto, anchor="w")
label_status.pack(fill="x")

barra_progresso = ttk.Progressbar(frame_progresso, orient="horizontal", length=100, mode="determinate")
barra_progresso.pack(fill="x")

# --- Painel de Log ---
frame_log = tk.Frame(frame, pady=5)
frame_log.pack(fill="both", expand=True)

log_text = tk.Text(frame_log, height=6, state="disabled", bg="#f0f0f0", wrap=tk.WORD)
log_text.pack(fill="both", expand=True)

# --- Lógica de Inicialização ---
# Carrega os últimos caminhos salvos ao iniciar o programa
origem_salva, destino_salvo = carregar_caminhos()
if origem_salva:
    caminho_origem.set(origem_salva)
if destino_salvo:
    caminho_destino.set(destino_salvo)

# Verifica o estado do botão com base nos caminhos carregados
verificar_estado_botao_iniciar()

janela.mainloop()