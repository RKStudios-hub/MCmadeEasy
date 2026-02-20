import requests
import json
import math

STRUCTURE_MARKERS = {
    "village": "Village",
    "pillager_outpost": "Pillager Outpost", 
    "desert_pyramid": "Desert Pyramid",
    "jungle_temple": "Jungle Temple",
    "swamp_hut": "Witch Hut",
    "ocean_monument": "Ocean Monument",
    "woodland_mansion": "Woodland Mansion",
    "stronghold": "Stronghold",
    "mineshaft": "Mineshaft",
    "ruined_portal": "Ruined Portal",
    "shipwreck": "Shipwreck",
    "buried_treasure": "Buried Treasure",
    "ocean_ruin": "Ocean Ruin",
    "igloo": "Igloo",
    "bastion": "Bastion Remnant",
    "nether_fortress": "Nether Fortress",
    "ruined_portal_nether": "Ruined Portal",
}

BIOME_HINTS = {
    "plains": "grassland plains",
    "forest": "dense forest",
    "birch_forest": "birch forest",
    "dark_forest": "dark forest",
    "jungle": "lush jungle",
    "taiga": "snowy taiga",
    "desert": "arid desert",
    "savanna": "dry savanna",
    "mountains": "mountainous terrain",
    "ice_plains": "frozen tundra",
    "swamp": "murky swamp",
    "mushroom_island": "fungal island",
    "beach": "sandy beach",
    "ocean": "deep ocean",
    "river": "flowing river",
    "nether_wastes": "nether wasteland",
    "soul_sand_valley": "soul sand valley",
    "crimson_forest": "crimson forest",
    "warped_forest": "warped forest",
}


