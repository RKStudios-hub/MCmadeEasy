import re
from engine.command_catalog import command_catalog

DANGEROUS_PATTERNS = [
    r';', r'&&', r'\|\|', r'\n',
    r'op\s+', r'deop\s+',
    r'sudo\s+', r'execute\s+as\s+',
    r'tellraw\s+@a', r'broadcast\s+',
    r'whitelist\s+off',
    r'plugman\s+', r'multiverse\s+',
    r'worldedit\s+', r'we\s+',
    r'\$', r'`', r'\(.*\)',
]

BLACKLIST = [
    'stop', 'restart', 'reload',
    'op ', 'deop ', 'whitelist off',
    'execute as', 'sudo ',
    'console ', 'CONSOLE ',
]

MINECRAFT_COMMANDS = [
    'time', 'weather', 'give', 'summon', 'tp', 'teleport',
    'gamemode', 'heal', 'effect', 'enchant', 'xp', 'kill',
    'save', 'fly', 'feed', 'ability', 'say', 'tell', 'msg',
    'me', 'team', 'scoreboard', 'data', 'particle', 'playsound',
    'title', 'trigger', 'function', 'recipe', 'locate',
    'spreadplayers', 'setworldspawn', 'spawnpoint', 'clear',
    'containter', 'experience', 'gamerule', 'setidletimeout',
    'kick', 'ban', 'pardon', 'mute', 'tempban', 'warn',
    'whitelist', 'list', 'help', 'plugins', 'version',
]


class Validator:
    def __init__(self):
        self.dangerous_patterns = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]
        self.blacklist = BLACKLIST
        self.allowed_commands = MINECRAFT_COMMANDS
    
    def validate(self, command):
        command_lower = command.lower().strip()
        
        if not command_lower:
            return False, "Empty command"

        # Internal command tokens used by the AI pipeline.
        if command_lower.startswith("locate:") or command_lower.startswith("locate_tp:"):
            return True, "Valid (internal token)"
        
        for pattern in self.dangerous_patterns:
            if pattern.search(command):
                return False, f"Dangerous pattern detected: {pattern.pattern}"
        
        for black in self.blacklist:
            if command_lower.startswith(black):
                return False, f"Blacklisted command: {black}"
        
        cmd_name = self._extract_cmd_name(command_lower)
        dynamic_allowed = set(self.allowed_commands) | set(command_catalog.get_commands())
        if cmd_name and dynamic_allowed and cmd_name not in dynamic_allowed:
            # Allow unknown commands if they are namespaced, often plugin-owned.
            if ":" not in (command_lower.split()[0] if command_lower.split() else ""):
                return False, f"Unknown command root: {cmd_name}"
        
        return True, "Valid"
    
    def is_safe(self, command):
        valid, _ = self.validate(command)
        return valid
    
    def check_syntax(self, command):
        parts = command.split()
        if not parts:
            return False, "Empty command"
        
        base_cmd = parts[0].replace('minecraft:', '').replace('/', '')
        
        return True, "Syntax appears valid"

    def _extract_cmd_name(self, command_lower):
        first = command_lower.split()[0] if command_lower.split() else ""
        first = first.lstrip("/")
        if first.startswith("locate:") or first.startswith("locate_tp:"):
            return first
        if ":" in first:
            first = first.split(":", 1)[1]
        return first


class Simulator:
    def __init__(self):
        self.validator = Validator()
        self.simulation_log = []
    
    def simulate(self, command, player_name):
        valid, message = self.validator.validate(command)
        
        if not valid:
            self._log_simulation(command, player_name, False, message)
            return False, message
        
        valid_syntax, syntax_msg = self.validator.check_syntax(command)
        if not valid_syntax:
            self._log_simulation(command, player_name, False, syntax_msg)
            return False, syntax_msg
        
        self._log_simulation(command, player_name, True, "Simulation passed")
        return True, "Simulation passed"
    
    def _log_simulation(self, command, player, success, message):
        self.simulation_log.append({
            "command": command,
            "player": player,
            "success": success,
            "message": message
        })
        self.simulation_log = self.simulation_log[-100:]
    
    def get_simulation_log(self, limit=20):
        return self.simulation_log[-limit:]


validator = Validator()
simulator = Simulator()
