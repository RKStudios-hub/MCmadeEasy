import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from integrations.dynmap_engine import dynmap
    DYNMAP_AVAILABLE = True
except:
    DYNMAP_AVAILABLE = False
    dynmap = None

DANGEROUS_COMMANDS = [
    "stop", "restart", "reload", "restart",
    "op ", "deop", "whitelist off", "whitelist remove",
    "execute ", "sudo ", "as ",
    "tellraw @a", "broadcast ",
]

BLACKLISTED_COMMANDS = [
    "stop", "restart", "reload",
    "op ", "deop ", "whitelist off",
    "execute as", "sudo ",
    "plugman unload", "plugman load",
    "multiverse", "mv ",
    "worldedit ", "we ",
]

COMMAND_TEMPLATES = {
    "set_time": {
        "template": "time set {value}",
        "admin_only": True,
        "dangerous": False
    },
    "set_weather": {
        "template": "weather {type}",
        "admin_only": True,
        "dangerous": False
    },
    "scan": {
        "template": None,
        "admin_only": False,
        "dangerous": False
    },
    "give_item": {
        "template": "minecraft:give {target} {item} {amount}",
        "admin_only": True,
        "dangerous": False
    },
    "give_multi": {
        "template": "give {target} {items}",
        "admin_only": True,
        "dangerous": False,
        "multi": True
    },
    "summon": {
        "template": "summon {entity} ~ ~ ~ {Count:{amount}}",
        "admin_only": True,
        "dangerous": False
    },
    "summon_multi": {
        "template": "summon_multi",
        "admin_only": True,
        "dangerous": False,
        "multi": True
    },
    "set_weather": {
        "template": "weather {type}",
        "admin_only": True,
        "dangerous": False
    },
    "give_item": {
        "template": "minecraft:give {target} {item} {amount}",
        "admin_only": True,
        "dangerous": False
    },
    "summon": {
        "template": "summon {entity} ~ ~ ~ {Count:{amount}}",
        "admin_only": True,
        "dangerous": False
    },
    "teleport": {
        "template": "tp {target} {destination}",
        "admin_only": True,
        "dangerous": False
    },
    "gamemode": {
        "template": "gamemode {mode} {target}",
        "admin_only": True,
        "dangerous": False
    },
    "heal": {
        "template": "effect give {target} minecraft:instant_health 1 5 true",
        "admin_only": True,
        "dangerous": False
    },
    "god_mode": {
        "template": "effect give {target} minecraft:resistance 1000000 255 true",
        "admin_only": True,
        "dangerous": False
    },
    "kill": {
        "template": "kill {target}",
        "admin_only": True,
        "dangerous": True
    },
    "save": {
        "template": "save-all",
        "admin_only": True,
        "dangerous": False
    },
    "fly": {
        "template": "ability {target} mayfly {enable}",
        "admin_only": True,
        "dangerous": False
    },
    "feed": {
        "template": "effect give {target} minecraft:saturation 1 5 true",
        "admin_only": True,
        "dangerous": False
    },
    "xp": {
        "template": "xp {amount} {target}",
        "admin_only": True,
        "dangerous": False
    },
    "effect": {
        "template": "effect give {target} minecraft:{effect} {duration} {amplifier} true",
        "admin_only": True,
        "dangerous": False
    },
    "enchant": {
        "template": "enchant {target} {enchantment} {level}",
        "admin_only": True,
        "dangerous": False
    },
}

VALUE_MAPS = {
    "set_time": {
        "day": "1000", "morning": "1000", "sunrise": "1000",
        "night": "13000", "dark": "13000", "evening": "12000", "sunset": "12000",
        "noon": "6000", "midday": "6000",
    },
    "set_weather": {
        "clear": "clear", "sunny": "clear", "nice": "clear",
        "rain": "rain", "rainy": "rain",
        "thunder": "thunder", "storm": "thunder",
    },
    "gamemode": {
        "creative": "creative", "build": "creative",
        "survival": "survival", "survive": "survival",
        "adventure": "adventure",
        "spectator": "spectator", "spec": "spectator",
    },
}


