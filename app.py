from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from AgroSapiens_RaspJet import *
import threading
import time
from flask import Flask, request
from flask import send_from_directory
from AgroSapiens_RaspJet import check_weather_forecast
import json
from pathlib import Path
from flask import Response
from datetime import datetime, timedelta
import json
from database import get_user_city
from werkzeug.utils import secure_filename
import os
import serial
DATA_FILE = Path('static/data/plantation_data.json')
HISTORY_FILE = Path('static/data/history_data.json')
API_KEY_OPENWEATHER = '4f767637cb5cac126e3ae075b0051f2a'
notification_clients = []
ser = serial.Serial('COM4', 9600, timeout=1)

def load_history_data():
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def load_history_data(user_id):
    try:
        with open(f'static/data/{user_id}_history_data.json', 'r') as f:  # Arquivo por usuário
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def load_plantation_data(user_id):
    try:
        with open(f'static/data/{user_id}_plantation_data.json', 'r') as f:  # Correção aqui
            return json.load(f)
    except:
        return {
            'young_plants': 0,
            'adult_plants': 0,
            'water_used': '0L',
            'seed_stock': '0'
        }

def save_plantation_data(user_id, data):
    Path(f'static/data/{user_id}_plantation_data.json').parent.mkdir(parents=True, exist_ok=True)
    with open(f'static/data/{user_id}_plantation_data.json', 'w') as f:
        json.dump(data, f, indent=2)





app = Flask(__name__, static_url_path='/static')
app.secret_key = 'supersecretkey'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


UPLOAD_FOLDER = 'static/uploads/profiles'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configuração do banco de dados
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Criação da tabela com todas as colunas necessárias
    c.execute('''CREATE TABLE IF NOT EXISTS users
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                city TEXT NOT NULL,
                bio TEXT,
                profile_picture TEXT,
                cultures TEXT,
                likes INTEGER DEFAULT 0)''')
    
    # Adicionar coluna cultures se não existir
    try:
        c.execute("ALTER TABLE users ADD COLUMN cultures TEXT")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()

init_db()

class User(UserMixin):
    def __init__(self, user_id):
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user_data = c.fetchone()
            conn.close()

            if not user_data:
                raise ValueError("Usuário não encontrado")

            self.id = user_id
            self.username = user_data[1]
            self.email = user_data[2]
            self.city = user_data[4] if user_data[4] and user_data[4].strip() != '' else 'São Paulo'  # Fallback
            self.bio = user_data[5] if len(user_data) > 5 else ''
            self.profile_picture = user_data[6] if len(user_data) > 6 else None
            self.cultures = user_data[7].split(',') if len(user_data) > 7 and user_data[7] else []

        except Exception as e:
            print(f"Erro ao carregar usuário: {str(e)}")
            self.id = None
            self.username = "Usuário Inválido"
            self.city = 'São Paulo'
            self.cultures = []

@login_manager.user_loader
def load_user(user_id):
    try:
        return User(user_id)
    except:
        return None  # Retorna None se o usuário não existir


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/tts/<filename>')
def serve_tts(filename):
    return send_from_directory('static/tts', filename)

@app.route('/stream')
@login_required
def stream():
    def event_stream():
        while True:
            if system_state['last_notification']:
                message = json.dumps(system_state['last_notification'])
                yield f"data: {message}\n\n"
                system_state['last_notification'] = None  # Limpa após enviar
            time.sleep(1)
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/command', methods=['POST'])
@login_required
def handle_command():
    print("Porta serial aberta?", ser.is_open)
    try:
        command = request.json.get('command')
        
        if command == 'enable_irrigation':
            print('Ligando')
            enable_irrigation(ser)
        elif command == 'disable_irrigation':
            print('Desligando')
            disable_irrigation(ser)
        elif command == 'check_soil_moisture':
            check_soil_moisture(ser)
        elif command == 'check_temperature':
            check_temperature()
        else:
            return jsonify({'status': 'error', 'message': 'Comando inválido'}), 400
            
        return jsonify({'status': 'success', 'message': system_state['last_response']})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        city = request.form['city']  # Captura a cidade
        bio = request.form.get('bio', '')

        profile_picture = None
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_picture = filename

        if password != confirm_password:
            return render_template('register.html', error='As senhas não coincidem')

        hashed_password = generate_password_hash(password)
        
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            # Inclua a cidade na query
            c.execute("INSERT INTO users (username, email, password, city, bio, profile_picture) VALUES (?, ?, ?, ?, ?, ?)",
                     (username, email, hashed_password, city, bio, profile_picture))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error='Usuário ou email já existe')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            user_obj = User(user[0])
            login_user(user_obj)
            return redirect(url_for('index'))
        
        return render_template('login.html', error='Credenciais inválidas')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/preload')
