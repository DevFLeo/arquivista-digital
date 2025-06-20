# app.py - Versão Final com Sistema de Login Individual

import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configurações Principais ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
SECRET_KEY = 'uma-chave-super-secreta-e-longa-para-seguranca'
EXTENSION_MAP = {
    'png': 'imagens/png', 'jpg': 'imagens/jpg_jpeg', 'jpeg': 'imagens/jpg_jpeg',
    'gif': 'imagens/gif', 'webp': 'imagens/webp', 'svg': 'imagens/vetoriais',
    'docx': 'documentos/word', 'doc': 'documentos/word', 'xlsx': 'documentos/excel',
    'xls': 'documentos/excel', 'pptx': 'documentos/powerpoint', 'ppt': 'documentos/powerpoint',
    'pdf': 'documentos/pdf', 'txt': 'documentos/texto', 'mp3': 'multimedia/audio',
    'wav': 'multimedia/audio', 'mp4': 'multimedia/video', 'zip': 'compactados', 'rar': 'compactados'
}
ALLOWED_EXTENSIONS = set(EXTENSION_MAP.keys())

# --- Inicialização da Aplicação ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = SECRET_KEY
# --- 2. NOVA CONFIGURAÇÃO DO BANCO DE DADOS ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'arquivista.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- 3. INICIALIZAÇÃO DOS SISTEMAS DE BD E LOGIN ---
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Se um usuário não logado tentar acessar uma página protegida, ele será redirecionado para a rota 'login'.

# --- 4. MODELO DE USUÁRIO E CARREGADOR DE SESSÃO ---
# A classe User agora herda de UserMixin, que já traz funcionalidades prontas para o login_manager.
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Esta função é exigida pelo Flask-Login para saber como encontrar um usuário a partir do ID guardado na sessão.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Funções Auxiliares (Modificadas para funcionar por usuário) ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_upload_folder(user_id):
    """Retorna o caminho da pasta de uploads de um usuário específico."""
    return os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))

def scan_organized_files(user_id):
    """Escaneia os arquivos de um usuário específico."""
    organized_files = {}
    user_folder = get_user_upload_folder(user_id)
    
    if not os.path.isdir(user_folder):
        return {}

    for root, dirs, files in os.walk(user_folder):
        if not files: continue
        
        category_path = os.path.relpath(root, user_folder)
        if category_path == '.': continue

        category_name = category_path.replace(os.path.sep, ' / ')
        organized_files[category_name] = [{'nome': f, 'caminho': os.path.join(category_path, f)} for f in files]
        
    return organized_files

# --- 5. NOVAS ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Este nome de usuário já existe.')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Conta criada com sucesso! Por favor, faça o login.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required # Só quem está logado pode deslogar
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- 6. ROTAS PRINCIPAIS (AGORA PROTEGIDAS) ---
@app.route('/')
@login_required # Protege a página principal
def index():
    arquivos = scan_organized_files(current_user.id)
    return render_template('index.html', arquivos_organizados=arquivos)

@app.route('/upload', methods=['POST'])
@login_required # Protege a rota de upload
def upload_file():
    files = request.files.getlist('arquivo')
    user_folder = get_user_upload_folder(current_user.id)
    # ... (a lógica de upload agora precisa salvar em user_folder) ...
    successful_uploads = 0
    for file in files:
        if file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_ext = filename.rsplit('.', 1)[1].lower()
            destination_subfolder = EXTENSION_MAP.get(file_ext, 'outros')
            destination_path = os.path.join(user_folder, destination_subfolder)
            os.makedirs(destination_path, exist_ok=True)
            file.save(os.path.join(destination_path, filename))
            successful_uploads += 1
        else:
            if file.filename: flash(f'Arquivo "{file.filename}" ignorado (tipo não permitido).')
    
    if successful_uploads > 0: flash(f'{successful_uploads} arquivo(s) organizados com sucesso!')
    else: flash('Nenhum arquivo válido foi enviado.')
    return redirect(url_for('index'))

# --- Bloco de Execução Principal ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Cria as tabelas do banco de dados se não existirem
    app.run(host='127.0.0.1', port=5000, debug=True)