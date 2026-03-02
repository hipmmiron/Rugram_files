import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash

# --- ПРАВИЛЬНАЯ НАСТРОЙКА ПУТЕЙ ---
# Находим папку, где лежит этот файл (app.py)
base_dir = os.path.dirname(os.path.abspath(__file__))
# База будет лежать здесь же
db_path = os.path.join(base_dir, "messages.db")
# Папки UI и static лежат уровнем выше
ui_folder = os.path.abspath(os.path.join(base_dir, '..', 'UI'))
static_folder = os.path.abspath(os.path.join(base_dir, '..', 'static'))

app = Flask(__name__, template_folder=ui_folder, static_folder=static_folder)
app.config['SECRET_KEY'] = 'rugram_secret_key_1337'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# SocketIO с поддержкой туннелей
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- МОДЕЛИ ДАННЫХ ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(200), default='')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())

# Создаем базу, если её нет
with app.app_context():
    db.create_all()

# --- МАРШРУТЫ (ROUTES) ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'], avatar=session.get('avatar', ''))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['avatar'] = user.avatar
            return redirect(url_for('index'))
        
        flash('Неверный логин или пароль')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Заполни все поля!')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Этот ник уже занят, выбери другой')
            return redirect(url_for('register'))
        
        try:
            hashed_pw = generate_password_hash(password)
            new_user = User(username=username, password=hashed_pw)
            db.session.add(new_user)
            db.session.commit()
            print(f"[DB] Зарегистрирован новый юзер: {username}")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"[ERR] Ошибка БД: {e}")
            flash('Ошибка при регистрации')
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/search_users')
def search_users():
    if 'user_id' not in session: return {"users": []}
    query = request.args.get('q', '')
    users = User.query.filter(User.username.contains(query)).limit(10).all()
    return {"users": [{"id": u.id, "username": u.username, "avatar": u.avatar} for u in users if u.id != session.get('user_id')]}

# --- SOCKET.IO ЛОГИКА ---

@socketio.on('connect')
def on_connect():
    if 'user_id' in session:
        join_room(f"user_{session['user_id']}")
        print(f"[Socket] {session['username']} вошел в сеть")

@socketio.on('send_message')
def handle_send_message(data):
    sender_id = session.get('user_id')
    recipient_id = data.get('to_id')
    text = data.get('message')

    if sender_id and recipient_id and text:
        msg = Message(sender_id=sender_id, recipient_id=recipient_id, text=text)
        db.session.add(msg)
        db.session.commit()

        payload = {
            'message': text,
            'from_id': sender_id,
            'from_username': session['username']
        }
        emit('receive_message', payload, room=f"user_{recipient_id}")
        emit('receive_message', payload, room=f"user_{sender_id}")

if __name__ == '__main__':
    # 0.0.0.0 и 5555 — золотой стандарт для твоего туннеля
    socketio.run(app, host='0.0.0.0', port=5555, allow_unsafe_werkzeug=True)