def preload():
    return render_template('preload.html')  # Criar este template simples

@app.route('/historical_data/<int:days>')
@login_required
def get_historical_data_filtered(days):
    try:
        history = load_history_data(current_user.id)  # Alterado aqui
        filtered_data = filter_history_by_days(history, days)  # Já está usando dados do usuário
        return jsonify(filtered_data[-days:])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/historical_data')
def get_historical_data():
    return get_historical_data_filtered(15) # Default para 15 dias

@app.route('/')
def intro():
    return render_template('intro.html')

@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@app.route('/update_plantation', methods=['POST'])
@login_required
def update_plantation():
    try:
        data = request.json
        current = load_plantation_data(current_user.id)
        
        # Validação e conversão segura dos dados
        conversions = {
            'young_plants': lambda x: str(int(x)),
            'adult_plants': lambda x: str(int(x)),
            'water_used': lambda x: f"{int(x.replace('L', '').strip())}L" if isinstance(x, str) else f"{int(x)}L",
            'seed_stock': lambda x: str(int(x))
        }
        
        for key, value in data.items():
            if key in conversions:
                try:
                    current[key] = conversions[key](value)
                except ValueError as ve:
                    return jsonify({
                        'status': 'error',
                        'message': f'Valor inválido para {key}: {value}'
                    }), 400
        
        save_plantation_data(current_user.id, current)
        
        
        # Atualizar histórico
        today = datetime.now().strftime("%Y-%m-%d")
        history = load_history_data(current_user.id)
        
        # Encontrar ou criar entrada para hoje
        existing_entry = next((entry for entry in history if entry['date'] == today), None)
        if existing_entry:
            existing_entry['data'] = current
        else:
            history.append({'date': today, 'data': current})
        
        # Manter apenas últimos 30 dias
        save_history_data(current_user.id, history[-30:])
        
        return jsonify({'status': 'success'})
    
    except Exception as e:
        app.logger.error(f"Erro grave: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Erro interno: {str(e)}'
        }), 500

@app.route('/status')
@login_required
def get_status():
    status = get_system_status()
    next_weathers()
    weathers_status = climate_forecast
    plantation_data = load_plantation_data(current_user.id)
    forecast_list = [
    {
        'dayNumber': weathers_status['day1'],
        'maxTemp': weathers_status['max_temp_day1'],
        'minTemp': weathers_status['min_temp_day1'],
        'weather': weathers_status['weather1'],
        'totalRain' : weathers_status['precipitation1'],
        'wind' : weathers_status['wind1'],
        'dateDay' : weathers_status['date1']
    },
    {
        'dayNumber': weathers_status['day2'],
        'maxTemp': weathers_status['max_temp_day2'],
        'minTemp': weathers_status['min_temp_day2'],
        'weather': weathers_status['weather2'],
        'totalRain' : weathers_status['precipitation2'],
        'wind' : weathers_status['wind2'],
        'dateDay' : weathers_status['date2']
        
    },
    {
        'dayNumber': weathers_status['day3'],
        'maxTemp': weathers_status['max_temp_day3'],
        'minTemp': weathers_status['min_temp_day3'],
        'weather': weathers_status['weather3'],
        'totalRain' : weathers_status['precipitation3'],
        'wind' : weathers_status['wind3'],
        'dateDay' : weathers_status['date3']
    },
    {
        'dayNumber': weathers_status['day4'],
        'maxTemp': weathers_status['max_temp_day4'],
        'minTemp': weathers_status['min_temp_day4'],
        'weather': weathers_status['weather4'],
        'totalRain' : weathers_status['precipitation4'],
        'wind' : weathers_status['wind4'],
        'dateDay' : weathers_status['date4']
    },
    {
        'dayNumber': weathers_status['day5'],
        'maxTemp': weathers_status['max_temp_day5'],
        'minTemp': weathers_status['min_temp_day5'],
        'weather': weathers_status['weather5'],
        'totalRain' : weathers_status['precipitation4'],
        'wind' : weathers_status['wind5'],
        'dateDay' : weathers_status['date5']
    }
    
]

    return jsonify({
        'irrigation': status['irrigation'],
        'auto_mode': status['auto_mode'],
        'soil_moisture': status['soil_moisture'],
        'temperature': status['temperature'],
        'weather': status['weather'],
        'humidity': status['humidity'],
        'wind': status['wind'],
        'clouds': status['clouds'],
        'pressure': status['pressure'],
        'sunrise': status['sunrise'],
        'sundown': status['sundown'],
        'forecast' : forecast_list,
        **plantation_data
    })


