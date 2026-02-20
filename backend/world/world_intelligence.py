import time
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from integrations.dynmap_engine import dynmap
    DYNMAP_AVAILABLE = True
except Exception as e:
    print(f"[WorldIntelligence] Dynmap import failed: {e}")
    DYNMAP_AVAILABLE = False
    dynmap = None

try:
    from integrations.terrain_analyzer import terrain_vision
    if terrain_vision:
        print(f"[WorldIntelligence] Terrain vision loaded: {type(terrain_vision)}")
except Exception as e:
    print(f"[WorldIntelligence] Terrain vision import failed: {e}")
    terrain_vision = None

_server_manager = None

def set_server_manager(server):
    global _server_manager
    _server_manager = server

class WorldIntelligence:
    def __init__(self):
        self.world_state = {
            "online_players": [],
            "weather": "clear",
            "time": "day",
            "time_ticks": 0,
            "world_mood": "calm",
            "mobs_near_players": {},
            "recent_events": [],
            "structures_near": {},
            "last_scan": 0,
            "dynmap_enabled": DYNMAP_AVAILABLE and (dynmap.is_enabled() if dynmap else False)
        }
        self.scan_interval = 30
    
    def update_player_list(self, players):
        self.world_state["online_players"] = players
    
    def update_weather(self, weather):
        self.world_state["weather"] = weather
        self._update_mood()
    
    def update_time(self, ticks):
        self.world_state["time_ticks"] = ticks
        
        if ticks < 12000:
            self.world_state["time"] = "day"
        elif ticks < 13000:
            self.world_state["time"] = "sunset"
        elif ticks < 23000:
            self.world_state["time"] = "night"
        else:
            self.world_state["time"] = "dawn"
        
        self._update_mood()
    
    def _update_mood(self):
        mood = "calm"
        
        if self.world_state["time"] == "night":
            mood = "tense"
        if self.world_state["weather"] == "rain" or self.world_state["weather"] == "thunder":
            mood = "stormy"
        
        self.world_state["world_mood"] = mood
    
    def add_event(self, event_type, details):
        self.world_state["recent_events"].append({
            "type": event_type,
            "details": details,
            "timestamp": time.time()
        })
        self.world_state["recent_events"] = self.world_state["recent_events"][-20:]
    
    def get_state(self):
        return self.world_state.copy()
    
    def get_dynmap_info(self, player_name=None):
        if not DYNMAP_AVAILABLE or not dynmap or not dynmap.enabled:
            return None
        
        if player_name:
            return dynmap.get_nearby_info(player_name)
        return dynmap.get_player_positions()
    
    def get_player_position_from_server(self, player_name):
        if not _server_manager or not _server_manager.is_running():
            return None
        
        _server_manager.send_command(f"execute at {player_name} run data get entity {player_name} Pos")
        time.sleep(0.8)
        
        recent_lines = _server_manager.output_lines[-80:]
        
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        
        for line in recent_lines:
            clean_line = ansi_escape.sub('', line)
            
            if player_name.lower() in clean_line.lower() and "entity data" in clean_line.lower():
                if ":" in clean_line:
                    data_part = clean_line.split(":", 1)[1]
                    match = re.search(r'\[([^\]]+)\]', data_part)
                    if match:
                        coords_str = match.group(1)
                        parts = [p.strip().rstrip('d').rstrip('D') for p in coords_str.split(',')]
                        if len(parts) >= 3:
                            try:
                                x = float(parts[0])
                                y = float(parts[1])
                                z = float(parts[2])
                                return {"x": x, "y": y, "z": z, "world": "world"}
                            except:
                                pass
        return None
    
    def get_player_info(self, player_name):
        print(f"[WorldIntelligence] Getting player info for {player_name}")
        
        # Try dynmap first
        if DYNMAP_AVAILABLE and dynmap and dynmap.enabled:
            print("[WorldIntelligence] Trying dynmap...")
            info = dynmap.get_nearby_info(player_name)
            if info:
                print(f"[WorldIntelligence] Got dynmap info: {info}")
                return {"source": "dynmap", **info}
        
        # Try server command
        print("[WorldIntelligence] Trying server position...")
        pos = self.get_player_position_from_server(player_name)
        if pos:
            print(f"[WorldIntelligence] Got server position: {pos}")
            return {
                "source": "server",
                "player": pos,
                "position": pos,
                "location_description": f"at coordinates {int(pos['x'])}, {int(pos['y'])}, {int(pos['z'])}",
                "nearby_players": [],
                "nearby_structures": []
            }
        
        print(f"[WorldIntelligence] No position found for {player_name}")
        return None
    
    def get_context_string(self):
        players = self.world_state["online_players"]
        weather = self.world_state["weather"]
        time_of_day = self.world_state["time"]
        mood = self.world_state["world_mood"]
        
        context = f"Players online: {', '.join(players) or 'none'}. Weather: {weather}. Time: {time_of_day}. Mood: {mood}."
        
        if self.world_state.get("dynmap_enabled") and DYNMAP_AVAILABLE and dynmap:
            try:
                dynmap_context = dynmap.get_full_context()
                if dynmap_context:
                    context = dynmap_context
            except:
                pass
        
        return context
    
    def get_player_context(self, player_name):
        info = self.get_player_info(player_name)
        if info:
            return info
        if not DYNMAP_AVAILABLE or not dynmap or not dynmap.enabled:
            return None
        
        try:
            return dynmap.get_nearby_info(player_name)
        except:
            return None
    
    def get_dynmap_context(self):
        if not DYNMAP_AVAILABLE or not dynmap or not dynmap.enabled:
            return ""
        
        try:
            return dynmap.get_context_string()
        except:
            return ""
    
    def get_terrain_info(self, x, y, z, world="world"):
        if not terrain_vision:
            return None
        
        try:
            return terrain_vision.get_terrain_summary(x, z, world)
        except:
            return None
    
    def analyze_terrain_with_ai(self, player_name, x, z, world="world", question=None):
        """Use the terrain vision AI to analyze and describe terrain"""
        print(f"[WorldIntelligence] Analyzing terrain for {player_name} at {x}, {z}")
        
        if not terrain_vision:
            print("[WorldIntelligence] No terrain_vision object")
            # Fallback to basic description without vision
            return self._basic_terrain_description(player_name, x, z)
        
        try:
            # Use vision AI that sees actual images
            result = terrain_vision.ask_terrain_ai_vision(player_name, x, z, question, world)
            print(f"[WorldIntelligence] Vision result: {result[:100] if result else 'None'}")
            if result and "not configured" not in result.lower() and "could not download" not in result.lower():
                return result
            else:
                # Fallback if vision fails
                return self._basic_terrain_description(player_name, x, z)
        except Exception as e:
            print(f"[WorldIntelligence] Terrain analysis error: {e}")
            return self._basic_terrain_description(player_name, x, z)
    
    def _basic_terrain_description(self, player_name, x, z, world_name="world"):
        """Provide basic terrain info without AI vision"""
        try:
            if terrain_vision:
                data = terrain_vision.get_terrain_summary(x, z, world_name)
                if data:
                    biome = terrain_vision.get_biome_description(data)
                    return f"At your position ({int(x)}, {int(z)}): {biome}. (Dynmap vision analysis unavailable)"
        except:
            pass
        return f"Your position is at coordinates {int(x)}, {int(z)}. I cannot analyze the terrain without Dynmap access."
    
    def get_terrain_description(self, x, z, world="world"):
        """Get simple biome description"""
        if not terrain_vision:
            return None
        
        try:
            data = terrain_vision.get_terrain_summary(x, z, world)
            if data:
                return terrain_vision.get_biome_description(data)
        except:
            pass
        return None
    
    def describe_terrain_for_player(self, x, y, z, world="world"):
        if not terrain_vision:
            return "I can't analyze the terrain right now."
        
        try:
            return terrain_vision.get_biome_description(
                terrain_vision.get_terrain_summary(x, z, world)
            )
        except:
            return "Something went wrong analyzing terrain."
    
    def should_autonomous_trigger(self, trigger):
        now = time.time()
        if now - self.world_state["last_scan"] < self.scan_interval:
            return False
        
        self.world_state["last_scan"] = now
        
        triggers = {
            "night": self.world_state["time"] == "night",
            "rain": self.world_state["weather"] == "rain",
            "thunder": self.world_state["weather"] == "thunder",
            "lonely": len(self.world_state["online_players"]) == 0,
            "crowded": len(self.world_state["online_players"]) > 5,
        }
        
        return triggers.get(trigger, False)


world_intelligence = WorldIntelligence()
