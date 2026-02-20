import time
from core.audit_logger import audit_logger
from engine.validator import validator, simulator

class Executor:
    def __init__(self):
        self.audit = audit_logger
        self.validator = validator
        self.simulator = simulator
        self.command_history = []
        self.rate_limit = {}
        self.rate_limit_window = 10
        self.max_commands_per_window = 20
    
    def execute(self, command, player_name, intent_data=None):
        if not command or not command.strip():
            return False, "Empty command"
        
        if not self._check_rate_limit(player_name):
            return False, "Rate limited. Slow down."
        
        valid, message = self.simulator.simulate(command, player_name)
        if not valid:
            self.audit.log_command(player_name, intent_data.get("original_message", ""), 
                                   intent_data.get("intent", ""), command, False)
            return False, message
        
        self.command_history.append({
            "command": command,
            "player": player_name,
            "timestamp": time.time(),
            "intent": intent_data.get("intent") if intent_data else None
        })
        self.command_history = self.command_history[-500:]
        
        self.audit.log_command(player_name, intent_data.get("original_message", "") if intent_data else "",
                               intent_data.get("intent", "") if intent_data else "",
                               command, True)
        
        return True, "Ready to execute"
    
    def _check_rate_limit(self, player_name):
        now = time.time()
        
        if player_name not in self.rate_limit:
            self.rate_limit[player_name] = []
        
        self.rate_limit[player_name] = [
            t for t in self.rate_limit[player_name]
            if now - t < self.rate_limit_window
        ]
        
        if len(self.rate_limit[player_name]) >= self.max_commands_per_window:
            return False
        
        self.rate_limit[player_name].append(now)
        return True
    
    def get_history(self, player_name=None, limit=50):
        if player_name:
            return [h for h in reversed(self.command_history) if h["player"] == player_name][:limit]
        return self.command_history[-limit:]
    
    def get_recent_commands(self, limit=10):
        return self.command_history[-limit:]


executor = Executor()
