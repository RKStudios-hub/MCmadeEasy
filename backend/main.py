from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import os
import re
import random
import time

from profile_manager import create_profile, list_profiles, get_profile, update_profile, rename_profile, delete_profile
from downloader import (
    get_vanilla_versions, download_vanilla,
    get_paper_versions, get_paper_builds, download_paper,
    get_purpur_versions, get_purpur_builds, download_purpur,
    get_spigot_versions, download_spigot,
    get_forge_versions, get_forge_builds, download_forge,
    get_latest_forge_version,
    get_neoforge_versions, get_neoforge_builds, download_neoforge,
    get_latest_neoforge_version,
    get_fabric_mc_versions, download_fabric_mc
)
from server_manager import ServerManager
import ai_engine
from world.world_intelligence import world_intelligence, set_server_manager
from integrations.mod_loader import ModLoader
from integrations.drive_backup import backup_manager
from integrations.grief_protection import grief_protection
from integrations.web_hosting import hosting_manager
from core.audit_logger import audit_logger

app = FastAPI()

server = ServerManager()
set_server_manager(server)
console_subscribers = []

mod_loader = ModLoader(server)

@app.get("/")
def root():
    return {"message": "MCmadeEasy API", "status": "running"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

console_subscribers = []
set_server_manager(server)
console_subscribers = []

async def broadcast_console_message(message: str):
    for ws in console_subscribers[:]:
        try:
            await ws.send_json({"ai": None, "chat": None, "lines": [f"[ModLoader] {message}"]})
        except:
            if ws in console_subscribers:
                console_subscribers.remove(ws)

def get_profile_path(name):
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "servers", name)

@app.get("/profiles")
def profiles():
    return list_profiles()

@app.get("/profile/{name}")
def profile(name: str):
    return get_profile(name)

@app.post("/profile/{name}")
async def create_server_profile(name: str, request: Request):
    try:
        body = await request.json()
    except:
        body = {}
    
    software = body.get("software", "paper")
    version = body.get("version", "1.21.4")
    ram = body.get("ram", "4G")
    
    profile_path = get_profile_path(name)
    if not os.path.exists(profile_path):
        create_profile(name)
    
    update_profile(name, {"software": software, "version": version, "ram": ram})
    
    return {"status": "ok", "profile": get_profile(name)}

@app.post("/profile/{name}/edit")
async def edit_server_profile(name: str, request: Request):
    try:
        body = await request.json()
    except:
        body = {}
    
    new_name = (body.get("name") or "").strip()
    version = body.get("version")
    ram = body.get("ram")
    
    if not get_profile(name):
        return {"success": False, "message": f"Profile '{name}' not found"}
    
    if server.is_running() and os.path.basename(server.current_profile) == name:
        return {"success": False, "message": "Cannot edit a running server. Stop it first."}
    
    old_profile_path = get_profile_path(name)
    if new_name and new_name != name:
        ok, err = rename_profile(name, new_name)
        if not ok:
            return {"success": False, "message": err or "Rename failed"}
        name = new_name
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        current_path = os.path.join(data_dir, "current_profile.json")
        if os.path.exists(current_path):
            try:
                with open(current_path, "r") as f:
                    data = json.load(f)
                if data.get("path"):
                    if data["path"] == old_profile_path:
                        data["path"] = get_profile_path(name)
                        with open(current_path, "w") as f:
                            json.dump(data, f)
            except:
                pass
    
    update = {}
    if version:
        update["version"] = version
    if ram:
        update["ram"] = ram
    if update:
        update_profile(name, update)
    
    return {"success": True, "profile": get_profile(name)}

@app.delete("/profile/{name}")
def delete_server_profile(name: str):
    if server.is_running() and os.path.basename(server.current_profile) == name:
        return {"success": False, "message": "Cannot delete a running server. Stop it first."}
    
    ok, err = delete_profile(name)
    if not ok:
        return {"success": False, "message": err or "Delete failed"}
    
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    current_path = os.path.join(data_dir, "current_profile.json")
    if os.path.exists(current_path):
        try:
            with open(current_path, "r") as f:
                data = json.load(f)
            if data.get("path") == get_profile_path(name):
                os.remove(current_path)
        except:
            pass
    
    return {"success": True}

