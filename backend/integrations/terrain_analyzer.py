"""
🗺️ MC Overseer Terrain Vision System
Reads tiles from local Dynmap files + Groq AI
"""

import json
import os
from io import BytesIO
from datetime import datetime
from PIL import Image


def load_config():
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    config_path = os.path.join(backend_dir, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

config = load_config()
ai_config = config.get("ai", {})

# Server config to find Dynmap tiles
servers_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "servers")

GROQ_API_KEY = ai_config.get("api_key", "")
TERRAIN_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


class TerrainVision:
    def __init__(self):
        self.groq_client = self._init_groq()
        self.tiles_base = self._find_dynmap_tiles()
    
    def _init_groq(self):
        if not GROQ_API_KEY:
            print("[TerrainVision] No API key")
            return None
        try:
            from groq import Groq
            return Groq(api_key=GROQ_API_KEY)
        except:
            print("[TerrainVision] Groq import failed")
            return None
    
    def _find_dynmap_tiles(self):
        """Find the local Dynmap tiles directory"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        servers_path = os.path.join(base_dir, "servers")
        
        if os.path.exists(servers_path):
            for server_name in os.listdir(servers_path):
                server_path = os.path.join(servers_path, server_name)
                if os.path.isdir(server_path):
                    tiles_path = os.path.join(server_path, "plugins", "dynmap", "web", "tiles")
                    if os.path.exists(tiles_path):
                        print(f"[TerrainVision] Found tiles at: {tiles_path}")
                        return tiles_path
        
        print("[TerrainVision] Could not find local tiles directory")
        return None
    
    def world_to_tile(self, x, z, zoom=0):
        if zoom == 0:
            tile_x = int(x // 128)
            tile_z = int(z // 128)
        else:
            scale = 2 ** zoom
            tile_x = int(x // (128 * scale))
            tile_z = int(z // (128 * scale))
        return tile_x, tile_z
    
    def load_tile_from_file(self, world, prefix, zoom, tile_x, tile_z):
        """Load a tile from local filesystem"""
        if not self.tiles_base:
            return None
        
        # Try different path formats
        paths_to_try = [
            os.path.join(self.tiles_base, world, prefix, str(zoom), f"{tile_x}_{tile_z}.png"),
            os.path.join(self.tiles_base, world, f"{prefix}_{zoom}", f"{tile_x}_{tile_z}.png"),
            os.path.join(self.tiles_base, world, prefix, f"z{zoom}", f"{tile_x}_{tile_z}.png"),
        ]
        
        for path in paths_to_try:
            if os.path.exists(path):
                try:
                    img = Image.open(path)
                    return img
                except:
                    pass
        return None
    
    def get_combined_image(self, player_x, player_z, radius=3, world="world"):
        """Load tiles and combine into a single image"""
        if not self.tiles_base:
            return None
        
        prefixes = ["flat", "t", "surface", ""]
        
        center_x, center_z = self.world_to_tile(player_x, player_z)
        print(f"[TerrainVision] Looking for tiles around {center_x}, {center_z}")
        
        for prefix in prefixes:
            tiles = []
            tile_size = 128
            valid = 0
            
            for dz in range(-radius, radius + 1):
                row = []
                for dx in range(-radius, radius + 1):
                    img = self.load_tile_from_file(world, prefix, 0, center_x + dx, center_z + dz)
                    if img:
                        row.append(img)
                        valid += 1
                    else:
                        row.append(Image.new('RGB', (tile_size, tile_size), (50, 50, 50)))
                tiles.append(row)
            
            if valid > 0:
                print(f"[TerrainVision] Found {valid} tiles with prefix: '{prefix}'")
                break
        
        if valid == 0:
            print(f"[TerrainVision] No tiles found for position ({player_x}, {player_z})")
            return None
        
        rows = len(tiles)
        cols = len(tiles[0]) if tiles else 0
        if rows == 0 or cols == 0:
            return None
        
        combined = Image.new('RGB', (cols * tile_size, rows * tile_size))
        for y, row in enumerate(tiles):
            for x, tile in enumerate(row):
                combined.paste(tile, (x * tile_size, y * tile_size))
        
        return combined
    
    def image_to_base64(self, img):
        import base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def ask_terrain_ai_vision(self, player_name, player_x, player_z, question=None, world="world"):
        """Send image to Groq vision AI"""
        print(f"[TerrainVision] Analyzing terrain at ({player_x}, {player_z})")
        
        if not self.groq_client:
            return "AI not configured - please add Groq API key"
        
        img = self.get_combined_image(player_x, player_z, radius=2, world=world)
        
        if not img:
            return f"You're at coordinates ({int(player_x)}, {int(player_z)}). I can't see the map tiles from local files. Make sure Dynmap has rendered tiles in servers/*/plugins/dynmap/web/tiles/"
        
        try:
            img_base64 = self.image_to_base64(img)
            
            user_q = question or "Describe what you see in this Minecraft map. What terrain, biomes, and structures can you identify?"
            
            completion = self.groq_client.chat.completions.create(
                model=TERRAIN_MODEL,
                messages=[
                    {"role": "system", "content": "You are analyzing Minecraft Dynmap satellite imagery. Describe terrain, biomes, structures based ONLY on what you see in the image."},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}},
                        {"type": "text", "text": f"Player: {player_name}\nPosition: {int(player_x)}, {int(player_z)}\nQuestion: {user_q}"}
                    ]}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            return completion.choices[0].message.content
        
        except Exception as e:
            print(f"[TerrainVision] AI error: {e}")
            return f"Error analyzing terrain: {str(e)}"


terrain_vision = TerrainVision()
