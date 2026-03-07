import re
import difflib
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
    "raw_command": {
        "template": None,
        "admin_only": True,
        "dangerous": True
    },
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
        "template": "give {target} {item} {amount}",
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
    "teleport": {
        "template": "tp {target} {destination}",
        "admin_only": True,
        "dangerous": False
    },
    "locate": {
        "template": None,
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

        if intent == "raw_command":
            command = (parameters.get("command") or "").strip()
            if not command:
                return None
            return self._normalize_raw_command(command.lstrip("/"))
        
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
        
        if intent == "locate":
            structure = parameters.get("structure") or parameters.get("destination")
            resolved = self._resolve_structure(structure)
            if resolved:
                return f"LOCATE:{resolved}"
            return None
        
        cmd = template["template"]
        
        params = parameters.copy()
        
        if intent == "teleport" and "destination" in params:
            resolved = self._resolve_destination(params["destination"])
            if resolved:
                if isinstance(resolved, str) and resolved.startswith("LOCATE:"):
                    structure_id = resolved.split(":", 1)[1]
                    target = params.get("target", "@a")
                    return f"LOCATE_TP:{structure_id}:{target}"
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
        
        structure_id = self._resolve_structure(dest_lower)
        if structure_id:
            # Return a LOCATE token so main.py can run locate -> parse -> tp flow
            return f"LOCATE:{structure_id}"
        
        return dest_lower
    
    def _resolve_structure(self, name):
        if not name:
            return None
        struct_lower = str(name).lower().strip()
        struct_norm = re.sub(r"[_-]+", " ", struct_lower)
        struct_norm = re.sub(r"\s+", " ", struct_norm).strip()
        structure_map = {
            "village": "village",
            "nearest village": "village",
            "closest village": "village",
            "snowy village": "village_snowy",
            "snow village": "village_snowy",
            "showy village": "village_snowy",
            "desert village": "village_desert",
            "savanna village": "village_savanna",
            "taiga village": "village_taiga",
            "plains village": "village_plains",
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
            "end city": "end_city",
            "endcity": "end_city",
            "shipwreck": "shipwreck",
            "buried treasure": "buried_treasure",
            "ruined portal": "ruined_portal",
            "mineshaft": "mineshaft",
        }
        if struct_norm in structure_map:
            return structure_map[struct_norm]

        # Prefer explicit multi-word phrase containment (e.g. "desert village")
        for key in sorted(structure_map.keys(), key=len, reverse=True):
            if " " in key and key in struct_norm:
                return structure_map[key]

        # Fuzzy match after phrase checks to handle typos like "showy village".
        close = difflib.get_close_matches(struct_norm, list(structure_map.keys()), n=1, cutoff=0.72)
        if close:
            return structure_map[close[0]]

        # Single-word fallback only for exact token hits.
        tokens = set(struct_norm.split())
        for key, value in structure_map.items():
            if " " not in key and key in tokens:
                return value
        return None
    
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

    def _normalize_raw_command(self, command):
        cmd = command.strip()
        lower = cmd.lower()

        # Common shorthand normalization from chat-style wording.
        time_match = re.match(r"^time\s+(day|night|noon|midnight|sunrise|sunset|\d+)$", lower)
        if time_match:
            return f"time set {time_match.group(1)}"

        gamemode_match = re.match(r"^gamemode\s+(survival|creative|adventure|spectator)$", lower)
        if gamemode_match:
            return f"gamemode {gamemode_match.group(1)} @a"

        tp_me_match = re.match(r"^(tp|teleport)\s+me\s+(.+)$", cmd, re.IGNORECASE)
        if tp_me_match:
            raw_dest = tp_me_match.group(2).strip()
            raw_dest = re.sub(r"^(to\s+)", "", raw_dest, flags=re.IGNORECASE).strip()
            resolved = self._resolve_destination(raw_dest)
            if isinstance(resolved, str) and resolved.startswith("LOCATE:"):
                structure_id = resolved.split(":", 1)[1]
                return f"LOCATE_TP:{structure_id}:@a"
            if resolved:
                return f"tp @a {resolved}"
            return "tp @a"

        # Normalize natural-language locate shorthand.
        locate_match = re.match(r"^locate\s+(?:nearest|closest)\s+(.+)$", lower)
        if locate_match:
            structure_text = locate_match.group(1).strip()
            resolved = self._resolve_structure(structure_text)
            if resolved:
                return f"LOCATE:{resolved}"
            return f"locate structure {structure_text}"

        locate_plain_match = re.match(r"^locate\s+(.+)$", lower)
        if locate_plain_match and "structure" not in lower and "biome" not in lower:
            structure_text = locate_plain_match.group(1).strip()
            resolved = self._resolve_structure(structure_text)
            if resolved:
                return f"LOCATE:{resolved}"
            return f"locate structure {structure_text}"

        # Natural kill phrasing -> valid selector command
        kill_all_match = re.match(r"^kill\s+all(?:\s+the)?\s+([a-z_ ]+)$", lower)
        if kill_all_match:
            entity_text = kill_all_match.group(1).strip()
            entity_map = {
                "enderman": "enderman",
                "endermen": "enderman",
                "zombie": "zombie",
                "zombies": "zombie",
                "skeleton": "skeleton",
                "skeletons": "skeleton",
                "skelitons": "skeleton",
                "skeltons": "skeleton",
                "creeper": "creeper",
                "creepers": "creeper",
                "spider": "spider",
                "spiders": "spider",
                "sheep": "sheep",
                "sheeps": "sheep",
                "villager": "villager",
                "villagers": "villager",
                "vilager": "villager",
                "vilagers": "villager",
            }
            if entity_text in entity_map:
                entity = entity_map[entity_text]
            else:
                close = difflib.get_close_matches(entity_text, list(entity_map.keys()), n=1, cutoff=0.74)
                entity = entity_map[close[0]] if close else entity_text.replace(" ", "_")
            # 3 chunks radius = 48 blocks. Execute at players so distance is player-relative.
            return f"execute at @a run kill @e[type=minecraft:{entity},distance=..48]"

        return cmd


command_builder = CommandBuilder()
