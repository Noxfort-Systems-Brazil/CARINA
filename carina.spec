# -*- mode: python ; coding: utf-8 -*-
# CARINA Spec File - Versão Completa (com todas as dependências e correção cuDNN)
from PyInstaller.utils.hooks import collect_all
import sys
import os
import glob # Necessário para busca manual de libs se preciso
import traceback # Para debug

# --- Usa os.getcwd() para obter o diretório raiz do projeto ---
project_base = os.getcwd()
print(f"INFO: Project base directory detected as: {project_base}")
# --- Fim ---

# --- Bloco de Coleta Seguro (v8) ---
# Inicializa as listas
all_hiddenimports = []
all_datas = []
all_binaries = []

# Lista de pacotes que precisam de coleta profunda
packages_to_collect = [
    'torch_geometric',
    'captum',
    'transformers',
    'accelerate',
    'pandas',
    'scipy',
    'sklearn',
    'websockets',
    'tensorboard',
    'google.protobuf',
    'nvidia', # Coletar pacotes da NVIDIA (cuDNN, cuBLAS)
    # --- CORREÇÃO: Pacotes que faltavam e causavam crash na inicialização ---
    'grpc',        # gRPC (central_controller.py)
    'flet',        # UI Framework
    'flet_core',   # Flet internals
    'flet_runtime', # Flet runtime
    'prometheus_client', # Métricas (metrics_manager.py)
    'psycopg2',    # PostgreSQL (database_manager.py)
    'paho',        # MQTT (monitor_client.py)
    'pysnmp',      # SNMP (hardware communication)
]

def _is_valid_spec(item):
    """Verifica se um item está no formato (str, str) que o PyInstaller espera para datas/binaries."""
    return (
        isinstance(item, (list, tuple)) and
        len(item) == 2 and
        isinstance(item[0], str) and
        isinstance(item[1], str)
    )

print("INFO: Iniciando coleta profunda de pacotes...")
for package in packages_to_collect:
    try:
        print(f"INFO: Coletando de '{package}'...")
        # Coleta tudo que o pacote precisa
        hi, da, bi = collect_all(package)
        
        # Filtra a lista 'hi' para garantir que contém APENAS strings.
        if hi:
            for item in hi:
                if isinstance(item, str):
                    all_hiddenimports.append(item)
                else:
                    print(f"AVISO (hiddenimport): Ignorando item mal formatado de '{package}': {item}")
        
        # Filtramos agressivamente para incluir APENAS 2-tuplas de strings.
        if da:
            for item in da:
                if _is_valid_spec(item):
                    all_datas.append(item)
                else:
                    print(f"AVISO (data): Ignorando item mal formatado de '{package}': {item}")
        
        if bi:
            for item in bi:
                if _is_valid_spec(item):
                    all_binaries.append(item)
                else:
                    print(f"AVISO (binary): Ignorando item mal formatado de '{package}': {item}")

        print(f"INFO: Coleta de '{package}' concluída.")
    except Exception as e:
        if package == 'nvidia':
            print(f"AVISO: Falha ao coletar '{package}'. Se estiver usando GPU, isso é crítico. Erro: {e}")
        else:
            print(f"ERRO: Falha ao coletar de '{package}'. Erro: {e}")
            raise # Para outros pacotes, para o build

print("INFO: Coleta profunda de pacotes concluída.")

# --- CORREÇÃO CRÍTICA: INCLUSÃO MANUAL DA LIB CUDNN (VAI AQUI) ---
print("INFO: Iniciando busca manual e inclusão de libs CUDNN...")
cuda_libs = []
try:
    import torch
    # Caminho provável das bibliotecas do PyTorch no ambiente de build
    torch_lib_dir = os.path.join(os.path.dirname(torch.__file__), 'lib')
    
    # Bibliotecas CUDNN que faltaram no log
    lib_patterns = [
        'libcudnn_ops_infer.so.*',
        'libcudnn_cnn_infer.so.*',
        'libcudnn.so.*' 
    ]
    
    for pattern in lib_patterns:
        # Busca recursivamente
        found_libs = glob.glob(os.path.join(torch_lib_dir, pattern), recursive=True)
        for lib_path in found_libs:
             # Adiciona como binário. O ponto ('.') no destino significa "na raiz do executável".
             cuda_libs.append((lib_path, '.')) 
             print(f"INFO: Incluindo lib CUDA: {lib_path}")
             
except Exception as e:
    print(f"ERRO: Falha crítica na busca manual por libs CUDA/cuDNN: {traceback.format_exc()}")
    
all_binaries.extend(cuda_libs)
print(f"INFO: Total de {len(cuda_libs)} libs CUDNN adicionadas manualmente a all_binaries.")
# --- FIM DA CORREÇÃO CUDNN ---