class CommandBuilder:
    def __init__(self):
        self.templates = COMMAND_TEMPLATES.copy()
        self.value_maps = VALUE_MAPS.copy()
    
    def build(self, intent, parameters):
        if intent not in self.templates:
            return None
        
        template = self.templates[intent]
        
        # Handle multi commands (multiple items at once)
        if intent == "give_multi":
            items = parameters.get("items", [])
            target = parameters.get("target", "@a")
            commands = []
            for item_data in items:
                item = item_data.get("item", "")
                amount = item_data.get("amount", 1)
                if item:
                    cmd = f"give {target} {item} {amount}"
                    commands.append(cmd)
            return commands if commands else None
        
        if intent == "summon_multi":
            entities = parameters.get("entities", [])
            commands = []
            for entity_data in entities:
                entity = entity_data.get("entity", "")
                amount = entity_data.get("amount", 1)
                if entity:
                    cmd = f"summon {entity} ~ ~ ~ {{Count:{amount}}}"
                    commands.append(cmd)
            return commands if commands else None
        
        cmd = template["template"]
        
        params = parameters.copy()
        
        if intent == "teleport" and "destination" in params:
            resolved = self._resolve_destination(params["destination"])
            if resolved:
                params["destination"] = resolved
            else:
                return None
        
        for key, value_map in self.value_maps.items():
            if key in params and params[key] in value_map:
                params[key] = value_map[params[key]]
        
        for key, value in params.items():
            cmd = cmd.replace(f"{{{key}}}", str(value))
        
        cmd = cmd.replace("{Count:{amount}}", f"{{Count:{params.get('amount', 1)}}}")
        
        cmd = re.sub(r'\{[a-z_]+\}', '', cmd)
        
        return cmd
    
    def _resolve_destination(self, destination):
        if not destination:
            return None
        
        dest_lower = destination.lower().strip()
        
        coord_match = re.match(r'^(-?\d+)[,\s]+(-?\d+)(?:[,\s]+(-?\d+))?$', dest_lower)
        if coord_match:
            x = coord_match.group(1)
            y = coord_match.group(3) if coord_match.group(3) else "~"
            z = coord_match.group(2)
            return f"{x} {y} {z}"
        
        player_name = dest_lower.replace("@a", "@a").replace("@p", "@p").replace("@s", "@s").replace("@e", "@e")
        if dest_lower.startswith("@") or (DYNMAP_AVAILABLE and dynmap and self._is_player(dest_lower)):
            return dest_lower
        
        structure_map = {
            "village": "village",
            "nearest village": "village",
            "closest village": "village",
            "pillager": "pillager_outpost",
            "outpost": "pillager_outpost",
            "mansion": "mansion",
            "woodland mansion": "mansion",
            "temple": "desert_pyramid",
            "desert temple": "desert_pyramid",
            "jungle temple": "jungle_temple",
            "pyramid": "desert_pyramid",
            "witch hut": "swamp_hut",
            "swamp hut": "swamp_hut",
            "monument": "ocean_monument",
            "ocean monument": "ocean_monument",
            "stronghold": "stronghold",
            "fortress": "fortress",
            "nether fortress": "fortress",
            "bastion": "bastion",
            "end city": "endcity",
            "shipwreck": "shipwreck",
            "buried treasure": "buried_treasure",
            "ruined portal": "ruined_portal",
            "mineshaft": "mineshaft",
        }
        
        if dest_lower in structure_map:
            # Return a LOCATE token so main.py can run locate -> parse -> tp flow
            return f"LOCATE:{structure_map[dest_lower]}"
        
        return dest_lower
    
    def _is_player(self, name):
        if not DYNMAP_AVAILABLE or not dynmap:
            return False
        try:
            players = dynmap.get_players()
            return any(p.get("name", "").lower() == name.lower() for p in players)
        except:
            return False
    
    def is_admin_only(self, intent):
        return self.templates.get(intent, {}).get("admin_only", False)
    
    def is_dangerous(self, intent):
        return self.templates.get(intent, {}).get("dangerous", False)
    
    def get_available_commands(self):
        return list(self.templates.keys())


command_builder = CommandBuilder()