class DynmapIntegration:
    def __init__(self, host="127.0.0.1", port=8123):
        self.base_url = f"http://{host}:{port}"
        self.enabled = False
        self.endpoints = {}
        self._test_connection()
        self._load_worlds()
    
    def _test_connection(self):
        endpoints_to_try = [
            ("/up", "up"),
            ("/up.php", "up_php"),
            ("/", "root"),
            ("/index.html", "index"),
        ]
        
        for path, name in endpoints_to_try:
            try:
                resp = requests.get(f"{self.base_url}{path}", timeout=2)
                if resp.status_code == 200:
                    self.endpoints[name] = True
                    self.enabled = True
            except:
                pass
        
        standalone_endpoints = [
            "/standalone/players.json",
            "/api/players", 
            "/worlds",
        ]
        
        for path in standalone_endpoints:
            try:
                resp = requests.get(f"{self.base_url}{path}", timeout=2)
                if resp.status_code == 200:
                    self.endpoints["standalone_json"] = path
                    break
            except:
                pass
    
    def _load_worlds(self):
        self.worlds = self.get_worlds()
    
    def is_enabled(self):
        return self.enabled
    
    def get_players(self):
        try:
            resp = requests.get(f"{self.base_url}/standalone/players.json", timeout=2)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return []
    
    def get_player_positions(self):
        players = self.get_players()
        positions = {}
        for p in players:
            positions[p.get("name")] = {
                "x": p.get("x"),
                "y": p.get("y"),
                "z": p.get("z"),
                "world": p.get("world", "world"),
                "health": p.get("health", 20)
            }
        return positions
    
    def get_worlds(self):
        try:
            resp = requests.get(f"{self.base_url}/standalone/worlds.json", timeout=2)
            if resp.status_code == 200:
                worlds_data = resp.json()
                return worlds_data
        except:
            pass
        return []
    
    def get_markers(self, world="world"):
        try:
            resp = requests.get(f"{self.base_url}/standalone/markers/{world}.json", timeout=2)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return {"sets": {}, "markers": []}
    
    def get_structure_markers(self, world="world"):
        markers_data = self.get_markers(world)
        structures = []
        
        for marker in markers_data.get("markers", []):
            marker_type = marker.get("type", "")
            if "marker" in marker_type.lower():
                label = marker.get("label", "")
                x = marker.get("x", 0)
                y = marker.get("y", 0)
                z = marker.get("z", 0)
                structures.append({
                    "name": label,
                    "x": x, "y": y, "z": z,
                    "type": "structure"
                })
        
        return structures
    
    def find_nearby_structures(self, x, y, z, world="world", radius=500):
        structures = self.get_structure_markers(world)
        nearby = []
        
        for s in structures:
            dx = s["x"] - x
            dz = s["z"] - z
            distance = (dx*dx + dz*dz) ** 0.5
            if distance < radius:
                nearby.append({
                    "name": s["name"],
                    "distance": int(distance),
                    "direction": self._get_direction(dx, dz)
                })
        
        nearby.sort(key=lambda s: s["distance"])
        return nearby[:5]
    
    def _get_direction(self, dx, dz):
        angle = math.atan2(dz, dx) * 180 / 3.14159
        if -22.5 <= angle < 22.5:
            return "east"
        elif 22.5 <= angle < 67.5:
            return "southeast"
        elif 67.5 <= angle < 112.5:
            return "south"
        elif 112.5 <= angle < 157.5:
            return "southwest"
        elif 157.5 <= angle < 180 or -180 <= angle < -157.5:
            return "west"
        elif -157.5 <= angle < -112.5:
            return "northwest"
        elif -112.5 <= angle < -67.5:
            return "north"
        elif -67.5 <= angle < -22.5:
            return "northeast"
        return "unknown"
    
    def describe_location(self, x, y, z, world="world"):
        description = f"at coordinates {int(x)}, {int(y)}, {int(z)}"
        
        if y < 20:
            description += " (underground in a cave)"
        elif y < 40:
            description += " (underground)"
        elif y > 120:
            description += " (high in the sky)"
        elif y > 80:
            description += " (flying high)"
        elif y > 65:
            description += " (in the air)"
        
        if -100 < x < 100 and -100 < z < 100:
            description += ", near spawn"
        
        nearby_structures = self.find_nearby_structures(x, y, z, world, radius=300)
        if nearby_structures:
            closest = nearby_structures[0]
            description += f", {closest['distance']} blocks {closest['direction']} from {closest['name']}"
        
        return description
    
    def get_terrain_info(self, x, y, z, world="world"):
        info = []
        
        if y < 20:
            info.append("underground/cave")
        elif y < 40:
            info.append("underground")
        elif y > 80:
            info.append("high altitude")
        
        if -100 < x < 100 and -100 < z < 100:
            info.append("near spawn")
        
        if -200 < x < 200 and -200 < z < 200:
            info.append("spawn chunks")
        
        if y > 60 and y < 70:
            info.append("sea level nearby")
        
        return info if info else ["surface"]
    
    def describe_terrain(self, x, y, z):
        descriptions = []
        
        if y < 20:
            descriptions.append("deep underground in caves")
        elif y < 40:
            descriptions.append("underground in mineshafts or caves")
        elif y > 120:
            descriptions.append("so high you might fall to your death")
        elif y > 80:
            descriptions.append("flying high above the world")
        elif y > 65:
            descriptions.append("in the clouds")
        elif 55 < y < 65:
            descriptions.append("at ocean level")
        
        if -50 < x < 50 and -50 < z < 50:
            descriptions.append("right near the world spawn point")
        
        return ", ".join(descriptions) if descriptions else "on the surface"
    
    def get_nearby_info(self, player_name):
        positions = self.get_player_positions()
        
        if player_name not in positions:
            return None
        
        player_pos = positions[player_name]
        px, py, pz = player_pos["x"], player_pos["y"], player_pos["z"]
        world = player_pos.get("world", "world")
        
        nearby_players = []
        for name, pos in positions.items():
            if name == player_name:
                continue
            dx = pos["x"] - px
            dy = pos["y"] - py
            dz = pos["z"] - pz
            distance = (dx*dx + dy*dy + dz*dz) ** 0.5
            if distance < 30:
                nearby_players.append({"name": name, "distance": int(distance)})
        
        nearby_structures = self.find_nearby_structures(px, py, pz, world, radius=500)
        
        return {
            "player": player_pos,
            "nearby_players": nearby_players,
            "nearby_structures": nearby_structures,
            "location_description": self.describe_location(px, py, pz, world),
            "terrain": self.get_terrain_info(px, py, pz, world)
        }
    
    def get_full_context(self, player_name=None):
        context_parts = []
        
        players = self.get_players()
        if players:
            names = [p.get("name") for p in players]
            context_parts.append(f"Players online: {', '.join(names)}")
        
        if player_name:
            info = self.get_nearby_info(player_name)
            if info:
                context_parts.append(f"{player_name} is {info['location_description']}")
                
                if info.get("nearby_structures"):
                    structures = info["nearby_structures"][:3]
                    struct_names = [f"{s['name']} ({s['distance']}m {s['direction']})" for s in structures]
                    context_parts.append(f"Nearby structures: {', '.join(struct_names)}")
                
                if info.get("nearby_players"):
                    player_names = [p['name'] for p in info['nearby_players']]
                    context_parts.append(f"Nearby players: {', '.join(player_names)}")
        
        return ". ".join(context_parts) + "."
    
    def get_context_string(self):
        players = self.get_players()
        if not players:
            return "No players on Dynmap."
        
        names = [p.get("name") for p in players]
        return f"Dynmap shows {len(players)} player(s) online: {', '.join(names)}"


dynmap = DynmapIntegration()