# --- Adiciona importações manuais (Correções) ---
all_hiddenimports.extend([
    'PySide6.QtSvg',
    'PySide6.QtNetwork',
    'scipy._lib.array_api_compat.numpy.fft',
    'torch_geometric.graphgym',
    'torch_geometric.graphgym.loader',
    'torch_geometric.datasets',
    'torch_geometric.profile',
    'websockets',
    'websockets.sync',
    'websockets.sync.client',
    'websockets.sync.server',
    'websockets.legacy',
    'websockets.legacy.client',
    'websockets.legacy.server',
    'tensorboard',
    'tensorboard.compat',
    'tensorboard.compat.tensorflow_stub',
    'tensorboard.plugins',
    'tensorboard.plugins.projector',
    'tensorboard.summary',
    'google.protobuf.struct_pb2',
    'google.protobuf.timestamp_pb2',
    'google.protobuf.any_pb2',
    'google.protobuf.duration_pb2',
    # Transformers & Accelerate (Explicit)
    'transformers',
    'accelerate',
    'safetensors',
    'huggingface_hub',
    # Importações explícitas da NVIDIA
    'nvidia.cudnn',
    'nvidia.cublas',
    'nvidia.cuda_nvrtc',
    'nvidia.cuda_runtime',
    # --- CORREÇÃO: Módulos que faltavam (causavam crash) ---
    # gRPC
    'grpc',
    'grpc._cython',
    'grpc._cython.cygrpc',
    'grpc.experimental',
    'grpc.framework',
    'grpc.framework.foundation',
    # Flet UI
    'flet',
    'flet.app',
    'flet.canvas',
    'flet.core',
    'flet_core',
    'flet_runtime',
    # Database & Messaging
    'psycopg2',
    'psycopg2._psycopg',
    'psycopg2.extensions',
    'psycopg2.extras',
    'paho',
    'paho.mqtt',
    'paho.mqtt.client',
    'paho.mqtt.publish',
    'paho.mqtt.subscribe',
    # Metrics
    'prometheus_client',
    'prometheus_client.exposition',
    'prometheus_client.metrics',
    'prometheus_client.metrics_core',
    # SNMP
    'pysnmp',
    'pysnmp.hlapi',
])

# --- Adiciona Dados do Projeto (Assets, Configs) ---
all_datas.extend([
    # --- CORREÇÃO 7 (Erro de Runtime 'No module named utils') ---
    (os.path.join(project_base, 'src'), 'src'),
    # --- FIM DA CORREÇÃO 7 ---

    # --- CORREÇÃO: Proto/gRPC generated files ---
    (os.path.join(project_base, 'proto'), 'proto'),

    # Assets da UI
    (os.path.join(project_base, 'ui/assets'), 'ui/assets'),
    # Assets de localização da UI
    (os.path.join(project_base, 'ui/locales'), 'ui/locales'),
    # Assets de localização do Backend
    (os.path.join(project_base, 'src/locale_backend'), 'locale_backend'),
    # Arquivo de Configuração
    (os.path.join(project_base, 'config/settings.ini'), 'config'),
    # Qwen SLM (Frozen Neural Network Weights)
    (os.path.join(project_base, 'Model_Vault'), 'Model_Vault')
])
# --- Fim da Coleta ---


# 4. Hooks de Runtime:
# O hook personalizado para adicionar 'src' ao sys.path.
runtime_hooks = [os.path.join(project_base, 'src/hooks/pyi_runtime_hooks.py')]

a = Analysis(
    ['carina.py'], # Script principal na raiz
    
    pathex=[project_base], # Adiciona a raiz do projeto ao path de análise
    
    # Passa as listas filtradas e corretas
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks, # Hook está em src/hooks
    
    excludes=['libstdc++.so.6', 'tkinter', '_tkinter'],    
    # --- CORREÇÃO 18 (Erro OSError / TorchScript) ---
    noarchive=True,
    # --- FIM DA CORREÇÃO 18 ---
    
    optimize=0, # Manter 0 durante debug
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
)

# --- CORREÇÃO 17 (Filtro Manual GLIBCXX) ---
print("INFO: Iniciando Correção 17 (Filtro Manual GLIBCXX)...")
filtered_binaries = []
for item in a.binaries:
    dest_path = item[0]
    # Remove libstdc++.so.6 incluído pelo PyTorch (causa erro GLIBCXX)
    if 'libstdc++.so.6' in dest_path:
        print(f"AVISO (Correção 17): Removendo binário problemático: {item}")
    else:
        filtered_binaries.append(item)
a.binaries = filtered_binaries
print("INFO: Correção 17 (Filtro Manual GLIBCXX) concluída.")
# --- FIM DA CORREÇÃO 17 ---

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='carina', # Nome final do executável
    debug=False, # Mudar para True se precisar de mais debug do PyInstaller
    bootloader_ignore_signals=False,
    strip=False,
    upx=False, # UPX Desativado (recomendado para debug e compatibilidade)
    console=True, # Mantém console visível
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Caminho do ícone relativo à raiz (onde o .spec está)
    icon=os.path.join('ui', 'assets', 'images', 'logo.png')
)

# --- Bloco de Coleta e Agrupamento ---
coll = COLLECT(
    exe,
    a.binaries, # Usa a lista a.binaries JÁ FILTRADA
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False, # UPX Desativado
    upx_exclude=[],
    name='carina' # Nome da pasta final em 'dist/'
)