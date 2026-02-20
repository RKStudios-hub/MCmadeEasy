import json
import os

DEFAULT_PERMISSIONS = {
    "owner": ["*"],
    "admin": [
        "time", "weather", "give", "tp", "summon", "heal", "god", 
        "gamemode", "xp", "kill", "save", "kick", "ban", "unban",
        "fly", "feed", "repair", "enchant", "effect", "setblock", "fill"
    ],
    "moderator": [
        "kick", "ban", "unban", "mute", "tempban", "warn"
    ],
    "builder": [
        "gamemode", "give", "fly", "tp"
    ],
    "vip": [
        "fly", "feed", "heal", "tp"
    ],
    "player": []
}

DEFAULT_ROLES = {
    "owner": ["hrupe"],
    "admin": ["Admin", "Sweete_Nightmare"],
    "moderator": [],
    "builder": [],
    "vip": []
}

INTENT_TO_PERMISSION = {
    "give_item": "give",
    "set_time": "time",
    "set_weather": "weather",
    "summon": "summon",
    "teleport": "tp",
    "gamemode": "gamemode",
    "heal": "heal",
    "god_mode": "god",
    "kill": "kill",
    "save": "save",
    "fly": "fly",
    "feed": "feed",
    "xp": "xp",
    "effect": "effect",
    "enchant": "enchant",
}

class RoleEngine:
    def __init__(self, config_path=None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "config.json"
        )
        self.permissions = DEFAULT_PERMISSIONS.copy()
        self.roles = DEFAULT_ROLES.copy()
        self.load_config()
    
    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                config = json.load(f)
                ai_config = config.get("ai", {})
                self.roles = ai_config.get("roles", DEFAULT_ROLES)
                custom_perms = ai_config.get("permissions", {})
                if custom_perms:
                    self.permissions.update(custom_perms)
    
    def reload(self):
        self.load_config()
    
    def get_player_role(self, player_name):
        for role, players in self.roles.items():
            if player_name in players:
                return role
        return "player"
    
    def is_admin(self, player_name):
        return self.get_player_role(player_name) in ["owner", "admin"]
    
    def has_permission(self, player_name, intent):
        role = self.get_player_role(player_name)
        perms = self.permissions.get(role, [])
        
        if "*" in perms:
            return True
        if intent in perms:
            return True
        return False
    
    def can_execute(self, player_name, intent, confidence=1.0):
        mapped_intent = INTENT_TO_PERMISSION.get(intent, intent)
        
        role = self.get_player_role(player_name)
        
        print(f"[RoleEngine] Player: {player_name}, Role: {role}, Intent: {intent}, Confidence: {confidence}")
        print(f"[RoleEngine] Available permissions for {role}: {self.permissions.get(role, [])}")
        
        if role == "player":
            return False
        
        if role == "admin" and confidence >= 0.7:
            result = self.has_permission(player_name, mapped_intent)
            print(f"[RoleEngine] has_permission result: {result}")
            return result
        
        if role == "moderator" and confidence >= 0.8:
            return self.has_permission(player_name, mapped_intent)
        
        if role == "builder" and confidence >= 0.85:
            return self.has_permission(player_name, mapped_intent)
        
        return False
    
    def get_allowed_commands(self, player_name):
        role = self.get_player_role(player_name)
        return self.permissions.get(role, [])


role_engine = RoleEngine()
