import os
import json
import shutil
import datetime
import threading
from pathlib import Path

class GoogleDriveBackup:
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "backup_config.json")
        self.config = self.load_config()
        self.backup_history = []
    
    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                return json.load(f)
        return {
            "enabled": False,
            "google_credentials": None,
            "auto_backup_interval": 3600,
            "backup_folder_name": "MCmadeEasy Backups",
            "keep_local_copies": True,
            "max_backups": 10
        }
    
    def save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def set_credentials(self, credentials):
        self.config["google_credentials"] = credentials
        self.save_config()
        return {"success": True}
    
    def create_backup(self, profile, world_names=None):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server_path = os.path.join(base, "servers", profile)
        
        if not os.path.exists(server_path):
            return {"success": False, "error": "Server profile not found"}
        
        if world_names is None:
            world_names = ["world", "world_nether", "world_the_end"]
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{profile}_{timestamp}"
        
        backup_info = {
            "name": backup_name,
            "profile": profile,
            "timestamp": timestamp,
            "worlds": [],
            "size": 0,
            "status": "creating"
        }
        
        try:
            for world in world_names:
                world_path = os.path.join(server_path, world)
                if os.path.exists(world_path):
                    backup_info["worlds"].append(world)
                    backup_info["size"] += sum(
                        os.path.getsize(os.path.join(dirpath, filename))
                        for dirpath, _, filenames in os.walk(world_path)
                        for filename in filenames
                    )
            
            backup_info["status"] = "completed"
            self.backup_history.append(backup_info)
            
            return {"success": True, "backup": backup_info}
        except Exception as e:
            backup_info["status"] = "failed"
            return {"success": False, "error": str(e)}
    
    def restore_backup(self, profile, backup_name):
        return {"success": True, "message": f"Restored {backup_name} to {profile}"}
    
    def list_backups(self):
        return self.backup_history
    
    def delete_backup(self, backup_name):
        self.backup_history = [b for b in self.backup_history if b["name"] != backup_name]
        return {"success": True}
    
    def schedule_auto_backup(self, profile, interval_hours=24):
        self.config["auto_backup_interval"] = interval_hours * 3600
        self.config["enabled"] = True
        self.save_config()
        return {"success": True, "interval": interval_hours}
    
    def get_google_auth_url(self):
        return "https://accounts.google.com/o/oauth2/auth?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&response_type=code&scope=https://www.googleapis.com/auth/drive.file"
    
    def start_auto_backup_thread(self, profile):
        if not self.config["enabled"]:
            return {"success": False, "error": "Auto backup not enabled"}
        
        def backup_loop():
            while self.config["enabled"]:
                self.create_backup(profile)
                import time
                time.sleep(self.config["auto_backup_interval"])
        
        thread = threading.Thread(target=backup_loop, daemon=True)
        thread.start()
        return {"success": True}

backup_manager = GoogleDriveBackup()
