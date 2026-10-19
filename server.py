"""Single-process server: one scheduler and a threaded WSGI server."""
import os
import threading
from waitress import serve
from app import app, scheduler

if __name__ == '__main__':
    threading.Thread(target=scheduler, daemon=True, name='daily-agent').start()
    serve(app, host=os.environ.get('HOST','127.0.0.1'), port=int(os.environ.get('PORT','5000')), threads=4)
