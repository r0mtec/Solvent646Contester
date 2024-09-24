import sys
import os
import subprocess
import time
import psutil
import logging
import threading
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Настройка логирования
LOG_FILE = "application.log"
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = './code_submissions'
TEST_FOLDER = './test_cases'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEST_FOLDER'] = TEST_FOLDER

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///contest.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Модель пользователя
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    submissions = db.relationship('Submission', backref='author', lazy=True)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Модель для отправленных решений
class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), nullable=False)
    test_result = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Загрузка пользователя из сессии
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))



# Тайм-аут и лимиты
TIMEOUT = 2
MEMORY_LIMIT_MB = 256

progress_status = {}


def get_available_tests():
    """Получаем список файлов тестов из папки test_cases"""
    try:
        test_files = [f for f in os.listdir(TEST_FOLDER) if os.path.isfile(os.path.join(TEST_FOLDER, f))]
        return test_files
    except Exception as e:
        logging.error(f"Ошибка при получении тестов: {str(e)}")
        return []


def run_tests_in_background(task_id, language, code_file, test_cases):
    """Функция для выполнения тестов в фоновом режиме"""
    run_tests(language, code_file, test_cases, task_id)

def run_code(language, file_path, test_input):
    """Функция для выполнения кода пользователя с поддержкой разных языков"""
    start_time = time.time()
    compilation_time = 0

    try:
        if language == "python":
            logging.info(f"Запуск Python программы: {file_path}")
            command = [sys.executable, file_path]
        elif language == "cpp":
            # Компиляция C++
            executable = file_path.replace('.cpp', '.exe')  # На Windows нужен файл .exe
            compile_command = ['g++', file_path, '-o', executable]

            logging.info(f"Компиляция C++: {compile_command}")
            compile_start = time.time()
            compile_process = subprocess.run(compile_command, capture_output=True)
            compilation_time = time.time() - compile_start

            if compile_process.returncode != 0:
                logging.error(f"Ошибка компиляции C++: {compile_process.stderr.decode()}")
                raise Exception(f"Ошибка компиляции C++: {compile_process.stderr.decode()}")

            if not os.path.exists(executable):
                logging.error(f"Не удается найти скомпилированный файл: {executable}")
                raise Exception(f"Не удается найти скомпилированный файл: {executable}")

            logging.info(f"Запуск C++ программы: {executable}")
            command = [executable]
        elif language == "java":
            # Компиляция Java
            compile_command = ['javac', file_path]
            logging.info(f"Компиляция Java: {compile_command}")
            compile_process = subprocess.run(compile_command, capture_output=True)

            if compile_process.returncode != 0:
                logging.error(f"Ошибка компиляции Java: {compile_process.stderr.decode()}")
                raise Exception(f"Ошибка компиляции Java: {compile_process.stderr.decode()}")

            class_name = os.path.basename(file_path).replace('.java', '')
            command = ['java', class_name]
            logging.info(f"Запуск Java программы: {class_name}")
        else:
            logging.error(f"Язык {language} не поддерживается.")
            raise Exception(f"Язык {language} не поддерживается.")

        # Запуск программы с ограничением по времени
        logging.info(f"Запуск команды: {command}")
        program_start = time.time()
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        output, error = process.communicate(input=test_input.encode(), timeout=TIMEOUT)
        program_execution_time = time.time() - program_start
        exit_code = process.returncode

        if exit_code != 0:
            logging.error(f"Ошибка выполнения программы. Код выхода: {exit_code}, Ошибка: {error.decode()}")
            raise Exception(f"Process finished with exit code {exit_code}: {error.decode()}")

        logging.info(f"Вывод программы: {output.decode()}")

        try:
            process_info = psutil.Process(process.pid)
            memory_usage = process_info.memory_info().rss / 1024 / 1024  # MB
        except psutil.NoSuchProcess:
            memory_usage = 0

        elapsed_time = time.time() - start_time

        return {
            "output": output.decode(),
            "error": error.decode(),
            "time": program_execution_time,
            "compilation_time": compilation_time,
            "memory": memory_usage,
            "exit_code": exit_code
        }

    except subprocess.TimeoutExpired:
        process.kill()
        logging.error("Программа превысила лимит по времени.")
        return {
            "output": "",
            "error": "Timeout expired",
            "time": TIMEOUT,
            "memory": MEMORY_LIMIT_MB,
            "exit_code": -1
        }

    except Exception as e:
        logging.error(f"Ошибка: {str(e)}")
        return {
            "output": "",
            "error": str(e),
            "time": 0,
            "memory": 0,
            "exit_code": -1
        }


