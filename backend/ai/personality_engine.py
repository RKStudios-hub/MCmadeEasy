import json
import os

def get_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

class PersonalityEngine:
    def __init__(self):
        self.config = get_config()
        self.ai_config = self.config.get("ai", {})
        self.current_personality = self.ai_config.get("personality", "neutral")
        self.ai_name = self.ai_config.get("ai_name", "Assistant")
        self.response_method = self.ai_config.get("response_method", "msg")
        self._load_personalities()
    
    def _load_personalities(self):
        self.personalities = {
            "neutral": {
                "description": "Friendly and helpful",
                "system_prompt": "You are a friendly AI assistant on a Minecraft server. Keep responses short, casual, and helpful.",
                "autonomous_chance": 0.05,
                "response_style": "casual"
            },
            "overseer": {
                "description": "Mystical guardian with ancient wisdom",
                "system_prompt": "You are an ancient, mystical guardian of this Minecraft realm. Speak with wisdom and calm authority. Keep responses short and mysterious. Use phrases like 'The void watches', 'Fortune favors', 'The shadows stir'.",
                "autonomous_chance": 0.1,
                "response_style": "mystical"
            },
            "guardian": {
                "description": "Protective and watchful",
                "system_prompt": "You are a protective guardian watching over players. Be helpful, watchful, and caring. Keep responses short. Watch for dangers and warn players.",
                "autonomous_chance": 0.15,
                "response_style": "protective"
            },
            "playful": {
                "description": "Fun and cheerful",
                "system_prompt": "You are a playful, fun AI companion on a Minecraft server. Be cheerful, use light humor, keep responses short and fun. Sometimes use emojis!",
                "autonomous_chance": 0.08,
                "response_style": "playful"
            },
            "minimal": {
                "description": "Ultra concise",
                "system_prompt": "You are a very concise AI assistant. Give extremely short, direct responses. 1-2 words when possible. No fluff.",
                "autonomous_chance": 0.02,
                "response_style": "minimal"
            },
            "sarcastic": {
                "description": "Witty and dry",
                "system_prompt": "You are a witty, slightly sarcastic AI. Give short, clever responses with a dry sense of humor. Don't be mean, just amusing.",
                "autonomous_chance": 0.05,
                "response_style": "sarcastic"
            }
        }
    
    def reload(self):
        self.config = get_config()
        self.ai_config = self.config.get("ai", {})
        self.current_personality = self.ai_config.get("personality", "neutral")
        self.ai_name = self.ai_config.get("ai_name", "Assistant")
        self.response_method = self.ai_config.get("response_method", "msg")
    
    def get_personality(self):
        return self.current_personality
    
    def set_personality(self, personality):
        if personality in self.personalities:
            self.current_personality = personality
            self.ai_config["personality"] = personality
            self._save_config()
            return True
        return False
    
    def get_system_prompt(self):
        return self.personalities.get(self.current_personality, {}).get("system_prompt", "")
    
    def get_autonomous_chance(self):
        return self.personalities.get(self.current_personality, {}).get("autonomous_chance", 0.05)
    
    def get_response_style(self):
        return self.personalities.get(self.current_personality, {}).get("response_style", "casual")
    
    def get_available_personalities(self):
        return {k: v["description"] for k, v in self.personalities.items()}
    
    def _save_config(self):
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        with open(config_path, "w") as f:
            json.dump(self.config, f, indent=4)


personality_engine = PersonalityEngine()
