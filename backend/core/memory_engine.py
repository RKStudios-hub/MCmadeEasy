import json
import os
import time
from datetime import datetime

class MemoryEngine:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.servers_dir = os.path.join(self.base_dir, "servers")
        self.player_memories = {}
        self.conversation_history = {}
        self.world_context = {}
        self.loaded_servers = set()
    
    def _get_server_path(self, server_name):
        """Get the server-specific data directory"""
        return os.path.join(self.servers_dir, server_name)
    
    def _get_memory_file(self, server_name):
        """Get the memory file path for a server"""
        return os.path.join(self._get_server_path(server_name), "memory.json")
    
    def _load_server_memory(self, server_name):
        """Load memory for a specific server"""
        if server_name in self.loaded_servers:
            return
        
        memory_file = self._get_memory_file(server_name)
        if os.path.exists(memory_file):
            try:
                with open(memory_file, "r") as f:
                    data = json.load(f)
                    # Merge into our dictionaries with server prefix
                    players = data.get("players", {})
                    for key, val in players.items():
                        full_key = f"{server_name}:{key}"
                        self.player_memories[full_key] = val
                    
                    conversations = data.get("conversations", {})
                    for key, val in conversations.items():
                        full_key = f"{server_name}:{key}"
                        self.conversation_history[full_key] = val
                    
                    world_ctx = data.get("world_context", {})
                    if world_ctx:
                        self.world_context[server_name] = world_ctx
            except Exception as e:
                print(f"Error loading memory for {server_name}: {e}")
        
        self.loaded_servers.add(server_name)
    
    def _save_server_memory(self, server_name):
        """Save memory for a specific server"""
        server_path = self._get_server_path(server_name)
        os.makedirs(server_path, exist_ok=True)
        
        # Extract just this server's data
        server_players = {}
        for key, val in self.player_memories.items():
            if key.startswith(f"{server_name}:"):
                player_key = key[len(f"{server_name}:"):]
                server_players[player_key] = val
        
        server_convos = {}
        for key, val in self.conversation_history.items():
            if key.startswith(f"{server_name}:"):
                convo_key = key[len(f"{server_name}:"):]
                server_convos[convo_key] = val
        
        memory_file = self._get_memory_file(server_name)
        with open(memory_file, "w") as f:
            json.dump({
                "players": server_players,
                "conversations": server_convos,
                "world_context": self.world_context.get(server_name, {})
            }, f, indent=2)
    
    def _get_key(self, player_name, server_name=None):
        """Get the storage key for player memory"""
        if server_name:
            return f"{server_name}:{player_name}"
        return player_name
    
    def get_player(self, player_name, server_name=None):
        if server_name:
            self._load_server_memory(server_name)
        
        key = self._get_key(player_name, server_name)
        if key not in self.player_memories:
            self.player_memories[key] = {
                "name": player_name,
                "server": server_name,
                "first_seen": time.time(),
                "last_seen": time.time(),
                "role": "player",
                "playstyle": None,
                "trust_score": 0.5,
                "preferred_tone": "casual",
                "frequent_commands": [],
                "risk_flag": False,
                "conversation_count": 0,
                "last_intent": None,
                "last_target": None
            }
        else:
            self.player_memories[key]["last_seen"] = time.time()
        return self.player_memories[key]
    
    def update_player(self, player_name, server_name=None, **kwargs):
        player = self.get_player(player_name, server_name)
        player.update(kwargs)
        if server_name:
            self._save_server_memory(server_name)
    
    def increment_conversation(self, player_name, server_name=None):
        player = self.get_player(player_name, server_name)
        player["conversation_count"] = player.get("conversation_count", 0) + 1
        if server_name:
            self._save_server_memory(server_name)
    
    def set_last_intent(self, player_name, intent, target=None, server_name=None):
        player = self.get_player(player_name, server_name)
        player["last_intent"] = intent
        player["last_target"] = target
        if server_name:
            self._save_server_memory(server_name)
    
    def add_command_usage(self, player_name, command_type, server_name=None):
        player = self.get_player(player_name, server_name)
        freq = player.get("frequent_commands", [])
        if command_type not in freq:
            freq.append(command_type)
            player["frequent_commands"] = freq[-5:]
        if server_name:
            self._save_server_memory(server_name)
    
    def get_context(self, player_name, server_name=None):
        player = self.get_player(player_name, server_name)
        key = self._get_key(player_name, server_name)
        recent_convos = self.conversation_history.get(key, [])[-3:]
        server_info = f" on server '{server_name}'" if server_name else ""
        context = f"Player {player_name} has been here{server_info} since {datetime.fromtimestamp(player['first_seen']).strftime('%Y-%m-%d')}. "
        context += f"Conversations: {player.get('conversation_count', 0)}. "
        context += f"Trust score: {player.get('trust_score', 0.5):.2f}. "
        if recent_convos:
            context += "Recent: " + " | ".join([f"'{c['user']}'→'{c['ai'][:30]}'" for c in recent_convos if len(c.get('ai', '')) > 0])
        return context
    
    def add_conversation(self, player_name, user_message, ai_response, server_name=None):
        key = self._get_key(player_name, server_name)
        if key not in self.conversation_history:
            self.conversation_history[key] = []
        self.conversation_history[key].append({
            "user": user_message,
            "ai": ai_response,
            "time": time.time()
        })
        self.conversation_history[key] = self.conversation_history[key][-10:]
        if server_name:
            self._save_server_memory(server_name)
    
    def update_world_context(self, server_name=None, **kwargs):
        if server_name:
            if server_name not in self.world_context:
                self.world_context[server_name] = {}
            self.world_context[server_name].update(kwargs)
            self._save_server_memory(server_name)
        else:
            self.world_context.update(kwargs)
    
    def get_world_context(self, server_name=None):
        if server_name:
            self._load_server_memory(server_name)
            return self.world_context.get(server_name, {})
        return self.world_context if not server_name else {}
    
    def clear_server_memory(self, server_name):
        """Clear all memory for a specific server"""
        keys_to_remove = [k for k in self.player_memories.keys() if k.startswith(f"{server_name}:")]
        for key in keys_to_remove:
            del self.player_memories[key]
        
        convo_keys_to_remove = [k for k in self.conversation_history.keys() if k.startswith(f"{server_name}:")]
        for key in convo_keys_to_remove:
            del self.conversation_history[key]
        
        if server_name in self.world_context:
            del self.world_context[server_name]
        
        # Delete the memory file
        memory_file = self._get_memory_file(server_name)
        if os.path.exists(memory_file):
            os.remove(memory_file)


memory_engine = MemoryEngine()
