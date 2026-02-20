import json
import os
import time
from datetime import datetime

class MemoryEngine:
    def __init__(self, data_dir=None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.player_memories = {}
        self.conversation_history = {}
        self.world_context = {}
        self.load_memories()
    
    def load_memories(self):
        memory_file = os.path.join(self.data_dir, "memory.json")
        if os.path.exists(memory_file):
            with open(memory_file, "r") as f:
                data = json.load(f)
                self.player_memories = data.get("players", {})
                self.conversation_history = data.get("conversations", {})
    
    def save_memories(self):
        memory_file = os.path.join(self.data_dir, "memory.json")
        with open(memory_file, "w") as f:
            json.dump({
                "players": self.player_memories,
                "conversations": self.conversation_history
            }, f, indent=2)
    
    def get_player(self, player_name):
        if player_name not in self.player_memories:
            self.player_memories[player_name] = {
                "name": player_name,
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
                "last_target": None,
                "server_specific": {}
            }
        else:
            self.player_memories[player_name]["last_seen"] = time.time()
        return self.player_memories[player_name]
    
    def update_player(self, player_name, **kwargs):
        player = self.get_player(player_name)
        player.update(kwargs)
        self.save_memories()
    
    def increment_conversation(self, player_name):
        player = self.get_player(player_name)
        player["conversation_count"] = player.get("conversation_count", 0) + 1
        self.save_memories()
    
    def set_last_intent(self, player_name, intent, target=None):
        player = self.get_player(player_name)
        player["last_intent"] = intent
        player["last_target"] = target
        self.save_memories()
    
    def add_command_usage(self, player_name, command_type):
        player = self.get_player(player_name)
        freq = player.get("frequent_commands", [])
        if command_type not in freq:
            freq.append(command_type)
            player["frequent_commands"] = freq[-5:]
        self.save_memories()
    
    def get_context(self, player_name):
        player = self.get_player(player_name)
        recent_convos = self.conversation_history.get(player_name, [])[-3:]
        context = f"Player {player_name} has been here since {datetime.fromtimestamp(player['first_seen']).strftime('%Y-%m-%d')}. "
        context += f"Conversations: {player.get('conversation_count', 0)}. "
        context += f"Trust score: {player.get('trust_score', 0.5):.2f}. "
        if recent_convos:
            context += "Recent: " + " | ".join([f"'{c['user']}'→'{c['ai'][:30]}'" for c in recent_convos if len(c.get('ai', '')) > 0])
        return context
    
    def add_conversation(self, player_name, user_message, ai_response):
        if player_name not in self.conversation_history:
            self.conversation_history[player_name] = []
        self.conversation_history[player_name].append({
            "user": user_message,
            "ai": ai_response,
            "time": time.time()
        })
        self.conversation_history[player_name] = self.conversation_history[player_name][-10:]
        self.save_memories()
    
    def update_world_context(self, **kwargs):
        self.world_context.update(kwargs)
    
    def get_world_context(self):
        return self.world_context


memory_engine = MemoryEngine()
