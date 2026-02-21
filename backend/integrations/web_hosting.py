import os
import json
import socket
import threading
import http.server
import socketserver
from pathlib import Path

class WebHostingManager:
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "hosting_config.json")
        self.config = self.load_config()
        self.server = None
        self.server_thread = None
        self.is_running = False
    
    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                return json.load(f)
        return {
            "enabled": False,
            "port": 8000,
            "public_access": False,
            "custom_domain": None,
            "ssl_enabled": False,
            "password_protected": False,
            "password": None,
            "allowed_ips": [],
            "serve_dynmap": True,
            "serve_dashboard": True
        }
    
    def save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def start_server(self, port=None):
        if port is None:
            port = self.config["port"]
        
        if self.is_running:
            return {"success": False, "error": "Server already running"}
        
        try:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            frontend_path = os.path.join(base, "frontend")
            
            class Handler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=frontend_path, **kwargs)
                
                def log_message(self, format, *args):
                    print(f"[WebHost] {self.address_string()} - {format % args}")
            
            self.server = socketserver.TCPServer(("", port), Handler)
            self.is_running = True
            
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            local_ip = self.get_local_ip()
            
            return {
                "success": True,
                "local_url": f"http://localhost:{port}",
                "network_url": f"http://{local_ip}:{port}",
                "port": port
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def stop_server(self):
        if not self.is_running:
            return {"success": False, "error": "Server not running"}
        
        try:
            self.server.shutdown()
            self.is_running = False
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_status(self):
        return {
            "running": self.is_running,
            "port": self.config["port"],
            "local_url": f"http://localhost:{self.config['port']}" if self.is_running else None,
            "network_url": f"http://{self.get_local_ip()}:{self.config['port']}" if self.is_running else None,
            "public_access": self.config["public_access"]
        }
    
    def update_config(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
        self.save_config()
        return {"success": True, "config": self.config}
    
    def check_port_available(self, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("", port))
            s.close()
            return True
        except:
            return False
    
    def get_available_port(self, start=8000, end=9000):
        for port in range(start, end):
            if self.check_port_available(port):
                return port
        return None

hosting_manager = WebHostingManager()
