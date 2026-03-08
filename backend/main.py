from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
import asyncio
import json
import os
import re
import random
import time

from profile_manager import (
    create_profile, list_profiles, get_profile, update_profile, 
    rename_profile, delete_profile, get_base_dir, BASE_DIR
)
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
from engine.command_catalog import command_catalog
from engine.ml_command_engine import ml_command_engine

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

def get_active_profile_path():
    if server.current_profile:
        return server.current_profile
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "current_profile.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                if data.get("path"):
                    return data["path"]
        except:
            pass
    return None

def _extract_locate_coords(locate_resp: str):
    if not locate_resp:
        return None
    # Typical format: "... is at [-912, ~, 224] (710 blocks away)"
    m = re.search(r"\[\s*(-?\d+)\s*,\s*(?:~|-?\d+)\s*,\s*(-?\d+)\s*\]", locate_resp)
    if m:
        return m.group(1), m.group(2)
    # Fallback: first and last integer in line
    ints = re.findall(r"-?\d+", locate_resp)
    if len(ints) >= 2:
        return ints[0], ints[-1]
    return None

def _clean_locate_message(locate_resp: str):
    if not locate_resp:
        return None
    raw = re.sub(r"^\[[^\]]+\]\s*INFO\]:\s*", "", locate_resp).strip()
    coords = _extract_locate_coords(raw)
    dist_match = re.search(r"\((\d+)\s+blocks away\)", raw, re.IGNORECASE)
    struct_match = re.search(r"nearest\s+([#a-z0-9_:]+)(?:\s+\(([^)]+)\))?", raw, re.IGNORECASE)
    if coords:
        x, z = coords
        distance = dist_match.group(1) if dist_match else None
        if struct_match:
            shown = struct_match.group(2) or struct_match.group(1)
            shown = shown.replace("minecraft:", "").replace("#", "")
            if distance:
                return f"Nearest {shown} is at x {x}, z {z} ({distance} blocks away)."
            return f"Nearest {shown} is at x {x}, z {z}."
        if distance:
            return f"Found it at x {x}, z {z} ({distance} blocks away)."
        return f"Found it at x {x}, z {z}."
    return raw

def _build_tp_fallback_commands(message: str):
    if not message:
        return []
    if not re.search(r"^\s*(tp|teleport)\b", message, re.IGNORECASE):
        return []
    try:
        # Friendly shortcut for common non-vanilla phrasing.
        if re.search(r"\bto\s+(spawn|worldspawn|world spawn)\b", message, re.IGNORECASE):
            return ["spawn"]
        fallback_cmd = ai_engine.mc_ai.command_builder.build(
            "raw_command",
            {"command": message.strip(), "target": "@a"}
        )
        if fallback_cmd:
            return [fallback_cmd]
    except Exception:
        return []
    return []

def _structure_dimension(structure: str):
    s = (structure or "").lower().strip()
    if s in ["end_city", "minecraft:end_city", "endcity"]:
        return "minecraft:the_end"
    if s in ["fortress", "minecraft:fortress", "bastion", "minecraft:bastion"]:
        return "minecraft:the_nether"
    return None