def compare_output(user_output, expected_output):
    """Сравнение вывода программы с ожидаемым результатом"""
    return user_output.strip() == expected_output.strip()


def run_tests(language, code_file, test_cases, task_id):
    """Функция для запуска всех тестов"""
    global progress_status
    results = []

    total_tests = len(test_cases)
    for i, (test_input, expected_output) in enumerate(test_cases):
        result = run_code(language, code_file, test_input)
        logging.info(f"Тест #{i + 1}: Ожидалось {expected_output}, Получено {result['output']}")

        if result["exit_code"] != 0:
            result_status = "Runtime Error"
        elif compare_output(result["output"], expected_output):
            result_status = "Passed"
        else:
            result_status = "Failed"

        results.append({
            "test": i + 1,
            "status": result_status,
            "output": result["output"],
            "expected": expected_output,
            "time": result["time"],
            "compilation_time": result.get("compilation_time", 0),
            "memory": result["memory"],
            "error": result["error"]
        })

        # Обновление прогресса
        progress_status[task_id] = results

    # Проверяем, прошли ли все тесты
    all_tests_passed = all(result['status'] == 'Passed' for result in results)

    return results, all_tests_passed



@app.route('/')
def index():
    test_files = get_available_tests()  # Получаем доступные тесты
    return render_template('index.html', test_files=test_files)


@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    global progress_status

    if 'code_file' not in request.files or 'test_file' not in request.form:
        flash('Необходимо загрузить код и выбрать задачу.')
        return redirect(request.url)

    code_file = request.files['code_file']
    test_file = request.form.get('test_file')
    language = request.form.get('language')

    if code_file.filename == '' or not test_file or not language:
        flash('Оба файла и выбор языка должны быть выбраны для загрузки.')
        return redirect(request.url)

    # Сохранение файлов
    code_path = os.path.join(app.config['UPLOAD_FOLDER'], code_file.filename)
    code_file.save(code_path)

    test_path = os.path.join(app.config['TEST_FOLDER'], test_file)

    # Генерация уникального ID для задания
    task_id = str(int(time.time()))

    # Инициализация состояния прогресса
    total_tests = 1
    progress_status[task_id] = {'current': 0, 'total': total_tests, 'progress': 0}

    # Загрузка тестов из файла
    test_cases = []
    with open(test_path, 'r') as f:
        for line in f:
            parts = line.strip().split(' ')
            input_data = ' '.join(parts[:-1])
            expected_output = parts[-1]
            test_cases.append((input_data, expected_output))

    # Запуск тестов в фоновом потоке
    test_thread = threading.Thread(target=run_tests_in_background, args=(task_id, language, code_path, test_cases))
    test_thread.start()

    # Переход на страницу с прогрессом
    return redirect(url_for('task_status', task_id=task_id))


@app.route('/profile')
@login_required
def profile():
    submissions = Submission.query.filter_by(author=current_user).all()
    return render_template('profile.html', submissions=submissions)


@app.route('/status/<task_id>')
def task_status(task_id):
    """Страница с прогрессом выполнения"""
    return render_template('progress.html', task_id=task_id)


@app.route('/progress/<task_id>')
def get_progress(task_id):
    """Получаем прогресс выполнения тестов"""
    progress_data = progress_status.get(task_id, {})

    # Логируем, что сервер отправляет на клиент
    logging.info(f"Прогресс для задачи {task_id}: {progress_data}")

    return jsonify(progress_data)


@app.route('/results/<task_id>')
def results(task_id):
    # Извлекаем результаты из глобального progress_status, которые были сохранены после выполнения тестов
    task_result = progress_status.get(task_id, {})
    if not task_result:
        flash('Результаты тестов не найдены!')
        return redirect(url_for('index'))

    return render_template('results.html', results=task_result)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создаем все таблицы
    app.run(debug=True)

