"""
🗺️ MC Overseer Terrain Vision System
Reads tiles from local Dynmap files + Groq AI
"""

import json
import os
from io import BytesIO
from datetime import datetime

try:
    from PIL import Image
except Exception as e:
    Image = None
    print(f"[TerrainVision] PIL import failed: {e}")


def load_config():
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    config_path = os.path.join(backend_dir, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

config = load_config()
ai_config = config.get("ai", {})
providers_config = ai_config.get("providers", {})
VISION_PROVIDER = ai_config.get("vision_provider") or ai_config.get("provider", "groq")

# Server config to find Dynmap tiles
servers_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "servers")

# Get API key from providers (allow vision-specific override)
GROQ_API_KEY = (
    ai_config.get("vision_api_key")
    or providers_config.get("groq", {}).get("api_key", "")
    or ai_config.get("api_key", "")
)

def _resolve_vision_model():
    provider = VISION_PROVIDER
    provider_cfg = providers_config.get(provider, {})
    explicit = provider_cfg.get("vision_model") or ai_config.get("vision_model")
    if isinstance(explicit, str) and explicit.strip():
        chosen = explicit.strip()
        if "vision" in chosen.lower():
            return chosen
        print(f"[TerrainVision] Vision model '{chosen}' is not vision-capable. Falling back to a vision model.")
    models = provider_cfg.get("models", [])
    for model in models:
        if isinstance(model, str) and "vision" in model.lower():
            return model
    model = ai_config.get("model", "")
    if isinstance(model, str) and "vision" in model.lower():
        return model
    return "llama-3.2-90b-vision-preview"

TERRAIN_MODEL = _resolve_vision_model()
print(f"[TerrainVision] Using vision model: {TERRAIN_MODEL}")