def _execute_ai_commands(commands_to_run, player):
    executed = False
    feedback = []
    for cmd in commands_to_run or []:
        if not cmd:
            continue
        executed = True
        if isinstance(cmd, str) and cmd.startswith("LOCATE_TP:"):
            parts = cmd.split(":", 2)
            if len(parts) == 3:
                structure = parts[1]
                target = parts[2] if parts[2] else player
                locate_resp = server.locate_structure(player, structure)
                if locate_resp:
                    coords = _extract_locate_coords(locate_resp)
                    if coords:
                        x, z = coords
                        dim = _structure_dimension(structure)
                        if dim:
                            server.send_command(f"execute in {dim} run tp {target} {x} ~ {z}")
                        else:
                            server.send_command(f"tp {target} {x} ~ {z}")
                        clean = _clean_locate_message(locate_resp) or "Located destination."
                        server.send_command(f'tellraw {player} [{{"text":"[{ai_engine.mc_ai.ai_name}] ","color":"light_purple"}},{{"text":"{clean} Teleporting now.","color":"white"}}]')
                        feedback.append(f"{clean} Teleporting now.")
                    else:
                        msg = f"Could not parse locate output for {structure}."
                        server.send_command(f'tellraw {player} [{{"text":"[{ai_engine.mc_ai.ai_name}] ","color":"light_purple"}},{{"text":"{msg}","color":"white"}}]')
                        feedback.append(msg)
                else:
                    msg = f"Locate failed for {structure}."
                    server.send_command(f'tellraw {player} [{{"text":"[{ai_engine.mc_ai.ai_name}] ","color":"light_purple"}},{{"text":"{msg}","color":"white"}}]')
                    feedback.append(msg)
        elif isinstance(cmd, str) and cmd.startswith("LOCATE:"):
            parts = cmd.split(":", 1)
            if len(parts) == 2:
                structure = parts[1]
                locate_resp = server.locate_structure(player, structure)
                if locate_resp:
                    clean = _clean_locate_message(locate_resp) or locate_resp
                    server.send_command(f'tellraw {player} [{{"text":"[{ai_engine.mc_ai.ai_name}] ","color":"light_purple"}},{{"text":"{clean}","color":"white"}}]')
                    feedback.append(clean)
                else:
                    msg = f"Locate failed for {structure}."
                    server.send_command(f'tellraw {player} [{{"text":"[{ai_engine.mc_ai.ai_name}] ","color":"light_purple"}},{{"text":"{msg}","color":"white"}}]')
                    feedback.append(msg)
        else:
            server.send_command(cmd)
    return executed, feedback

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
        return {"success": False, "message": "Sorry the action could not be performed because the server is running"}
    
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
        return {"success": False, "message": "Sorry the action could not be performed because the server is running"}
    
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
        try:
            backup_manager.on_server_stop(profile)
        except Exception:
            pass
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
def get_all_players(profile: str = None):
    """Get all players who have ever joined from usercache.json"""
    profile_path = None
    
    # If profile name provided, resolve to path
    if profile:
        profile_path = os.path.join(get_base_dir(), BASE_DIR, profile)
        if not os.path.exists(profile_path):
            profile_path = None
            
    # Fallback: current running server
    if not profile_path:
        profile_path = server.current_profile
    
    # Fallback: get it from config
    if not profile_path:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "current_profile.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    profile_path = data.get("path")
            except:
                pass
    
    # Final fallback: find any usercache (this is what caused the bug, keep as last resort)
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
def get_players_details(limit: int = 0):
    return {"players": server.get_players_details(limit)}

