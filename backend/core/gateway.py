import json
import os
import requests

def get_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

class Gateway:
    def __init__(self):
        self.config = get_config()
        self.ai_config = self.config.get("ai", {})
        self.api_key = self.ai_config.get("api_key", "")
        self.model = self.ai_config.get("model", "llama-3.1-8b-instant")
        self.enabled = self.ai_config.get("enabled", True)
        self.mode = self.ai_config.get("mode", "chat")
        self.server_context = {}
    
    def reload(self):
        self.config = get_config()
        self.ai_config = self.config.get("ai", {})
        self.api_key = self.ai_config.get("api_key", "")
        self.model = self.ai_config.get("model", "llama-3.1-8b-instant")
        self.enabled = self.ai_config.get("enabled", True)
        self.mode = self.ai_config.get("mode", "chat")
    
    def is_enabled(self):
        return self.enabled and self.mode != "off"
    
    def get_mode(self):
        return self.mode
    
    def set_mode(self, mode):
        self.mode = mode
        self.ai_config["mode"] = mode
        self._save_config()
    
    def toggle(self):
        self.enabled = not self.enabled
        self.ai_config["enabled"] = self.enabled
        self._save_config()
        return self.enabled
    
    def _save_config(self):
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        with open(config_path, "w") as f:
            json.dump(self.config, f, indent=4)
    
    def update_server_context(self, **kwargs):
        self.server_context.update(kwargs)
    
    def get_server_context(self):
        return self.server_context
    
    def call_ai(self, system_prompt, user_message, temperature=0.7):
        if not self.api_key:
            return None, "No API key configured"
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": 256
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=15)
            result = resp.json()
            if "choices" in result:
                return result["choices"][0]["message"]["content"], None
            elif "error" in result:
                return None, result["error"].get("message", "API Error")
            else:
                return None, str(result)
        except Exception as e:
            return None, str(e)


gateway = Gateway()
