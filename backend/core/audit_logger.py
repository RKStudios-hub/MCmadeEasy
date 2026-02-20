import json
import os
import time
from datetime import datetime

class AuditLogger:
    def __init__(self, log_dir=None):
        self.log_dir = log_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.current_log_file = os.path.join(self.log_dir, f"audit_{datetime.now().strftime('%Y%m%d')}.json")
        self.logs = []
        self.load_today_logs()
    
    def load_today_logs(self):
        if os.path.exists(self.current_log_file):
            try:
                with open(self.current_log_file, "r") as f:
                    self.logs = json.load(f)
            except:
                self.logs = []
    
    def save_logs(self):
        with open(self.current_log_file, "w") as f:
            json.dump(self.logs, f, indent=2)
    
    def log(self, event_type, player, message, intent=None, command=None, success=True, metadata=None):
        entry = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "type": event_type,
            "player": player,
            "message": message,
            "intent": intent,
            "command": command,
            "success": success,
            "metadata": metadata or {}
        }
        self.logs.append(entry)
        self.logs = self.logs[-1000:]
        self.save_logs()
        return entry
    
    def log_command(self, player, message, intent, command, success=True):
        return self.log("command", player, message, intent, command, success)
    
    def log_chat(self, player, message, response):
        return self.log("chat", player, message, None, None, True, {"response": response[:100]})
    
    def log_event(self, event_type, metadata):
        return self.log("event", "system", event_type, None, None, True, metadata)
    
    def get_player_logs(self, player_name, limit=50):
        return [l for l in reversed(self.logs) if l.get("player") == player_name][-limit:]
    
    def get_recent(self, limit=20):
        return self.logs[-limit:]
    
    def search(self, query, limit=50):
        results = []
        for log in reversed(self.logs):
            if query.lower() in str(log).lower():
                results.append(log)
            if len(results) >= limit:
                break
        return results


audit_logger = AuditLogger()
