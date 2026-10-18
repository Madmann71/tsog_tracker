#!/usr/bin/env python3
"""
Локальный сервер синхронизации мастерской ТСОГ.
Работает на чистом Python 3 без сторонних библиотек (zero-dependency).
Обеспечивает одновременную работу и автоматическую синхронизацию между всеми устройствами в Wi-Fi сети.
"""

import http.server
import socketserver
import json
import os
import socket
import threading
import time
from datetime import datetime

PORT = 8080
DB_FILE = 'database.json'
HTML_FILE = 'index.html'

lock = threading.Lock()
revision = 1
last_updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
last_updated_by = 'Система'
cached_data = None

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return '127.0.0.1'

def init_db():
    global revision, last_updated_at, last_updated_by, cached_data
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                revision = data.get('version', 1)
                last_updated_at = data.get('updatedAt', last_updated_at)
                last_updated_by = data.get('updatedBy', 'Система')
                cached_data = data
                print(f"[БД] Загружена существующая база: {len(data.get('items', []))} позиций, ревизия v{revision}")
                return
        except Exception as e:
            print(f"[Внимание] Ошибка чтения {DB_FILE}, создаем начальную базу: {e}")

    cached_data = {
        'version': 1,
        'updatedAt': last_updated_at,
        'updatedBy': 'Инициализация',
        'items': [],
        'logs': [],
        'editorsList': [
            {'name': 'Николай (Ст. мастер)', 'pin': '1111'},
            {'name': 'Инженер ТСОГ', 'pin': '2222'},
            {'name': 'Мастер ВОЛС', 'pin': '3333'},
            {'name': 'Начальник мастерской', 'pin': '4444'}
        ]
    }
    save_db_file(cached_data)

def save_db_file(data):
    temp_file = DB_FILE + '.tmp'
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_file, DB_FILE)

class SyncHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Включаем CORS для всех запросов
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Master-Name')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        global revision, last_updated_at, last_updated_by, cached_data

        if self.path == '/api/version':
            with lock:
                res = {
                    'version': revision,
                    'updatedAt': last_updated_at,
                    'updatedBy': last_updated_by,
                    'itemsCount': len(cached_data.get('items', [])) if cached_data else 0
                }
            payload = json.dumps(res, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if self.path == '/api/data':
            with lock:
                payload = json.dumps(cached_data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        # Перенаправление корня на index.html
        if self.path in ('/', '/index.html'):
            if os.path.exists(HTML_FILE):
                self.path = '/' + HTML_FILE
            elif os.path.exists('tsog_workshop_tracker.html'):
                self.path = '/tsog_workshop_tracker.html'

        return super().do_GET()

    def do_POST(self):
        global revision, last_updated_at, last_updated_by, cached_data

        if self.path == '/api/data':
            try:
                content_len = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_len).decode('utf-8')
                new_data = json.loads(body)

                with lock:
                    revision += 1
                    last_updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
                    last_updated_by = new_data.get('updatedBy', 'Мастер')

                    new_data['version'] = revision
                    new_data['updatedAt'] = last_updated_at
                    cached_data = new_data
                    save_db_file(new_data)

                print(f"[СИНХРОН v{revision}] Изменения от «{last_updated_by}» сохранены ({len(new_data.get('items', []))} позиций). Рассылка на устройства...")
                
                resp = json.dumps({
                    'status': 'ok',
                    'version': revision,
                    'updatedAt': last_updated_at
                }).encode('utf-8')

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                self.send_response(500)
                err_resp = json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8')
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(err_resp)))
                self.end_headers()
                self.wfile.write(err_resp)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        # Не спамим в консоль частыми опросами /api/version
        if '/api/version' in args[0]:
            return
        super().log_message(format, *args)

def run_server():
    init_db()
    local_ip = get_local_ip()
    server_address = ('', PORT)
    
    # Разрешаем повторное использование сокета
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(server_address, SyncHandler) as httpd:
        print("=" * 70)
        print(" СЕРВЕР МАСТЕРСКОЙ ТСОГ ЗАПУЩЕН И ГОТОВ К РАБОТЕ")
        print("=" * 70)
        print(f" 1. На этом ПК в браузере:      http://localhost:{PORT}")
        print(f" 2. На смартфонах Android (Wi-Fi): http://{local_ip}:{PORT}")
        print("-" * 70)
        print(f" * База данных хранится в:      {os.path.abspath(DB_FILE)}")
        print(" * Автосинхронизация активна:   изменения подтягиваются мгновенно")
        print(" * Для завершения работы нажмите Ctrl + C")
        print("=" * 70)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nСервер остановлен.")

if __name__ == '__main__':
    run_server()