@app.route('/chat', methods=['POST'])
def handle_chat():
    try:
        data = request.json
        print(f"Recebido: {data['message']}")  # Log de depuração
        
        response = handle_gpt_query(data['message'], data.get('history', []))
        print(f"Resposta gerada: {response}")  # Log de depuração
        
        audio_filename = text_to_speech(response)
        return jsonify({
            'response': response,
            'audio': audio_filename
        })
        
    except Exception as e:
        print(f"Erro grave: {str(e)}")  # Log de erro
        return jsonify({'response': f"Erro: {str(e)}"})
    

@app.route('/voice', methods=['POST'])
def handle_voice():
    try:
        input_text = handle_voice_input()
        return jsonify({'text': input_text})
    except Exception as e:
        return jsonify({'error': str(e)})

def status_updater():
    while True:
        try:
            check_temperature()
            check_soil_moisture(ser)
            
            notifications = check_environment_changes()
            if notifications:
                system_state['last_notification'] = {
                    'timestamp': datetime.now().isoformat(),
                    'messages': notifications
                }
            
            threading.Event().wait(5)
        except Exception as e:
            print(f"Erro no status updater: {str(e)}")

@app.route('/forecast')
@login_required
def forecast():
    check_temperature
    return render_template('forecast.html', forecast=system_state['weather'])

@app.route('/weather/coordinates')
@login_required
def get_coordinates():
    try:
        # Validação robusta da cidade
        if not hasattr(current_user, 'city') or not current_user.city.strip():
            app.logger.error("Cidade não configurada para o usuário %s", current_user.id)
            return jsonify(error="Por favor, configure sua cidade no perfil"), 400
        
        # Codificação correta da cidade
        city = requests.utils.quote(current_user.city)
        
        # Chamada à API de geolocalização
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city},,BR&limit=1&appid={API_KEY_OPENWEATHER}"
        response = requests.get(geo_url)
        
        if response.status_code != 200:
            app.logger.error("Erro na API Geo: %s - %s", response.status_code, response.text)
            return jsonify(error="Serviço de localização indisponível"), 500
            
        data = response.json()
        if not data:
            app.logger.error("Cidade não encontrada: %s", current_user.city)
            return jsonify(error=f"Cidade '{current_user.city}' não encontrada"), 404
            
        return jsonify({
            "lat": data[0]["lat"],
            "lon": data[0]["lon"],
            "city": current_user.city
        })
        
    except Exception as e:
        app.logger.exception("Erro crítico em get_coordinates:")
        return jsonify(error="Erro interno no servidor"), 500

@app.route('/radio/')
def radio():
    return render_template('radio.html')

@app.route('/notifications')
@login_required
def get_notifications():
    return jsonify(system_state.get('last_notification', {}))





def filter_history_by_days(data, days):
    today = datetime.now().date()
    filtered = []
    for entry in data:
        try:
            entry_date = datetime.strptime(entry['date'], "%Y-%m-%d").date()
            if (today - entry_date).days <= days:
                filtered.append(entry)
        except:
            continue
    return sorted(filtered, key=lambda x: x['date'])


def clean_old_tts_files():
    while True:
        now = time.time()
        for filename in os.listdir("static/tts"):
            filepath = os.path.join("static/tts", filename)
            # Apaga arquivos com mais de 1 hora
            if os.stat(filepath).st_mtime < now - 600:
                try:
                    os.remove(filepath)
                except:
                    pass
        time.sleep(600)

