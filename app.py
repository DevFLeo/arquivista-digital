# app.py

import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

# --- 1. Configuração Centralizada ---
# Mover as configurações para uma classe é uma prática limpa e organizada.
class Config:
    UPLOAD_FOLDER = 'uploads'
    MAX_FILES = 40
    SECRET_KEY = 'uma-chave-super-secreta-para-seguranca'
    LOG_FILE = 'arquivista.log'
    EXTENSION_MAP = {
        'png': 'imagens/png', 'jpg': 'imagens/jpg_jpeg', 'jpeg': 'imagens/jpg_jpeg',
        'gif': 'imagens/gif', 'webp': 'imagens/webp', 'svg': 'imagens/vetoriais',
        'docx': 'documentos/word', 'doc': 'documentos/word', 'xlsx': 'documentos/excel',
        'xls': 'documentos/excel', 'pptx': 'documentos/powerpoint', 'ppt': 'documentos/powerpoint',
        'pdf': 'documentos/pdf', 'txt': 'documentos/texto', 'mp3': 'multimedia/audio',
        'wav': 'multimedia/audio', 'mp4': 'multimedia/video', 'zip': 'compactados', 'rar': 'compactados'
    }
    ALLOWED_EXTENSIONS = set(EXTENSION_MAP.keys())

# --- 2. Inicialização e Configuração da Aplicação ---
app = Flask(__name__)
app.config.from_object(Config)

# --- 3. Configuração do Logging ---
# Configura um sistema de log para registrar atividades e erros em um arquivo.
logging.basicConfig(
    filename=app.config['LOG_FILE'],
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

# --- 4. Funções Auxiliares ---
def allowed_file(filename):
    """Verifica se a extensão de um arquivo é permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def scan_organized_files():
    """Escaneia a pasta de uploads e retorna um dicionário de arquivos organizados."""
    organized_files = {}
    upload_folder = app.config['UPLOAD_FOLDER']
    
    # os.walk percorre recursivamente todas as pastas e arquivos
    for root, dirs, files in os.walk(upload_folder):
        if not files:
            continue
        # Pega o nome da categoria (ex: 'imagens/png') a partir do caminho completo
        category_path = os.path.relpath(root, upload_folder)
        category_name = category_path.replace(os.path.sep, ' / ')
        
        organized_files[category_name] = []
        for filename in files:
            organized_files[category_name].append({
                'nome': filename,
                'caminho': os.path.join(category_path, filename) # Caminho relativo para a função de delete
            })
    return organized_files

# --- 5. Rotas da Aplicação ---
@app.route('/')
def index():
    """Rota principal que exibe o formulário e a lista de arquivos."""
    app.logger.info("Página principal acessada.")
    organized_files = scan_organized_files()
    return render_template('index.html', arquivos_organizados=organized_files)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Rota para lidar com o upload e organização dos arquivos."""
    uploaded_files = request.files.getlist("arquivo")
    
    if len(uploaded_files) > app.config['MAX_FILES']:
        flash(f'Erro: Limite de {app.config["MAX_FILES"]} arquivos por vez excedido.')
        app.logger.warning(f'Tentativa de upload de {len(uploaded_files)} arquivos (limite: {app.config["MAX_FILES"]}).')
        return redirect(url_for('index'))

    if not uploaded_files or uploaded_files[0].filename == '':
        flash('Nenhum arquivo selecionado!')
        return redirect(url_for('index'))

    successful_uploads = 0
    for file in uploaded_files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_ext = filename.rsplit('.', 1)[1].lower()
            
            destination_subfolder = app.config['EXTENSION_MAP'].get(file_ext, 'outros')
            destination_path = os.path.join(app.config['UPLOAD_FOLDER'], destination_subfolder)
            
            os.makedirs(destination_path, exist_ok=True)
            
            final_path = os.path.join(destination_path, filename)
            file.save(final_path)
            
            app.logger.info(f'Arquivo "{filename}" salvo em "{destination_path}".')
            successful_uploads += 1
        else:
            if file.filename:
                flash(f'Arquivo "{file.filename}" ignorado (tipo não permitido).')
                app.logger.warning(f'Tentativa de upload de arquivo não permitido: {file.filename}')

    if successful_uploads > 0:
        flash(f'{successful_uploads} arquivo(s) foram organizados com sucesso!')
    
    return redirect(url_for('index'))

@app.route('/delete/<path:filepath>', methods=['POST'])
def delete_file(filepath):
    """Rota para deletar um arquivo específico."""
    # Medida de segurança: constrói o caminho absoluto e verifica se ele realmente está dentro da pasta de uploads
    # Isso previne ataques de "Directory Traversal".
    upload_folder_abs = os.path.abspath(app.config['UPLOAD_FOLDER'])
    file_to_delete_abs = os.path.abspath(os.path.join(upload_folder_abs, filepath))

    if os.path.commonpath([file_to_delete_abs, upload_folder_abs]) != upload_folder_abs:
        flash("Erro: Tentativa de acesso a um caminho inválido.")
        app.logger.error(f'Tentativa de deleção de arquivo fora do diretório de uploads: {filepath}')
        return redirect(url_for('index'))

    try:
        os.remove(file_to_delete_abs)
        flash(f'Arquivo "{os.path.basename(filepath)}" deletado com sucesso.')
        app.logger.info(f'Arquivo deletado: {file_to_delete_abs}')
    except FileNotFoundError:
        flash("Erro: Arquivo não encontrado para deleção.")
        app.logger.error(f'Tentativa de deletar arquivo não existente: {file_to_delete_abs}')
    except Exception as e:
        flash(f"Ocorreu um erro ao deletar o arquivo: {e}")
        app.logger.error(f"Erro ao deletar {file_to_delete_abs}: {e}")
        
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)

    