class TerrainVision:
    def __init__(self):
        self.groq_client = self._init_groq()
        self.tiles_base = self._find_dynmap_tiles()
        self.placeholder_color = (50, 50, 50)
    
    def _init_groq(self):
        if VISION_PROVIDER != "groq":
            print(f"[TerrainVision] Vision provider '{VISION_PROVIDER}' not supported for image analysis")
            return None
        if not GROQ_API_KEY:
            print("[TerrainVision] No API key")
            return None
        try:
            from groq import Groq
            return Groq(api_key=GROQ_API_KEY)
        except Exception as e:
            print(f"[TerrainVision] Groq import failed: {e}")
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
        if not self.tiles_base or not Image:
            return None

        world_dir = os.path.join(self.tiles_base, world)
        prefix_dir = os.path.join(world_dir, prefix) if prefix else world_dir

        extensions = ["png", "jpg", "jpeg", "webp"]
        paths_to_try = []

        # Legacy formats
        for ext in extensions:
            if prefix:
                paths_to_try.append(os.path.join(prefix_dir, str(zoom), f"{tile_x}_{tile_z}.{ext}"))
                paths_to_try.append(os.path.join(prefix_dir, f"z{zoom}", f"{tile_x}_{tile_z}.{ext}"))
                paths_to_try.append(os.path.join(world_dir, f"{prefix}_{zoom}", f"{tile_x}_{tile_z}.{ext}"))
            else:
                paths_to_try.append(os.path.join(world_dir, str(zoom), f"{tile_x}_{tile_z}.{ext}"))
                paths_to_try.append(os.path.join(world_dir, f"z{zoom}", f"{tile_x}_{tile_z}.{ext}"))

        # Dynmap filetree format: tiles/world/<map>/<x>_<z>/<x>_<z>.<ext>
        tile_dir = os.path.join(prefix_dir, f"{tile_x}_{tile_z}")
        for ext in extensions:
            paths_to_try.append(os.path.join(tile_dir, f"{tile_x}_{tile_z}.{ext}"))

        for path in paths_to_try:
            if os.path.exists(path):
                try:
                    img = Image.open(path)
                    return img.convert("RGB")
                except Exception:
                    pass

        # If directory exists, grab the first image file inside (best-effort)
        if os.path.isdir(tile_dir):
            try:
                for name in os.listdir(tile_dir):
                    lower = name.lower()
                    if lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
                        try:
                            img = Image.open(os.path.join(tile_dir, name))
                            return img.convert("RGB")
                        except Exception:
                            continue
            except Exception:
                pass

        # Fallback: find nearest tile directory when exact tile isn't present
        if os.path.isdir(prefix_dir):
            try:
                best = None
                best_dist = None
                for name in os.listdir(prefix_dir):
                    if "_" not in name:
                        continue
                    parts = name.split("_", 1)
                    if len(parts) != 2:
                        continue
                    try:
                        tx = int(parts[0])
                        tz = int(parts[1])
                    except Exception:
                        continue
                    dist = (tx - tile_x) * (tx - tile_x) + (tz - tile_z) * (tz - tile_z)
                    if best_dist is None or dist < best_dist:
                        best_dist = dist
                        best = name
                if best:
                    nearest_dir = os.path.join(prefix_dir, best)
                    if os.path.isdir(nearest_dir):
                        for name in os.listdir(nearest_dir):
                            lower = name.lower()
                            if lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
                                try:
                                    img = Image.open(os.path.join(nearest_dir, name))
                                    return img.convert("RGB")
                                except Exception:
                                    continue
            except Exception:
                pass
        return None
    
    def get_combined_image(self, player_x, player_z, radius=3, world="world"):
        """Load tiles and combine into a single image"""
        if not self.tiles_base or not Image:
            return None
        
        prefixes = ["surface", "ct", "flat", "t", ""]
        
        center_x, center_z = self.world_to_tile(player_x, player_z)
        print(f"[TerrainVision] Looking for tiles around {center_x}, {center_z}")
        
        best_combined = None
        best_prefix = None
        for prefix in prefixes:
            tiles = []
            tile_size = None
            valid = 0
            
            for dz in range(-radius, radius + 1):
                row = []
                for dx in range(-radius, radius + 1):
                    img = self.load_tile_from_file(world, prefix, 0, center_x + dx, center_z + dz)
                    if img:
                        if not tile_size:
                            tile_size = img.size[0]
                        if img.size[0] != tile_size:
                            img = img.resize((tile_size, tile_size))
                        row.append(img)
                        valid += 1
                    else:
                        if not tile_size:
                            tile_size = 128
                        row.append(Image.new('RGB', (tile_size, tile_size), self.placeholder_color))
                tiles.append(row)
            
            if valid > 0:
                print(f"[TerrainVision] Found {valid} tiles with prefix: '{prefix}'")
                combined = Image.new('RGB', (len(tiles[0]) * tile_size, len(tiles) * tile_size))
                for y, row in enumerate(tiles):
                    for x, tile in enumerate(row):
                        combined.paste(tile, (x * tile_size, y * tile_size))
                if self._is_image_too_dark(combined) and prefix != prefixes[-1]:
                    print(f"[TerrainVision] Prefix '{prefix}' too dark, trying next")
                    if best_combined is None:
                        best_combined = combined
                        best_prefix = prefix
                    continue
                best_combined = combined
                best_prefix = prefix
                break
        
        if not best_combined:
            print(f"[TerrainVision] No tiles found for position ({player_x}, {player_z})")
            return None
        
        if best_prefix:
            print(f"[TerrainVision] Using prefix: '{best_prefix}'")
        
        return best_combined
    
    def _is_image_too_dark(self, img):
        try:
            sample = img.resize((48, 48))
            pixels = list(sample.getdata())
            if not pixels:
                return True
            dark = 0
            total = 0
            for r, g, b in pixels:
                if (r, g, b) == self.placeholder_color:
                    continue
                total += 1
                if r < 30 and g < 30 and b < 30:
                    dark += 1
            if total == 0:
                return True
            return (dark / total) > 0.75
        except Exception:
            return False

    def get_terrain_summary(self, player_x, player_z, world="world"):
        """Basic terrain heuristic from dynmap tiles (fallback when vision isn't available)."""
        if not Image:
            return None
        img = self.get_combined_image(player_x, player_z, radius=1, world=world)
        if not img:
            return None
        # Downsample to reduce cost and compute rough color ratios
        sample = img.resize((48, 48))
        pixels = list(sample.getdata())
        if not pixels:
            return None

        total = len(pixels)
        water = 0
        green = 0
        sand = 0
        snowy = 0
        dark = 0

        for r, g, b in pixels:
            if b > r + 25 and b > g + 25:
                water += 1
            if g > r + 15 and g > b + 10:
                green += 1
            if r > 170 and g > 150 and b < 120:
                sand += 1
            if r > 210 and g > 210 and b > 210:
                snowy += 1
            if r < 50 and g < 50 and b < 50:
                dark += 1

        return {
            "water_ratio": water / total,
            "green_ratio": green / total,
            "sand_ratio": sand / total,
            "snow_ratio": snowy / total,
            "dark_ratio": dark / total,
        }

    def get_biome_description(self, summary):
        if not summary:
            return "unknown terrain"
        water = summary.get("water_ratio", 0)
        green = summary.get("green_ratio", 0)
        sand = summary.get("sand_ratio", 0)
        snow = summary.get("snow_ratio", 0)
        dark = summary.get("dark_ratio", 0)

        if water > 0.45:
            return "an ocean or large body of water nearby"
        if snow > 0.35:
            return "snowy or icy terrain"
        if sand > 0.30:
            return "arid or desert-like terrain"
        if green > 0.35:
            return "lush forest or plains"
        if dark > 0.25:
            return "dark terrain (possibly caves or deep shadows)"
        return "mixed terrain"
    
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
        if not Image:
            return "Image processing not available - missing Pillow dependency"
        
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