def save_history_data(user_id, data):
    history_file = Path(f'static/data/{user_id}_history_data.json')  # Arquivo por usuário
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with open(history_file, 'w') as f:
        json.dump(data, f, indent=2)

def get_user_city(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT city FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 'Canindé de São Francisco'  # Fallback

@app.route('/status')
def status():
    return "OK", 200

# Inicialização dos dados ambientais
check_temperature()
check_soil_moisture(ser)

@app.route('/get_user_city')
@login_required
def get_user_city_route():
    try:
        return jsonify(current_user.city)
    except:
        return jsonify('Canindé de São Francisco')

@app.route('/like/<int:user_id>', methods=['POST'])
@login_required
def like_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET likes = likes + 1 WHERE id = ?", (user_id,))
    conn.commit()

    return jsonify(success=True)

@app.route('/search')
@login_required
def search():
    search_query = request.args.get('q')
    filter_city = request.args.get('city')
    filter_culture = request.args.get('culture')
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Buscar cidades disponíveis para o filtro
    c.execute("SELECT DISTINCT city FROM users")
    cities = [row[0] for row in c.fetchall()]
    
    # Construir query de busca
    query = "SELECT * FROM users WHERE 1=1"
    params = []
    
    

    if search_query:
        query += " AND username LIKE ?"
        params.append(f'%{search_query}%')
    
    if filter_city:
        query += " AND city = ?"
        params.append(filter_city)
    
    if filter_culture:
        query += " AND cultures LIKE ?"
        params.append(f'%{filter_culture}%')
    
    query += " ORDER BY likes DESC"
    
    c.execute(query, params)
    users = c.fetchall()
    conn.close()
    c.execute("SELECT * FROM users ORDER BY likes DESC LIMIT 10")
    top_users = list(enumerate(c.fetchall(), 1))
    return render_template('search.html',
                         users=users,
                         top_users=top_users,
                         cities=cities,
                         current_filters={
                             'q': search_query,
                             'city': filter_city,
                             'culture': filter_culture
                         })

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("PRAGMA table_info(users)")  # Verificar colunas existentes
        columns = [col[1] for col in c.fetchall()]

        if request.method == 'POST':
            city = request.form.get('city', '')
            if not city:
                # Retorne erro ao usuário
                return render_template('profile.html', 
                    error="A cidade é obrigatória para o sistema climático",
                    username=user_data[1],
                    )

        if 'cultures' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN cultures TEXT")
            conn.commit()

        if request.method == 'POST':
            # Processar atualizações
            bio = request.form.get('bio', '')
            city = request.form.get('city', '')
            cultures = request.form.get('cultures', '')
        
            # Processar nova imagem
            new_profile_pic = None
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    new_profile_pic = filename
        
            # Atualizar banco de dados
            update_fields = []
            params = []
        
            if bio != current_user.bio:
                update_fields.append("bio = ?")
                params.append(bio)
            if city != current_user.city:
                update_fields.append("city = ?")
                params.append(city)
            if cultures:
                update_fields.append("cultures = ?")
                params.append(cultures)
            if new_profile_pic:
                update_fields.append("profile_picture = ?")
                params.append(new_profile_pic)

            if update_fields:
                query = "UPDATE users SET " + ", ".join(update_fields) + " WHERE id = ?"
                params.append(current_user.id)
                c.execute(query, params)
                conn.commit()
        
                conn.close()
                return redirect(url_for('profile'))

    # Carregar dados do usuário
        c.execute("SELECT * FROM users WHERE id = ?", (current_user.id,))
        user_data = c.fetchone()
        
        # Mapeamento seguro dos dados
        cultures = user_data[7].split(',') if len(user_data) > 7 and user_data[7] else []
        
        conn.close()
        
        return render_template('profile.html', 
                            username=user_data[1],
                            city=user_data[4],
                            bio=user_data[5] if len(user_data) > 5 else '',
                            profile_pic=user_data[6] if len(user_data) > 6 else None,
                            cultures=cultures)
    except Exception as e:
        print(f"Erro no perfil: {str(e)}")
        return render_template('error.html', message="Erro ao carregar perfil"), 500

if __name__ == '__main__':
    threading.Thread(target=status_updater, daemon=True).start()
    threading.Thread(target=clean_old_tts_files, daemon=True).start()
    app.run(host='0.0.0.0', port=7070, debug=False)