@app.post("/profile/{name}/download")
def download_server(name: str, software: str, version: str, build: str = None):
    profile_path = get_profile_path(name)
    
    if software == "vanilla":
        success, msg = download_vanilla(version, profile_path)
    elif software == "paper":
        if not build:
            builds = get_paper_builds(version) or []
            build = builds[-1] if builds else None
        if not build:
            return {"success": False, "message": "No builds available for this version"}
        success, msg = download_paper(version, build, profile_path)
    elif software == "purpur":
        if not build:
            builds = get_purpur_builds(version) or []
            build = builds[-1] if builds else None
        if not build:
            return {"success": False, "message": "No builds available for this version"}
        success, msg = download_purpur(version, build, profile_path)
    elif software == "spigot" or software == "bukkit":
        success, msg = download_spigot(version, profile_path)
    elif software == "forge":
        if not build:
            full_version = get_latest_forge_version(version)
        else:
            full_version = f"{version}-{build}"
        if not full_version:
            return {"success": False, "message": "Could not find Forge version"}
        success, msg = download_forge(version, full_version, profile_path)
    elif software == "neoforge":
        return {"success": False, "message": "NeoForge requires manual download. Download from maven.neoforged.net and place server.jar in the server folder."}
    elif software == "fabric":
        success, msg = download_fabric_mc(version, profile_path)
    elif software == "quilt":
        return {"success": False, "message": "Quilt requires manual download. Use Paper or Purpur instead."}
    elif software == "leaf":
        return {"success": False, "message": "Leaf requires manual download. Use Paper or Purpur instead."}
    elif software == "spigot":
        return {"success": False, "message": "Spigot requires BuildTools to compile. Use Paper or Purpur instead."}
    else:
        return {"success": False, "message": "Unsupported software"}
    
    if success:
        print(f"[DOWNLOAD] Profile: {name}, Software: {software}, Version: {version}")
        update_profile(name, {"software": software, "version": version})
    
    return {"success": success, "message": msg}

@app.get("/versions/{software}")
def versions(software: str):
    if software == "vanilla":
        return get_vanilla_versions()
    elif software == "paper":
        return get_paper_versions()
    elif software == "fabric":
        return get_fabric_mc_versions()
    return []

@app.get("/paper/{version}/builds")
def paper_builds(version: str):
    return get_paper_builds(version)

@app.get("/status")
def status():
    running = server.is_running()
    profile = os.path.basename(server.current_profile) if server.current_profile else None
    
    # Get profile RAM info
    ram_info = "N/A"
    if profile:
        prof = get_profile(profile)
        if prof:
            ram_info = prof.get("ram", "4G")
    
    return {
        "running": running,
        "status": server.get_status(),
        "profile": profile,
        "ram": ram_info
    }

@app.post("/start/{name}")
def start(name: str):
    profile_path = get_profile_path(name)
    profile = get_profile(name)
    
    if not profile:
        return {"success": False, "message": f"Profile '{name}' not found"}
    
    jar_path = os.path.join(profile_path, "server.jar")
    if not os.path.exists(jar_path):
        return {"success": False, "message": "No server.jar found. Please download server software first using the Server Setup tab."}
    
    # Clear console output when starting a new server
    server.clear_output()
    
    ram = profile.get("ram", "4G") if profile else "4G"
    software = profile.get("software", "paper")
    print(f"[START] Profile: {name}, Software: {software}, RAM: {ram}")
    success, msg = server.start(profile_path, ram, software)
    if success:
        audit_logger.log("server_start", "system", f"Server '{name}' started with {ram} RAM", success=True, profile=name)
        update_profile(name, {"last_started": int(time.time())})
    return {"success": success, "message": msg}

