import os
import json
import urllib.request
from pathlib import Path

class ModLoader:
    def __init__(self, server_manager):
        self.server_manager = server_manager
    
    def get_mods_dir(self, profile):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server_path = os.path.join(base, "servers", profile)
        if os.path.exists(os.path.join(server_path, "plugins")):
            return os.path.join(server_path, "plugins")
        elif os.path.exists(os.path.join(server_path, "mods")):
            return os.path.join(server_path, "mods")
        return os.path.join(server_path, "mods")
    
    def get_mods_list(self, profile):
        mods_path = Path(self.get_mods_dir(profile))
        if not mods_path.exists():
            return []
        
        mods = []
        for f in mods_path.glob("*.jar"):
            mods.append({
                "name": f.stem,
                "file": f.name,
                "size": f.stat().st_size,
                "enabled": True
            })
        return mods
    
    def install_mod(self, profile, mod_url):
        mods_path = Path(self.get_mods_dir(profile))
        mods_path.mkdir(parents=True, exist_ok=True)
        
        filename = mod_url.split("/")[-1]
        dest_path = mods_path / filename
        
        try:
            urllib.request.urlretrieve(mod_url, dest_path)
            return {"success": True, "file": filename}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def remove_mod(self, profile, mod_name):
        mods_path = Path(self.get_mods_dir(profile))
        for f in mods_path.glob(f"{mod_name}*.jar"):
            f.unlink()
            return {"success": True}
        return {"success": False, "error": "Mod not found"}
    
    def get_modrinth_search(self, query, limit=10):
        url = f"https://api.modrinth.com/v2/search?query={query}&limit={limit}"
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read())
                return [{
                    "id": p["project_id"],
                    "title": p["title"],
                    "description": p["description"],
                    "downloads": p["downloads"],
                    "version": p["versions"][-1] if p["versions"] else None
                } for p in data.get("hits", [])]
        except Exception as e:
            return []
    
    def get_mod_versions(self, project_id):
        url = f"https://api.modrinth.com/v2/project/{project_id}/version"
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read())
                return [{
                    "id": v["id"],
                    "version": v["version_number"],
                    "game_versions": v["game_versions"],
                    "loaders": v["loaders"],
                    "files": [{"filename": f["filename"], "url": f["url"]} for f in v["files"]]
                } for v in data]
        except Exception as e:
            return []

mod_loader = None

def set_server_manager(manager):
    global mod_loader
    mod_loader = ModLoader(manager)
