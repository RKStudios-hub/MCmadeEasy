import time
from core.audit_logger import audit_logger
from engine.validator import validator, simulator
from engine.ml_command_engine import ml_command_engine

class Executor:
    def __init__(self):
        self.audit = audit_logger
        self.validator = validator
        self.simulator = simulator
        self.ml_engine = ml_command_engine
        self.command_history = []
        self.rate_limit = {}
        self.rate_limit_window = 10
        self.max_commands_per_window = 20
        self.last_resolved_command = None
    
    def execute(self, command, player_name, intent_data=None):
        intent_data = intent_data or {}
        self.last_resolved_command = None

        # ML-assisted command generation from intent/message/context.
        resolved_command = self.ml_engine.generate(command, intent_data, player_name)
        if not resolved_command or not str(resolved_command).strip():
            return False, "Empty command"
        
        if not self._check_rate_limit(player_name):
            return False, "Rate limited. Slow down."
        
        valid, message = self.simulator.simulate(resolved_command, player_name)
        if not valid:
            # One retry: ask ML to recover from malformed explicit command.
            retry_intent = dict(intent_data)
            retry_intent["original_message"] = intent_data.get("original_message", command or "")
            retry_command = self.ml_engine.generate(None, retry_intent, player_name)
            if retry_command and retry_command != resolved_command:
                valid2, message2 = self.simulator.simulate(retry_command, player_name)
                if valid2:
                    resolved_command = retry_command
                    valid, message = True, "Simulation passed (ml-retry)"
                else:
                    message = message2

        if not valid:
            self.audit.log_command(
                player_name,
                intent_data.get("original_message", ""),
                intent_data.get("intent", ""),
                resolved_command,
                False
            )
            self.ml_engine.learn(intent_data, resolved_command, False)
            return False, message
        
        self.command_history.append({
            "command": resolved_command,
            "player": player_name,
            "timestamp": time.time(),
            "intent": intent_data.get("intent") if intent_data else None
        })
        self.command_history = self.command_history[-500:]
        
        self.audit.log_command(player_name, intent_data.get("original_message", "") if intent_data else "",
                               intent_data.get("intent", "") if intent_data else "",
                               resolved_command, True)
        self.ml_engine.learn(intent_data, resolved_command, True)
        self.last_resolved_command = resolved_command
        
        return True, "Ready to execute"

    def get_last_resolved_command(self):
        return self.last_resolved_command
    
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