@app.post("/stop")
def stop():
    profile = os.path.basename(server.current_profile) if server.current_profile else "unknown"
    success, msg = server.stop()
    if success:
        audit_logger.log("server_stop", "system", f"Server '{profile}' stopped", success=True, profile=profile)
    return {"success": success, "message": msg}

@app.get("/activity")
def get_activity(limit: int = 20, profile: str = None):
    logs = audit_logger.get_recent(limit, profile)
    return [
        {
            "type": log.get("type", ""),
            "message": log.get("message", ""),
            "datetime": log.get("datetime", ""),
            "player": log.get("player", "")
        }
        for log in logs
    ]

@app.post("/dynmap/fullrender")
def trigger_fullrender():
    """Trigger Dynmap fullrender for the world"""
    success, msg = server.send_command("dynmap fullrender world")
    return {"success": success, "message": msg, "info": "Fullrender started - this may take a long time for large worlds"}

@app.post("/dynmap/render")
def trigger_render(west: int = -1000, south: int = -1000, east: int = 1000, north: int = 1000):
    """Trigger Dynmap render for a specific area"""
    success, msg = server.send_command(f"dynmap render world {west},{south},{east},{north}")
    return {"success": success, "message": msg}

@app.post("/command")
async def command(request: Request, cmd: str = None):
    # Accept cmd via query param or JSON body for compatibility with different clients
    if not cmd:
        try:
            data = await request.json()
            cmd = data.get('cmd') or data.get('command')
        except:
            pass

    if not cmd:
        return {"success": False, "message": "No command provided"}

    success, msg = server.send_command(cmd)
    return {"success": success, "message": msg}

@app.get("/console/history")
def console_history():
    return server.get_output()

@app.get("/server/stats")
def get_server_stats():
    return server.get_stats()

@app.get("/server/properties/{profile}")
def get_server_properties(profile: str):
    profile_path = get_profile_path(profile)
    props_path = os.path.join(profile_path, "server.properties")
    if not os.path.exists(props_path):
        return {}
    
    props = {}
    with open(props_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                props[key] = val
    return props

@app.post("/server/properties/{profile}")
async def save_server_properties(profile: str, request: Request):
    try:
        data = await request.json()
    except:
        data = {}
    
    profile_path = get_profile_path(profile)
    props_path = os.path.join(profile_path, "server.properties")
    
    with open(props_path, "w") as f:
        for key, val in data.items():
            # Convert booleans to lowercase strings
            if isinstance(val, bool):
                val = "true" if val else "false"
            f.write(f"{key}={val}\n")
    
    return {"status": "saved"}

@app.get("/player/{player}/coords")
def get_player_coords(player: str):
    coords = server.get_player_coords(player)
    return {"coords": coords}

@app.get("/player/{player}/info")
def get_player_info(player: str):
    info = world_intelligence.get_player_info(player)
    return {"info": info}

@app.get("/player/{player}/terrain")
def get_player_terrain(player: str):
    info = world_intelligence.get_player_info(player)
    if info:
        pos = info.get("player", info.get("position", {}))
        if pos:
            terrain = world_intelligence.analyze_terrain_with_ai(player, pos.get("x", 0), pos.get("z", 0))
            return {"terrain": terrain}
    return {"terrain": "Could not get player position"}

@app.get("/player/{player}/entities")
def get_nearby_entities(player: str):
    entities = server.get_nearby_entities(player)
    return {"entities": entities}

@app.get("/players/all")
def get_all_players():
    """Get all players who have ever joined from usercache.json"""
    profile_path = server.current_profile
    
    # If no profile loaded, try to get it from config
    if not profile_path:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "current_profile.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    profile_path = data.get("path")
            except:
                pass
    
    # If still no profile, try to find any usercache in common locations
    if not profile_path:
        servers_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "servers")
        if os.path.exists(servers_dir):
            try:
                for item in os.listdir(servers_dir):
                    test_path = os.path.join(servers_dir, item, "usercache.json")
                    if os.path.exists(test_path):
                        profile_path = os.path.join(servers_dir, item)
                        break
            except:
                pass
    
    if not profile_path:
        return {"players": [], "error": "No profile loaded"}
    
    usercache_path = os.path.join(profile_path, "usercache.json")
    
    # Get currently online players using server query
    online_players = []
    if server.is_running():
        try:
            server_stats = server.get_stats()
            online_players = server_stats.get("players", [])
            if not isinstance(online_players, list):
                online_players = []
        except:
            online_players = []
    
    # Read usercache if it exists
    usercache = []
    if os.path.exists(usercache_path):
        try:
            with open(usercache_path, "r") as f:
                usercache = json.load(f)
        except:
            pass
    
    # Add any currently online players that might not be in usercache yet (offline accounts)
    existing_names = {entry.get("name", "").lower() for entry in usercache}
    for player_name in online_players:
        if player_name.lower() not in existing_names:
            # Add the online player dynamically (offline/non-premium account)
            usercache.insert(0, {
                "name": player_name,
                "uuid": "offline_" + player_name,
                "expiresOn": "Now"
            })
    
    players = []
    # Create lowercase set for case-insensitive matching
    online_players_lower = [p.lower() for p in online_players]
    
    for entry in usercache:
        name = entry.get("name", "")
        uuid = entry.get("uuid", "")
        expires = entry.get("expiresOn", "")
        
        # Check if online (case-insensitive)
        is_online = name.lower() in online_players_lower
        
        # Try to get stats file for additional info (only for offline players to save time)
        stats_data = None
        if not is_online and uuid and not uuid.startswith("offline_"):
            stats_path = os.path.join(profile_path, "world", "stats", f"{uuid}.json")
            if os.path.exists(stats_path):
                try:
                    with open(stats_path, "r") as f:
                        stats_data = json.load(f)
                except:
                    pass
        
        players.append({
            "name": name,
            "uuid": uuid,
            "lastPlayed": expires,
            "isOnline": is_online,
            "stats": stats_data
        })
    
    return {"players": players}

