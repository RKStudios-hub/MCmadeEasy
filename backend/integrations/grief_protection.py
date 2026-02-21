import os
import json
import time
from pathlib import Path
from collections import defaultdict

class GriefProtection:
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "grief_config.json")
        self.events_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "grief_events.json")
        self.config = self.load_config()
        self.events = []
        self.block_changes = defaultdict(list)
        self.player_actions = defaultdict(list)
    
    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                return json.load(f)
        return {
            "enabled": False,
            "monitor_world": True,
            "monitor_nether": True,
            "monitor_end": True,
            "rollback_enabled": True,
            "alert_admins": True,
            "suspicious_threshold": 10,
            "ignored_players": ["spawner_mob", "worldedit"],
            "protected_regions": []
        }
    
    def save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def enable(self, enabled=True):
        self.config["enabled"] = enabled
        self.save_config()
        return {"success": True, "enabled": enabled}
    
    def analyze_player_actions(self, player, time_window=300):
        recent_actions = [
            a for a in self.player_actions[player]
            if time.time() - a.get("timestamp", 0) < time_window
        ]
        
        suspicious_count = 0
        for action in recent_actions:
            if action.get("type") in ["block_break", "block_place"]:
                suspicious_count += 1
        
        if suspicious_count >= self.config["suspicious_threshold"]:
            return {
                "suspicious": True,
                "action_count": len(recent_actions),
                "alert": f"Player {player} has performed {suspicious_count} block actions in {time_window}s"
            }
        
        return {"suspicious": False, "action_count": len(recent_actions)}
    
    def record_action(self, player, action_type, position, block_type=None):
        action = {
            "player": player,
            "type": action_type,
            "position": position,
            "block_type": block_type,
            "timestamp": time.time()
        }
        
        self.player_actions[player].append(action)
        
        if action_type in ["block_break", "block_place"]:
            self.block_changes.append(action)
        
        if self.config["alert_admins"]:
            analysis = self.analyze_player_actions(player)
            if analysis.get("suspicious"):
                return {"alert": analysis["alert"], "action": action}
        
        return {"success": True}
    
    def rollback_player(self, player, time_seconds=300):
        if not self.config["rollback_enabled"]:
            return {"success": False, "error": "Rollback not enabled"}
        
        cutoff_time = time.time() - time_seconds
        
        relevant_actions = [
            a for a in self.block_changes
            if a["player"] == player and a.get("timestamp", 0) > cutoff_time
        ]
        
        rollback_plan = []
        for action in relevant_actions:
            if action["type"] == "block_place":
                rollback_plan.append({
                    "action": "setblock",
                    "position": action["position"],
                    "block": action.get("block_type", "air")
                })
            elif action["type"] == "block_break":
                rollback_plan.append({
                    "action": "setblock",
                    "position": action["position"],
                    "block": action.get("previous_block", "stone")
                })
        
        return {
            "success": True,
            "player": player,
            "actions_rolled_back": len(rollback_plan),
            "plan": rollback_plan
        }
    
    def add_protected_region(self, name, min_pos, max_pos):
        region = {
            "name": name,
            "min": min_pos,
            "max": max_pos,
            "created_at": time.time()
        }
        self.config["protected_regions"].append(region)
        self.save_config()
        return {"success": True, "region": region}
    
    def remove_protected_region(self, name):
        self.config["protected_regions"] = [
            r for r in self.config["protected_regions"] if r["name"] != name
        ]
        self.save_config()
        return {"success": True}
    
    def is_position_protected(self, position):
        for region in self.config["protected_regions"]:
            if (region["min"][0] <= position[0] <= region["max"][0] and
                region["min"][1] <= position[1] <= region["max"][1] and
                region["min"][2] <= position[2] <= region["max"][2]):
                return True
        return False
    
    def get_events(self, limit=50):
        return self.events[-limit:]
    
    def get_stats(self):
        return {
            "total_events": len(self.events),
            "unique_players": len(self.player_actions),
            "protected_regions": len(self.config["protected_regions"]),
            "enabled": self.config["enabled"]
        }

grief_protection = GriefProtection()
