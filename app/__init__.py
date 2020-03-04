import os

from flask import Flask
from flask_pymodm import PyModm
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix

def get_app_folder():
    return os.path.dirname(__file__)


def get_runtime_folder():
    return os.path.join(get_app_folder(), 'runtime_folder')


def init_project(static_folder, *args):
    runtime_folder = get_runtime_folder()
    if not os.path.exists(runtime_folder):
        os.mkdir(runtime_folder)

    app = Flask(__name__, static_folder=static_folder)
    for file in args:
        app.config.from_pyfile(file, silent=False)

    app.wsgi_app = ProxyFix(app.wsgi_app)
    bootstrap = Bootstrap(app)
    db = PyModm(app)
    mail = Mail(app)
    socketio = SocketIO(app)
    login_manager = LoginManager(app)

    login_manager.login_view = "HomeView:signin"

    # socketio
    @socketio.on('connect')
    def connect():
        pass

    @socketio.on('disconnect')
    def disconnect():
        pass

    return app, bootstrap, db, mail, login_manager


app, bootstrap, db, mail, login_manager = init_project(
    'static',
    'config/public_config.py',
    'config/config.py',
    'config/db_config.py',
    'config/mail_config.py'
)

from app.home.view import HomeView
from app.subscriber.view import SubscriberView

HomeView.register(app)
SubscriberView.register(app)