@app.get("/players/details")
def get_players_details():
    return {"players": server.get_players_details()}

@app.get("/player/{player}/inventory")
def get_player_inventory(player: str):
    """Get detailed inventory for a specific player"""
    # Only get inventory if player is online
    stats = server.get_stats()
    online_players = [p.lower() for p in stats.get("players", [])]
    
    if player.lower() not in online_players:
        return {"error": "Player not online"}
    
    # Query player details
    details = server.get_player_details(player)
    if details:
        return {
            "name": player,
            "inventory": details.get("inventory", []),
            "coords": details.get("coords"),
            "gamemode": details.get("gamemode"),
            "health": details.get("health"),
            "hunger": details.get("hunger"),
            "xp_level": details.get("xp_level")
        }
    return {"error": "Could not get player data"}

@app.get("/player/{player}/locate/{structure}")
def locate_structure(player: str, structure: str):
    result = server.locate_structure(player, structure)
    return {"result": result}

@app.get("/ai/status")
def ai_status():
    status = ai_engine.mc_ai.get_status()
    return status

@app.post("/ai/chat")
async def ai_chat(request: Request, message: str = None, player: str = "Player"):
    # Accept message/player via query params or JSON body
    if not message:
        try:
            data = await request.json()
            message = data.get('message')
            player = data.get('player', player)
        except:
            pass

    if not message:
        return {"response": None}

    result = ai_engine.mc_ai.process_message(message, player)
    if result:
        return {"response": result.get("response"), "command": result.get("command")}
    return {"response": None}

@app.post("/ai/toggle")
def ai_toggle():
    enabled = ai_engine.mc_ai.toggle()
    return {"enabled": enabled}

@app.post("/ai/mode/{mode}")
def ai_set_mode(mode: str):
    if ai_engine.mc_ai.set_mode(mode):
        return {"mode": mode}
    return {"error": "Invalid mode"}

