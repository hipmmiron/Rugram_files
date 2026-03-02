import subprocess
import time
import os
import re
import sys
import random

# --- НАСТРОЙКИ ---
MY_IP = "192.168.1.95" # Твой локальный IP
PORT = "5555"          # Порт Flask
# -----------------

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
token_file_path = os.path.join(current_dir, "TOKEN")

# Читаем токен
try:
    with open(token_file_path, "r", encoding="utf-8") as f:
        GITHUB_TOKEN = f.read().strip()
except:
    print("[!] TOKEN не найден!"); sys.exit(1)

def update_vercel_beacon(url):
    """Обновляет только index.html, игнорируя остальное"""
    print(f"[*] Синхронизация с Vercel...")
    index_path = os.path.join(root_dir, "index.html")
    ts = int(time.time())
    
    # Маяк с жестким запретом кэша
    content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <script>window.location.replace("{url}?v={ts}");</script>
</head>
<body style="background:#000;color:#0f0;display:flex;justify-content:center;align-items:center;height:100vh;font-family:monospace;">
    <div style="text-align:center;border:1px solid #0f0;padding:20px;">
        <h2>RUGRAM SYSTEM ONLINE</h2>
        <p>Redirecting to tunnel... [{ts}]</p>
    </div>
</body>
</html>'''
    
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    try:
        os.chdir(root_dir)
        remote_url = f"https://{GITHUB_TOKEN}@github.com/hipmmiron/rugram.git"
        
        # Чистим индекс, чтобы не пушить лишние папки (code, UI и т.д.)
        os.system('git rm -r --cached . >nul 2>&1')
        os.system('git add index.html')
        # Создаем пустой .gitignore чтобы Vercel не пытался билдить твой Python
        with open(".gitignore", "w") as g: g.write("code/\nstart/\nUI/\nstatic/\nTOKEN\n*.db\n")
        os.system('git add .gitignore')
        
        os.system(f'git commit -m "Vercel Deploy {ts}"')
        os.system(f'git push {remote_url} main --force')
        print(f"[OK] Готово. Ссылка обновится через пару секунд.")
    except Exception as e:
        print(f"[!] Ошибка Git: {e}")

def run():
    os.system('cls && title Rugram Vercel Engine')
    os.system('taskkill /f /im ssh.exe >nul 2>&1')
    
    # 1. Запуск Flask
    server_script = os.path.join(root_dir, 'code', 'app.py')
    print("[1/3] Запуск сервера...")
    server = subprocess.Popen([sys.executable, server_script], cwd=os.path.join(root_dir, 'code'))
    time.sleep(5)

    # 2. Запуск Туннеля
    print(f"[2/3] Открытие туннеля через {MY_IP}...")
    ssh_cmd = f'ssh -o StrictHostKeyChecking=no -R 80:{MY_IP}:{PORT} nokey@localhost.run'
    tunnel = subprocess.Popen(ssh_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')

    # 3. Поиск ссылки
    url = ""
    for _ in range(40):
        line = tunnel.stdout.readline()
        if "lhr.life" in line:
            match = re.search(r"https://[a-zA-Z0-9.-]+\.lhr\.life", line)
            if match:
                url = match.group(0)
                break
    
    if url:
        print(f"[3/3] Ссылка получена: {url}")
        os.system(f'echo {url} | clip')
        update_vercel_beacon(url)
        print("\n--- СИСТЕМА ГОТОВА ---")
        print("Используй свою ссылку .vercel.app")
    else:
        print("[!] Не удалось поймать ссылку.")
    
    print("\nНажми ENTER для завершения...")
    input()
    server.terminate()
    os.system('taskkill /f /im ssh.exe >nul 2>&1')

if __name__ == "__main__":
    run()