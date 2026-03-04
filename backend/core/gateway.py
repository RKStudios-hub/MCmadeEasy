import json
import os
import requests

def get_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

PROVIDER_ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "google": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
}

class Gateway:
    def __init__(self):
        self.config = get_config()
        self.ai_config = self.config.get("ai", {})
        self.provider = self.ai_config.get("provider", "groq")
        self.api_key = self.ai_config.get("api_key", "")
        self.model = self.ai_config.get("model", "llama-3.1-8b-instant")
        self.enabled = self.ai_config.get("enabled", True)
        self.mode = self.ai_config.get("mode", "chat")
        self.providers_config = self.ai_config.get("providers", {})
        self.server_context = {}
    
    def reload(self):
        self.config = get_config()
        self.ai_config = self.config.get("ai", {})
        self.provider = self.ai_config.get("provider", "groq")
        self.api_key = self.ai_config.get("api_key", "")
        self.model = self.ai_config.get("model", "llama-3.1-8b-instant")
        self.enabled = self.ai_config.get("enabled", True)
        self.mode = self.ai_config.get("mode", "chat")
        self.providers_config = self.ai_config.get("providers", {})
    
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
    
    def _get_provider_key(self, provider=None):
        provider = provider or self.provider
        providers = self.providers_config.get(provider, {})
        if providers.get("api_key"):
            return providers["api_key"]
        if provider == "groq" and self.ai_config.get("api_key"):
            return self.ai_config["api_key"]
        return None
    
    def call_ai(self, system_prompt, user_message, temperature=0.7, provider=None, model=None):
        provider = provider or self.provider
        model = model or self.model
        
        api_key = self._get_provider_key(provider)
        if not api_key:
            return None, f"No API key configured for {provider}"
        
        if provider == "groq":
            return self._call_groq(api_key, model, system_prompt, user_message, temperature)
        elif provider == "openai":
            return self._call_openai(api_key, model, system_prompt, user_message, temperature)
        elif provider == "anthropic":
            return self._call_anthropic(api_key, model, system_prompt, user_message, temperature)
        elif provider == "google":
            return self._call_google(api_key, model, system_prompt, user_message, temperature)
        elif provider == "azure":
            return self._call_azure(api_key, model, system_prompt, user_message, temperature)
        elif provider == "local":
            return self._call_local(model, system_prompt, user_message, temperature)
        else:
            return None, f"Unknown provider: {provider}"
    
    def _call_groq(self, api_key, model, system_prompt, user_message, temperature):
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": 256
        }
        return self._make_request(url, headers, data)
    
    def _call_openai(self, api_key, model, system_prompt, user_message, temperature):
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": 256
        }
        return self._make_request(url, headers, data)
    
    def _call_anthropic(self, api_key, model, system_prompt, user_message, temperature):
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": 256
        }
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=15)
            result = resp.json()
            if "content" in result:
                return result["content"][0]["text"], None
            elif "error" in result:
                return None, result["error"].get("message", "API Error")
            else:
                return None, str(result)
        except Exception as e:
            return None, str(e)
    
    def _call_google(self, api_key, model, system_prompt, user_message, temperature):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": user_message}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 256
            }
        }
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=15)
            result = resp.json()
            if "candidates" in result:
                return result["candidates"][0]["content"]["parts"][0]["text"], None
            elif "error" in result:
                return None, result["error"].get("message", "API Error")
            else:
                return None, str(result)
        except Exception as e:
            return None, str(e)
    
    def _call_azure(self, api_key, model, system_prompt, user_message, temperature):
        providers_cfg = self.providers_config.get("azure", {})
        endpoint = providers_cfg.get("endpoint", "")
        deployment = providers_cfg.get("deployment", model)
        
        if not endpoint:
            return None, "Azure endpoint not configured"
        
        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-02-15-preview"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        data = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": 256
        }
        return self._make_request(url, headers, data)
    
    def _call_local(self, model, system_prompt, user_message, temperature):
        local_cfg = self.providers_config.get("local", {})
        url = local_cfg.get("url", "http://localhost:11434")
        
        if "/v1/chat/completions" not in url and "/completions" not in url:
            if "/api/chat" in url or "/generate" in url:
                pass
            else:
                url = f"{url}/v1/chat/completions"
        
        headers = {"Content-Type": "application/json"}
        
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": 256
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=60)
            result = resp.json()
            if "choices" in result:
                return result["choices"][0]["message"]["content"], None
            elif "response" in result:
                return result["response"], None
            elif "error" in result:
                return None, result.get("error", {}).get("message", "Local LLM Error")
            else:
                return None, str(result)
        except Exception as e:
            return None, str(e)
    
    def _make_request(self, url, headers, data):
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