@app.post("/ai/reload")
def ai_reload():
    ai_engine.mc_ai.reload()
    return {"status": "reloaded", "ai_name": ai_engine.mc_ai.ai_name}

@app.get("/config")
def get_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

@app.post("/config")
def save_config(data: dict):
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
    print(f"[CONFIG] Saving to: {config_path}")
    with open(config_path, "w") as f:
        json.dump(data, f, indent=4)
    ai_engine.mc_ai.reload()
    return {"status": "saved"}

@app.websocket("/console/ws")
async def console_ws(ws: WebSocket):
    await ws.accept()
    console_subscribers.append(ws)
    
    try:
        while True:
            try:
                lines = server.get_output()
                if lines:
                    data = {"lines": lines}
                    await ws.send_json(data)
                await asyncio.sleep(0.5)
            except RuntimeError as e:
                if 'close' in str(e).lower():
                    break
                raise
    except WebSocketDisconnect:
        pass
    finally:
        if ws in console_subscribers:
            console_subscribers.remove(ws)

async def broadcast_console():
    last_analyzed = ""
    last_broadcast_time = 0
    while True:
        try:
            if console_subscribers:
                lines = server.get_output()
                if lines:
                    new_line = lines[-1] if lines else ""
                    if new_line != last_analyzed and new_line:
                        last_analyzed = new_line
                        current_time = time.time()
                        
                        if current_time - last_broadcast_time < 0.3:
                            await asyncio.sleep(0.2)
                            continue
                        last_broadcast_time = current_time
                        
                        autonomous_response = ai_engine.mc_ai.process_console_line(new_line)
                        if autonomous_response:
                            ai_msg = f"[Ava] {autonomous_response}"
                            server.add_output_line(ai_msg)
                            command = f'tellraw @a [{{"text":"[{ai_engine.mc_ai.ai_name}] ","color":"light_purple"}},{{"text":"{autonomous_response}","color":"white"}}]'
                            server.send_command(command)
                        
                        chat_match = re.search(r'<([^>]+)> (.+)', new_line)
                        if chat_match:
                            player = chat_match.group(1)
                            message = chat_match.group(2).strip()
                            
                            result = ai_engine.mc_ai.process_message(message, player)
                            
                            print(f"[AI] Player: {player}, Mode: {ai_engine.mc_ai.mode}, Enabled: {ai_engine.mc_ai.is_enabled}")
                            if result:
                                print(f"[AI] Intent: {result.get('intent')}, Command: {result.get('command')}, Executed: {result.get('executed')}")
                            
                            if result and result.get("response"):
                                response = result["response"]
                                if len(response) > 150:
                                    response = response[:150] + "..."
                                # Log AI response to console
                                ai_msg = f"[Ava -> {player}] {response}"
                                server.add_output_line(ai_msg)
                                command = f'tellraw {player} [{{"text":"[{ai_engine.mc_ai.ai_name}] ","color":"light_purple"}},{{"text":"{response}","color":"white"}}]'
                                server.send_command(command)
                            
                            if result:
                                commands_to_run = result.get("commands") or ([result.get("command")] if result.get("command") else [])
                                for cmd in commands_to_run:
                                    if not cmd:
                                        continue
                                    print(f"[AI] Executing command: {cmd}")
                                    if isinstance(cmd, str) and cmd.startswith("LOCATE_TP:"):
                                        parts = cmd.split(":", 2)
                                        if len(parts) == 3:
                                            structure = parts[1]
                                            target = parts[2] if parts[2] else player
                                            locate_resp = server.locate_structure(player, structure)
                                            print(f"[AI] Locate response: {locate_resp}")
                                            if locate_resp:
                                                m = re.search(r"(-?\\d+)\\s+(-?\\d+)\\s+(-?\\d+)", locate_resp)
                                                if m:
                                                    x, y, z = m.group(1), m.group(2), m.group(3)
                                                    tp_cmd = f"tp {target} {x} {y} {z}"
                                                    server.send_command(tp_cmd)
                                                else:
                                                    server.send_command(f'tellraw {player} [{{"text":"[{ai_engine.mc_ai.ai_name}] ","color":"light_purple"}},{{"text":"Could not parse locate output for {structure}.","color":"white"}}]')
                                            else:
                                                server.send_command(f'tellraw {player} [{{"text":"[{ai_engine.mc_ai.ai_name}] ","color":"light_purple"}},{{"text":"Locate failed for {structure}.","color":"white"}}]')
                                    elif isinstance(cmd, str) and cmd.startswith("LOCATE:"):
                                        parts = cmd.split(":", 1)
                                        if len(parts) == 2:
                                            structure = parts[1]
                                            locate_resp = server.locate_structure(player, structure)
                                            print(f"[AI] Locate response: {locate_resp}")
                                            if locate_resp:
                                                server.send_command(f'tellraw {player} [{{"text":"[{ai_engine.mc_ai.ai_name}] ","color":"light_purple"}},{{"text":"{locate_resp}","color":"white"}}]')
                                            else:
                                                server.send_command(f'tellraw {player} [{{"text":"[{ai_engine.mc_ai.ai_name}] ","color":"light_purple"}},{{"text":"Locate failed for {structure}.","color":"white"}}]')
                                    else:
                                        server.send_command(cmd)
            await asyncio.sleep(0.5)
        except Exception:
            await asyncio.sleep(0.5)

