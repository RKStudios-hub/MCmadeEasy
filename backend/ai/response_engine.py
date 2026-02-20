import json
import random
from core.gateway import gateway
from core.memory_engine import memory_engine
from world.world_intelligence import world_intelligence

PERSONALITY_PROMPTS = {
    "neutral": "You are a friendly AI assistant on a Minecraft server. Keep responses short, casual, and helpful.",
    "overseer": "You are an ancient, mystical guardian of this Minecraft realm. Speak with wisdom and calm authority. Keep responses short and mysterious.",
    "guardian": "You are a protective guardian watching over players. Be helpful, watchful, and caring. Keep responses short.",
    "playful": "You are a playful, fun AI companion. Be cheerful, use light humor, keep responses short and fun.",
    "minimal": "You are a concise AI. Give very short, direct responses. No fluff.",
    "sarcastic": "You are a witty, slightly sarcastic AI. Give short, clever responses with a dry sense of humor.",
}


class ResponseEngine:
    def __init__(self):
        self.gateway = gateway
        self.memory = memory_engine
        self.personality = "neutral"
        self.ai_name = "Assistant"
    
    def configure(self, personality=None, ai_name=None):
        if personality:
            self.personality = personality
        if ai_name:
            self.ai_name = ai_name
    
    def generate(self, message, player_name, intent_result=None, context=None):
        player = self.memory.get_player(player_name)
        role = player.get("role", "player")
        trust = player.get("trust_score", 0.5)
        
        if intent_result and intent_result.get("intent") != "none" and intent_result.get("intent") != "unknown":
            return self._generate_command_response(intent_result, player_name)
        
        return self._generate_chat_response(message, player_name, context)
    
    def _generate_command_response(self, intent_result, player_name):
        intent = intent_result.get("intent", "")
        params = intent_result.get("parameters", {})
        success = intent_result.get("executed", False)
        
        if not success:
            responses = {
                "set_time": ["Done. The sun moves to your will.", "Time shifts around you."],
                "set_weather": ["The skies obey.", "Weather changes at your command."],
                "give_item": ["Your items materialize.", "Given."],
                "summon": ["They appear.", "Summoned."],
                "gamemode": ["Your world transforms.", "Mode changed."],
                "heal": ["Health restored.", "You feel renewed."],
                "fly": ["Gravity yields to you.", "Flight enabled."],
                "save": ["World saved.", "Everything stored safely."],
            }
            base = responses.get(intent, ["Done."])
            return random.choice(base)
        
        return "Command executed."
    
    def _generate_chat_response(self, message, player_name, context):
        system_prompt = PERSONALITY_PROMPTS.get(self.personality, PERSONALITY_PROMPTS["neutral"])
        
        player_context = self.memory.get_context(player_name)
        
        world_context = self.memory.get_world_context()
        world_str = f" Players online: {world_context.get('online_players', [])}. Weather: {world_context.get('weather', 'unknown')}. Time: {world_context.get('time', 'unknown')}."
        
        message_lower = message.lower()
        
        terrain_vision_keywords = [
            "terrain", "land", "biome", "what's around", "what is around",
            "what can you see", "what do you see", "scan", "analyze",
            "environment", "area", "surroundings", "explore", "direction",
            "around me", "near me", "see around", "look around", "whats around",
            "describe this", "describe the", "river", "ocean", "lake", "forest",
            "desert", "mountain", "hill", "valley", "village", "structure",
            "whats nearby", "whats near me", "whats close"
        ]
        
        needs_terrain_vision = any(word in message_lower for word in terrain_vision_keywords)
        
        print(f"[ResponseEngine] Message: {message}, Needs terrain: {needs_terrain_vision}")
        
        if needs_terrain_vision:
            try:
                player_info = world_intelligence.get_player_info(player_name)
                print(f"[ResponseEngine] Player info: {player_info}")
                if player_info:
                    pos = player_info.get("player") or player_info.get("position", {})
                    print(f"[ResponseEngine] Position: {pos}")
                    if pos:
                        x, z = pos.get("x", 0), pos.get("z", 0)
                        terrain_response = world_intelligence.analyze_terrain_with_ai(
                            player_name, x, z, "world", message
                        )
                        print(f"[ResponseEngine] Terrain response: {terrain_response}")
                        return terrain_response
            except Exception as e:
                print(f"[ResponseEngine] Terrain error: {e}")
                pass
        
        terrain_info = ""
        needs_position = any(word in message_lower for word in ["where", "location", "coords", "position", "am i"])
        
        if needs_position:
            try:
                player_info = world_intelligence.get_player_info(player_name)
                if player_info:
                    terrain = player_info.get("location_description", "")
                    structures = player_info.get("nearby_structures", [])
                    terrain_info = f" Your position: {terrain}."
                    if structures:
                        struct_str = ", ".join([f"{s['name']} ({s['distance']}m {s['direction']})" for s in structures[:2]])
                        terrain_info += f" Nearby: {struct_str}."
                    if player_info.get("source") == "server":
                        terrain_info += " (position from server)"
            except Exception as e:
                pass
        
        prompt = f"""{system_prompt}

Player context: {player_context}
{world_str}{terrain_info}

Player {player_name} says: {message}

Respond naturally as {self.ai_name}:"""

        response, error = self.gateway.call_ai(prompt, f"{player_name}: {message}", temperature=0.8)
        
        if error:
            return f"Hmm, something's not working right. ({error})"
        
        if response:
            response = response.strip()
            if len(response) > 150:
                response = response[:150] + "..."
        
        return response or "I didn't catch that."
    
    def generate_autonomous(self, trigger, player_name, context=None):
        autonomous_responses = {
            "night": ["The darkness stirs...", "Night falls. Be watchful.", "Mobs awaken in the shadows."],
            "rain": ["The skies grow dark.", "Storm clouds gather above.", "Rain drums upon the earth."],
            "join": ["A new presence enters.", "Welcome, traveler.", "Someone new walks these lands."],
            "death": ["Death is but a temporary setback.", "The void claims another.", "Respawn and try again."],
            "achievement": ["A great accomplishment!", "Your deeds are noted.", "Fortune favors the bold."],
            "lonely": ["The lands are quiet.", "No travelers yet.", "Silence fills the void."],
            "mob_nearby": ["Something lurks nearby...", "Danger approaches.", "Hostiles detected."],
            "low_hp": ["Your vitality wanes.", "Heal soon, or perish.", "Bloodied, but alive."],
        }
        
        if trigger in autonomous_responses:
            return random.choice(autonomous_responses[trigger])
        
        return None
    
    def generate_error(self, error_type, details=None):
        errors = {
            "no_permission": "You don't have permission for that.",
            "unknown_command": "I'm not sure what you mean.",
            "execution_failed": "That command didn't work.",
            "rate_limit": "Too many requests. Slow down.",
            "api_error": "My thoughts are scattered. Try again.",
        }
        
        base = errors.get(error_type, "Something went wrong.")
        if details:
            return f"{base} ({details})"
        return base


response_engine = ResponseEngine()
