# app.py - Versão Completa para Deploy no Render

import os
# A nova importação para o sistema de login
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
# A nova importação para o banco de dados
from flask_sqlalchemy import SQLAlchemy
# A nova importação para a segurança de senhas
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

# --- 1. Configurações e Inicialização ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

# Configura a chave secreta. Em produção, o Render a fornecerá como uma variável de ambiente.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uma-chave-de-desenvolvimento-super-segura')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Lógica para usar o Banco de Dados do Render (PostgreSQL) ou o local (SQLite)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    # O Render usa 'postgres://' mas o SQLAlchemy precisa de 'postgresql://'
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
else:
    # Se não estiver no Render, usa o banco de dados local 'arquivista.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'arquivista.db')

# A pasta de uploads principal
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')

# Dicionário de organização de arquivos
EXTENSION_MAP = {
    'png': 'imagens/png', 'jpg': 'imagens/jpg_jpeg', 'jpeg': 'imagens/jpg_jpeg',
    'gif': 'imagens/gif', 'webp': 'imagens/webp', 'svg': 'imagens/vetoriais',
    'docx': 'documentos/word', 'doc': 'documentos/word', 'xlsx': 'documentos/excel',
    'xls': 'documentos/excel', 'pptx': 'documentos/powerpoint', 'ppt': 'documentos/powerpoint',
    'pdf': 'documentos/pdf', 'txt': 'documentos/texto', 'mp3': 'multimedia/audio',
    'wav': 'multimedia/audio', 'mp4': 'multimedia/video', 'zip': 'compactados', 'rar': 'compactados'
}
ALLOWED_EXTENSIONS = set(EXTENSION_MAP.keys())

# --- 2. Inicialização dos Sistemas de BD e Login ---
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça o login para acessar esta página."

# --- 3. Modelo de Usuário e Carregador de Sessão ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- 4. Funções Auxiliares ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_upload_path(user_id):
    """Retorna o caminho da pasta de uploads de um usuário específico."""
    return os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))

def scan_organized_files(user_id):
    """Escaneia os arquivos de um usuário específico."""
    organized_files = {}
    user_folder = get_user_upload_path(user_id)
    if not os.path.isdir(user_folder): return {}

    for root, dirs, files in os.walk(user_folder):
        if not files: continue
        category_path = os.path.relpath(root, user_folder)
        if category_path == '.': continue
        category_name = category_path.replace(os.path.sep, ' / ')
        organized_files[category_name] = [{'nome': f, 'caminho': os.path.join(category_path, f)} for f in files]
    return organized_files

# --- 5. Rotas de Autenticação ---
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
        if not username or not password:
            flash('Usuário e senha são obrigatórios.')
            return redirect(url_for('register'))
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Este nome de usuário já existe. Por favor, escolha outro.')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Conta criada com sucesso! Por favor, faça o login.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- 6. Rotas Principais (Protegidas) ---
@app.route('/')
@login_required
def index():
    arquivos = scan_organized_files(current_user.id)
    return render_template('index.html', arquivos_organizados=arquivos)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    files = request.files.getlist('arquivo')
    user_folder = get_user_upload_path(current_user.id)
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
    if successful_uploads > 0:
        flash(f'{successful_uploads} arquivo(s) organizados com sucesso!')
    else:
        flash('Nenhum arquivo válido foi enviado.')
    return redirect(url_for('index'))

# --- 7. Bloco de Execução Principal ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Cria as tabelas do banco de dados se não existirem
    app.run(host='127.0.0.1', port=5000, debug=True)