@app.on_event("startup")
async def startup():
    asyncio.create_task(broadcast_console())

@app.get("/mods/search")
def search_mods(query: str):
    results = mod_loader.get_modrinth_search(query)
    return JSONResponse(content=results)

@app.get("/mods/{project_id}/versions")
def get_mod_versions(project_id: str):
    return mod_loader.get_mod_versions(project_id)

@app.get("/mods/{profile}")
def get_mods(profile: str, software: str = None):
    return mod_loader.get_mods_list(profile, software)

@app.post("/mods/{profile}/install")
async def install_mod(profile: str, request: Request):
    try:
        body = await request.json()
        mod_url = body.get("url")
        mod_name = body.get("name", "Unknown Mod")
        software = body.get("software")
        
        if not mod_url:
            return {"success": False, "error": "No mod URL provided"}
        
        result = mod_loader.install_mod(profile, mod_url, software)
        
        if result.get("success"):
            await broadcast_console_message(f"Installing mod: {mod_name}...")
            await broadcast_console_message(f"Successfully installed: {mod_name}")
            return {"success": True, "file": result.get("file")}
        else:
            await broadcast_console_message(f"Failed to install: {mod_name} - {result.get('error')}")
            return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/mods/{profile}/{mod_name}")
def remove_mod(profile: str, mod_name: str, software: str = None):
    return mod_loader.remove_mod(profile, mod_name, software)

@app.get("/backup/{profile}")
def create_backup(profile: str):
    return backup_manager.create_backup(profile)

@app.get("/backup/list")
def list_backups():
    return backup_manager.list_backups()

@app.post("/backup/restore")
def restore_backup(request: Request):
    return {"success": True, "message": "Restore functionality requires Google Drive integration"}

@app.post("/backup/schedule")
def schedule_backup(request: Request):
    return backup_manager.schedule_auto_backup("default")

@app.get("/grief/status")
def grief_status():
    return grief_protection.get_stats()

@app.post("/grief/enable")
def grief_enable(request: Request):
    return grief_protection.enable(True)

@app.post("/grief/disable")
def grief_disable(request: Request):
    return grief_protection.enable(False)

@app.post("/grief/rollback")
def grief_rollback(request: Request):
    return grief_protection.rollback_player("player", 300)

@app.get("/host/status")
def host_status():
    return hosting_manager.get_status()

@app.post("/host/start")
def host_start(request: Request):
    return hosting_manager.start_server()

@app.post("/host/stop")
def host_stop(request: Request):
    return hosting_manager.stop_server()

@app.post("/host/config")
def host_config(request: Request):
    return hosting_manager.update_config()