@app.get("/operators")
def get_operators(profile: str = None):
    profile_path = get_profile_path(profile) if profile else get_active_profile_path()
    if not profile_path:
        return {"operators": [], "error": "No profile loaded"}

    ops_path = os.path.join(profile_path, "ops.json")
    if not os.path.exists(ops_path):
        return {"operators": []}

    try:
        with open(ops_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        operators = []
        if isinstance(raw, list):
            for entry in raw:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name")
                if not name:
                    continue
                operators.append({
                    "name": name,
                    "uuid": entry.get("uuid"),
                    "level": entry.get("level", 4),
                    "bypassesPlayerLimit": bool(entry.get("bypassesPlayerLimit", False))
                })
        return {"operators": operators}
    except Exception as e:
        return {"operators": [], "error": str(e)}

@app.get("/player/{player}/inventory")
def get_player_inventory(player: str, fast: int = 1):
    """Get detailed inventory for a specific player"""
    # Only get inventory if player is online
    stats = server.get_stats()
    online_players = [p.lower() for p in stats.get("players", [])]
    
    if player.lower() not in online_players:
        return {"error": "Player not online"}
    
    # Fast path: inventory only
    if fast:
        details = server.get_player_inventory_fast(player)
    else:
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
    
    # Get current server name for server-specific AI memory/prompts
    server_name = None
    if server.current_profile:
        server_name = os.path.basename(server.current_profile)
    
    # Deterministic TP path: execute directly even if intent/AI path misses this turn.
    forced_tp_commands = _build_tp_fallback_commands(message)
    if forced_tp_commands:
        executed, feedback = _execute_ai_commands(forced_tp_commands, player)
        return {
            "response": feedback[0] if feedback else ("Teleporting..." if executed else "Teleport failed."),
            "command": forced_tp_commands[0],
            "executed": executed
        }

    result = ai_engine.mc_ai.process_message(message, player, server_name)
    if result:
        commands_to_run = result.get("commands") or ([result.get("command")] if result.get("command") else [])
        if not commands_to_run:
            commands_to_run = _build_tp_fallback_commands(message)
        executed, feedback = _execute_ai_commands(commands_to_run, player)

        response_text = result.get("response")
        has_locate_token = any(isinstance(c, str) and (c.startswith("LOCATE:") or c.startswith("LOCATE_TP:")) for c in commands_to_run)
        if has_locate_token:
            response_text = feedback[0] if feedback else "Done."
        return {"response": response_text, "command": result.get("command"), "executed": executed}
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

@app.get("/ai/commands")
def ai_commands(limit: int = 200):
    commands = command_catalog.get_commands()
    meta = command_catalog.get_meta()
    if limit > 0:
        commands = commands[:limit]
    return {"count": len(commands), "commands": commands, "meta": meta}

@app.get("/ai/ml/status")
def ai_ml_status():
    model = ml_command_engine.model
    return {
        "samples": len(model.get("samples", [])),
        "intents": len(model.get("by_intent", {})),
        "data_path": ml_command_engine.data_path
    }

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
    
    # Send current history first
    initial_lines = server.get_output()
    if initial_lines:
        await ws.send_json({"lines": initial_lines, "is_history": True})
    
    last_buffer = list(initial_lines)
    
    try:
        while True:
            try:
                current_lines = server.get_output()
                if current_lines:
                    # Calculate delta
                    overlap = 0
                    max_overlap = min(len(last_buffer), len(current_lines))
                    for k in range(max_overlap, 0, -1):
                        if last_buffer[-k:] == current_lines[:k]:
                            overlap = k
                            break
                    
                    new_lines = current_lines[overlap:]
                    if new_lines:
                        await ws.send_json({"lines": new_lines, "is_delta": True})
                        last_buffer = list(current_lines)
                
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
    previous_lines = []
    while True:
        try:
            lines = server.get_output()
            if lines:
                # Process true delta between snapshots so repeated identical lines
                # (e.g. same chat command twice) are not dropped.
                overlap = 0
                max_overlap = min(len(previous_lines), len(lines))
                for k in range(max_overlap, -1, -1):
                    if previous_lines[-k:] == lines[:k]:
                        overlap = k
                        break
                new_lines = lines[overlap:]
                previous_lines = list(lines)

                for new_line in new_lines:
                    if not new_line:
                        continue
                    
                    # Get server name for server-specific AI
                    server_name = None
                    if server.current_profile:
                        server_name = os.path.basename(server.current_profile)
                    
                    autonomous_response = ai_engine.mc_ai.process_console_line(new_line)
                    if autonomous_response:
                        ai_msg = f"[Ava] {autonomous_response}"
                        server.add_output_line(ai_msg)
                        command = f'tellraw @a [{{"text":"[{ai_engine.mc_ai.ai_name}] ","color":"light_purple"}},{{"text":"{autonomous_response}","color":"white"}}]'
                        server.send_command(command)
                    
                    chat_match = re.search(r'(?:\[.*?\]\s*)?<([^>]+)> (.+)', new_line)
                    if chat_match:
                        player = chat_match.group(1)
                        message = chat_match.group(2).strip()
                        
                        result = ai_engine.mc_ai.process_message(message, player, server_name)
                        
                        print(f"[AI] Player: {player}, Mode: {ai_engine.mc_ai.mode}, Enabled: {ai_engine.mc_ai.is_enabled}")
                        if result:
                            print(f"[AI] Intent: {result.get('intent')}, Command: {result.get('command')}, Executed: {result.get('executed')}")
                        
                        if result and result.get("response"):
                            commands_preview = result.get("commands") or ([result.get("command")] if result.get("command") else [])
                            has_locate_token = any(
                                isinstance(c, str) and (c.startswith("LOCATE:") or c.startswith("LOCATE_TP:"))
                                for c in commands_preview
                            )
                            # Avoid duplicate/contradictory chatter for locate; we'll send a clean result after command execution.
                            if has_locate_token:
                                response = None
                            else:
                                response = result["response"]
                                try:
                                    response = ai_engine.mc_ai.response_engine.naturalize_for_chat(
                                        response, player, result.get("intent")
                                    )
                                except Exception:
                                    pass
                            if response and len(response) > 150:
                                response = response[:150] + "..."
                            # Log AI response to console
                            if response:
                                ai_msg = f"[Ava -> {player}] {response}"
                                server.add_output_line(ai_msg)
                                command = f'tellraw {player} [{{"text":"[{ai_engine.mc_ai.ai_name}] ","color":"light_purple"}},{{"text":"{response}","color":"white"}}]'
                                server.send_command(command)
                        
                        if result:
                            commands_to_run = result.get("commands") or ([result.get("command")] if result.get("command") else [])
                            if not commands_to_run:
                                commands_to_run = _build_tp_fallback_commands(message)
                            for cmd in commands_to_run:
                                print(f"[AI] Executing command: {cmd}")
                            _execute_ai_commands(commands_to_run, player)
            await asyncio.sleep(0.5)
        except Exception:
            await asyncio.sleep(0.5)

@app.on_event("startup")
async def startup():
    backup_manager.start_scheduler(lambda: os.path.basename(server.current_profile) if server.current_profile else None)
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
    return backup_manager.create_backup(profile, backup_type="full_server", providers=["google_drive"], source="legacy")

@app.get("/backup/list")
def list_backups(profile: str = None):
    return backup_manager.list_backups(profile)

@app.post("/backup/create")
async def create_backup_advanced(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    profile = data.get("profile")
    backup_name = data.get("backup_name")
    backup_type = data.get("backup_type", "full_server")
    providers = data.get("providers", ["google_drive"])
    return backup_manager.create_backup(
        profile=profile,
        backup_name=backup_name,
        backup_type=backup_type,
        providers=providers,
        source="manual"
    )

@app.post("/backup/restore")
def restore_backup(request: Request):
    return {"success": True, "message": "Restore functionality requires Google Drive integration"}

@app.get("/backup/settings")
def get_backup_settings(profile: str):
    return backup_manager.get_settings(profile)

@app.post("/backup/settings")
async def save_backup_settings(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    profile = data.get("profile")
    return backup_manager.update_settings(profile, data)

@app.get("/backup/providers/status")
def backup_provider_status(providers: str = ""):
    provider_list = [p.strip() for p in providers.split(",") if p.strip()]
    return backup_manager.get_provider_connection_status(provider_list)

@app.get("/backup/providers/auth-url")
def backup_provider_auth_url(provider: str):
    return backup_manager.get_provider_auth_url(provider)

@app.get("/backup/providers/config")
def backup_provider_config(provider: str):
    return backup_manager.get_provider_oauth_config(provider)

@app.post("/backup/providers/config")
async def backup_provider_config_save(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    provider = data.get("provider")
    return backup_manager.set_provider_oauth_config(provider, data)

@app.get("/backup/oauth/callback/{provider}")
def backup_oauth_callback(provider: str, code: str = None, state: str = None, error: str = None):
    result = backup_manager.handle_oauth_callback(provider, code, state, error)
    if result.get("success"):
        html = f"""
        <html><body style='font-family:Arial,sans-serif;background:#0b0b0f;color:#fff;padding:24px;'>
        <h2>Cloud Login Connected</h2>
        <p>{provider} is now connected. You can close this tab and return to MC Overseer.</p>
        </body></html>
        """
        return HTMLResponse(content=html, status_code=200)
    msg = result.get("error", "OAuth login failed")
    html = f"""
    <html><body style='font-family:Arial,sans-serif;background:#0b0b0f;color:#fff;padding:24px;'>
    <h2>Cloud Login Failed</h2>
    <p>{msg}</p>
    <p>Check provider client id/secret and redirect URI env vars, then try again.</p>
    </body></html>
    """
    return HTMLResponse(content=html, status_code=400)

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
