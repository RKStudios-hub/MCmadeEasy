import subprocess
import os
import threading
import time
import re
import socket
import json

JAVA_PATH = r"C:\Users\hrupe\AppData\Local\Programs\Eclipse Adoptium\jdk-17.0.17.10-hotspot\bin\java.exe"

class ServerManager:
    def __init__(self):
        self.process = None
        self.current_profile = self._load_saved_profile()
        self.current_ram = None
        self.output_lines = []
        self._reading = False
        self._reader_thread = None
        # Cache for player list to prevent spam
        self._players_cache = []
        self._players_cache_time = 0
        self._players_cache_ttl = 5  # Cache for 5 seconds
        self._query_lock = threading.Lock()
    
    def _load_saved_profile(self):
        """Load the saved profile path from file"""
        try:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            config_path = os.path.join(data_dir, "current_profile.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    data = json.load(f)
                    return data.get("path")
        except:
            pass
        return None

    def is_running(self):
        return self.process is not None and self.process.poll() is None

    def start(self, profile_path, ram="4G", software="paper"):
        if self.is_running():
            return False, "Server already running"

        jar_path = os.path.join(profile_path, "server.jar")
        if not os.path.exists(jar_path):
            return False, "No server.jar found. Download server software first."

        eula_path = os.path.join(profile_path, "eula.txt")
        if not os.path.exists(eula_path):
            with open(eula_path, "w") as f:
                f.write("eula=true\n")

        ram_max = ram
        ram_min = "1G" if ram in ["2G", "4G"] else "2G"
        
        # Handle different server software
        if software in ["forge", "neoforge"]:
            # Find the forge version dynamically from the libraries folder
            forge_dir = "net/minecraftforge/forge" if software == "forge" else "net/neoforged"
            libraries_forge_path = os.path.join(profile_path, "libraries", forge_dir)
            
            forge_version = None
            if os.path.exists(libraries_forge_path):
                # Find the version folder (e.g., 1.20.1-47.4.10)
                for item in os.listdir(libraries_forge_path):
                    item_path = os.path.join(libraries_forge_path, item)
                    if os.path.isdir(item_path):
                        forge_version = item
                        break
            
            if not forge_version:
                # Fallback to hardcoded version
                forge_version = "1.20.1-47.4.10" if software == "forge" else "1.20.1-47.4.10"
            
            # Forge command with @args files
            win_args_path = os.path.join(profile_path, "libraries", forge_dir, forge_version, "win_args.txt")
            
            if os.path.exists(win_args_path):
                # Use the @args approach for Forge
                cmd = [
                    JAVA_PATH,
                    f"-Xmx{ram_max}",
                    f"-Xms{ram_min}"
                ]
                
                # Check for user_jvm_args.txt
                user_jvm_args_path = os.path.join(profile_path, "user_jvm_args.txt")
                if os.path.exists(user_jvm_args_path):
                    cmd.append(f"@{user_jvm_args_path}")
                
                cmd.append(f"@{win_args_path}")
                cmd.append("nogui")
            else:
                # Fallback: try running with -jar
                cmd = [
                    JAVA_PATH,
                    f"-Xmx{ram_max}",
                    f"-Xms{ram_min}",
                    "-jar",
                    "server.jar",
                    "nogui"
                ]
        else:
            cmd = [
                JAVA_PATH,
                f"-Xmx{ram_max}",
                f"-Xms{ram_min}",
                "-jar",
                "server.jar",
                "nogui"
            ]
        
        self.process = subprocess.Popen(
            cmd,
            cwd=profile_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        self.current_profile = profile_path
        self.current_ram = ram
        
        # Save current profile to file so we can read it when server is offline
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "current_profile.json"), "w") as f:
            json.dump({"path": profile_path}, f)
        
        self._reading = True
        self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self._reader_thread.start()

        return True, "Server started"

    def _read_output(self):
        while self._reading and self.process:
            try:
                line = self.process.stdout.readline()
                if line:
                    # Strip ANSI color codes - more comprehensive pattern
                    import re
                    # Handle various ANSI escape sequences
                    clean_line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line.strip())
                    clean_line = re.sub(r'\x1b\]\d+;[^\x07]*\x07', '', clean_line)  # OSC sequences
                    clean_line = re.sub(r'\x1b\[?[\d;]*[JKmsu]', '', clean_line)  # Other CSI sequences
                    self.output_lines.append(clean_line)
                    if len(self.output_lines) > 1000:
                        self.output_lines = self.output_lines[-500:]
            except Exception:
                break

    def stop(self):
        if not self.is_running():
            return False, "No server running"

        try:
            self.process.stdin.write("stop\n")
            self.process.stdin.flush()
            self.process.wait(timeout=30)
        except Exception:
            self.process.kill()

        self.process = None
        self._reading = False
        # Clear player cache
        self._players_cache = []
        self._players_cache_time = 0
        # Clear console output
        self.output_lines = []
        return True, "Server stopped"

    def clear_output(self):
        """Clear console output history"""
        self.output_lines = []

    def send_command(self, cmd):
        if not self.is_running():
            return False, "No server running"

        try:
            # Strip leading slash for console commands (Paper expects no leading /)
            cmd_to_send = cmd.lstrip('/')
            self.process.stdin.write(cmd_to_send + "\n")
            self.process.stdin.flush()
            return True, "Command sent"
        except Exception as e:
            return False, str(e)

    def get_output(self):
        return self.output_lines[-100:]
    
    def add_output_line(self, line):
        """Add a custom line to output (for AI responses)"""
        self.output_lines.append(line.strip())
        if len(self.output_lines) > 1000:
            self.output_lines = self.output_lines[-500:]

    def get_status(self):
        if self.is_running():
            return "running"
        return "stopped"
    
    def get_player_coords(self, player_name):
        """Get player coordinates"""
        if not self.is_running():
            return None
        self.send_command(f"execute at {player_name} run data get entity {player_name} Pos")
        time.sleep(0.5)
        # Get from recent output
        for line in reversed(self.output_lines[-20:]):
            if player_name in line and "Pos" in line:
                return line
        return None

    def _query_entity_data(self, player_name, path, timeout=1.0):
        if not self.is_running():
            return None
        
        with self._query_lock:
            # Send the command and wait a bit
            start_idx = len(self.output_lines)
            self.send_command(f"data get entity {player_name} {path}")
            
            deadline = time.time() + timeout
            checked_idx = start_idx
            while time.time() < deadline:
                time.sleep(0.05)
                new_lines = self.output_lines[checked_idx:]
                if new_lines:
                    for line in new_lines:
                        clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                        low = clean_line.lower()
                        if player_name.lower() in low and 'entity data' in low:
                            return clean_line
                        if player_name.lower() in low and path.lower() in low:
                            return clean_line
                    checked_idx = len(self.output_lines)
            
            # Fallback: search forward from start_idx for the first matching entity data line
            for line in self.output_lines[start_idx:]:
                clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                low = clean_line.lower()
                if player_name.lower() in low and 'entity data' in low:
                    return clean_line
            
            return None

    def _parse_entity_data(self, line):
        if not line:
            return None
        match = re.search(r"entity data:\s*(.*)$", line)
        if not match:
            return None
        return match.group(1).strip()

    def _parse_pos(self, data):
        if not data:
            return None
        match = re.search(r"\[([^\]]+)\]", data)
        if not match:
            return None
        parts = [p.strip().rstrip('dD') for p in match.group(1).split(",")]
        if len(parts) != 3:
            return None
        try:
            return {"x": float(parts[0]), "y": float(parts[1]), "z": float(parts[2])}
        except Exception:
            return None

    def _parse_gamemode(self, data):
        if not data:
            return None
        match = re.search(r"(-?\d+)", data)
        if not match:
            return None
        try:
            val = int(match.group(1))
        except Exception:
            return None
        return {0: "survival", 1: "creative", 2: "adventure", 3: "spectator"}.get(val, "unknown")

    def _parse_inventory(self, data):
        if not data:
            return []
        items = []

        for chunk in self._split_nbt_list(data):
            slot_match = re.search(r"Slot:\s*(-?\d+)b?", chunk)
            id_match = re.search(r'id:\s*"([^"]+)"', chunk)
            count_match = re.search(r"Count:\s*(\d+)b?", chunk)
            if id_match and count_match and slot_match:
                name = id_match.group(1).replace("minecraft:", "")
                items.append({
                    "slot": int(slot_match.group(1)),
                    "item": name,
                    "count": int(count_match.group(1))
                })

        if items:
            return items

        # Fallback: Simple id/count pairs without slot info
        pattern2 = r'id:\s*"([^"]+)",\s*Count:\s*(\d+)b?'
        matches = re.findall(pattern2, data)
        if matches:
            counts = {}
            for item_id, count in matches:
                name = item_id.replace("minecraft:", "")
                counts[name] = counts.get(name, 0) + int(count)
            slot = 0
            for k, v in counts.items():
                items.append({"slot": slot, "item": k, "count": v})
                slot += 1
            return items

        return []

    def _parse_inventory_full(self, data):
        """Parse full inventory with slot information - uses _parse_inventory"""
        if not data:
            return []
        return self._parse_inventory(data)

    def _parse_item_list(self, data):
        """Parse a list of item compounds without Slot fields (e.g., ArmorItems/Offhand)."""
        if not data:
            return []
        items = []
        for chunk in self._split_nbt_list(data):
            id_match = re.search(r'id:\s*"([^"]+)"', chunk)
            count_match = re.search(r"Count:\s*(\d+)b?", chunk)
            if not id_match:
                items.append(None)
                continue
            name = id_match.group(1).replace("minecraft:", "")
            count = int(count_match.group(1)) if count_match else 1
            items.append({"item": name, "count": count})
        return items

    def _split_nbt_list(self, data):
        """Split a top-level NBT list into item chunks without being confused by nested braces."""
        if not data:
            return []
        start = data.find('[')
        end = data.rfind(']')
        if start == -1 or end == -1 or end <= start:
            return [data]
        inner = data[start + 1:end]
        chunks = []
        buf = []
        depth = 0
        i = 0
        while i < len(inner):
            ch = inner[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth = max(0, depth - 1)
            if ch == ',' and depth == 0:
                chunk = ''.join(buf).strip()
                if chunk:
                    chunks.append(chunk)
                buf = []
                i += 1
                continue
            buf.append(ch)
            i += 1
        tail = ''.join(buf).strip()
        if tail:
            chunks.append(tail)
        return chunks

    def get_player_details(self, player_name):
        if not self.is_running():
            return None
        pos_line = self._query_entity_data(player_name, "Pos")
        gm_line = (
            self._query_entity_data(player_name, "playerGameType")
            or self._query_entity_data(player_name, "gameType")
            or self._query_entity_data(player_name, "PlayerGameType")
        )
        inv_line = self._query_entity_data(player_name, "Inventory")
        armor_line = self._query_entity_data(player_name, "ArmorItems")
        hand_line = (
            self._query_entity_data(player_name, "HandItems")
            or self._query_entity_data(player_name, "HandItem")
        )
        offhand_line = (
            self._query_entity_data(player_name, "Offhand")
            or self._query_entity_data(player_name, "OffhandItems")
            or self._query_entity_data(player_name, "OffHand")
        )
        
        # Get additional stats
        health_line = self._query_entity_data(player_name, "Health", timeout=0.6)
        food_line = self._query_entity_data(player_name, "foodLevel", timeout=0.6)
        xp_line = self._query_entity_data(player_name, "xpLevel", timeout=0.6)
        xp_total_line = self._query_entity_data(player_name, "totalExperience", timeout=0.6)

        pos = self._parse_pos(self._parse_entity_data(pos_line))
        gamemode = self._parse_gamemode(self._parse_entity_data(gm_line))
        inventory = self._parse_inventory_full(self._parse_entity_data(inv_line))

        # Some versions store offhand in slot -106 inside Inventory
        for item in inventory:
            if item.get("slot") == -106:
                inventory.append({"slot": 40, "item": item.get("item"), "count": item.get("count", 1)})
                break
        
        # Parse health
        health = None
        if health_line:
            health_match = re.search(r"(\d+\.?\d*)f?", self._parse_entity_data(health_line) or "")
            if health_match:
                health = float(health_match.group(1))
        
        # Parse food/hunger
        hunger = None
        if food_line:
            hunger_match = re.search(r"(\d+)", self._parse_entity_data(food_line) or "")
            if hunger_match:
                hunger = int(hunger_match.group(1))
        
        # Parse XP level
        xp_level = None
        if xp_line:
            xp_match = re.search(r"(\d+)", self._parse_entity_data(xp_line) or "")
            if xp_match:
                xp_level = int(xp_match.group(1))

        return {
            "name": player_name,
            "coords": pos,
            "gamemode": gamemode or "unknown",
            "inventory": inventory,
            "health": health,
            "hunger": hunger,
            "xp_level": xp_level
        }

    def get_player_inventory_fast(self, player_name):
        """Fast inventory fetch: only query Inventory and map offhand slot -106."""
        if not self.is_running():
            return None
        inv_line = self._query_entity_data(player_name, "Inventory", timeout=0.8)
        inventory = self._parse_inventory_full(self._parse_entity_data(inv_line))
        for item in inventory:
            if item.get("slot") == -106:
                inventory.append({"slot": 40, "item": item.get("item"), "count": item.get("count", 1)})
                break
        return {
            "name": player_name,
            "inventory": inventory,
            "gamemode": None,
            "health": None,
            "hunger": None,
            "xp_level": None,
            "coords": None
        }

    def get_players_details(self, limit: int = 0):
        """Get details for currently online players with basic stats"""
        stats = self.get_stats()
        players = stats.get("players", [])
        
        # Ensure players is always a list
        if not isinstance(players, list):
            players = []
        
        details = []
        max_players = len(players) if not limit or limit <= 0 else min(limit, len(players))
        for name in players[:max_players]:
            if not isinstance(name, str):
                continue
            try:
                pos_line = self._query_entity_data(name, "Pos")
                gm_line = self._query_entity_data(name, "playerGameType")
                if not gm_line:
                    gm_line = self._query_entity_data(name, "gameType")
                health_line = self._query_entity_data(name, "Health")
                food_line = self._query_entity_data(name, "foodLevel")
                xp_line = self._query_entity_data(name, "xpLevel")
                
                pos = self._parse_pos(self._parse_entity_data(pos_line))
                gm_data = self._parse_entity_data(gm_line) if gm_line else ""
                gamemode = self._parse_gamemode(gm_data)
                
                # Parse health
                health = None
                if health_line:
                    health_data = self._parse_entity_data(health_line) or ""
                    health_match = re.search(r"(\d+\.?\d*)f?", health_data)
                    if health_match:
                        health = float(health_match.group(1))
                
                # Parse food/hunger
                hunger = None
                if food_line:
                    food_data = self._parse_entity_data(food_line) or ""
                    hunger_match = re.search(r"(\d+)", food_data)
                    if hunger_match:
                        hunger = int(hunger_match.group(1))
                
                # Parse XP level
                xp_level = None
                if xp_line:
                    xp_data = self._parse_entity_data(xp_line) or ""
                    xp_match = re.search(r"(\d+)", xp_data)
                    if xp_match:
                        xp_level = int(xp_match.group(1))
                
                details.append({
                    "name": name,
                    "coords": pos,
                    "gamemode": gamemode or "survival",
                    "health": health,
                    "hunger": hunger,
                    "xp_level": xp_level
                })
            except Exception as e:
                # If anything fails, just add the player name
                details.append({"name": name})
        
        return details
    
    def get_nearby_entities(self, player_name, distance=30):
        """Get nearby entities"""
        if not self.is_running():
            return None
        self.send_command(f"execute at {player_name} run testfor @e[distance=..{distance}]")
        time.sleep(0.5)
        for line in reversed(self.output_lines[-20:]):
            if "entities" in line.lower() or "@e" in line:
                return line
        return None
    
    def locate_structure(self, player_name, structure_type):
        """Locate nearest structure"""
        if not self.is_running():
            return None
        requested = (structure_type or "").strip()
        requested_lower = requested.lower()
        dimension = None

        # Build candidate structure ids in order of preference.
        # Some MC versions reject minecraft:village and require biome-specific village structures.
        if requested_lower in ["village", "minecraft:village"]:
            candidates = [
                "#village",
                "minecraft:village_plains",
                "minecraft:village_desert",
                "minecraft:village_savanna",
                "minecraft:village_snowy",
                "minecraft:village_taiga",
            ]
        elif requested_lower in ["ocean_monument", "minecraft:ocean_monument", "monument", "minecraft:monument"]:
            candidates = [
                "minecraft:ocean_monument",
                "minecraft:monument",
            ]
        else:
            if requested.startswith("#"):
                candidates = [requested]
            elif ":" in requested:
                candidates = [requested]
            else:
                candidates = [f"minecraft:{requested}"]

        # Structures that only exist in specific dimensions.
        if requested_lower in ["end_city", "minecraft:end_city", "endcity"]:
            dimension = "minecraft:the_end"
        elif requested_lower in ["fortress", "minecraft:fortress", "bastion", "minecraft:bastion"]:
            dimension = "minecraft:the_nether"

        def _run_and_wait(command, timeout=8.0):
            start_idx = len(self.output_lines)
            self.send_command(command)
            deadline = time.time() + timeout
            checked_idx = start_idx
            while time.time() < deadline:
                time.sleep(0.15)
                new_lines = self.output_lines[checked_idx:]
                if not new_lines:
                    continue
                checked_idx = len(self.output_lines)
                for line in new_lines:
                    low = line.lower()
                    if "[ava" in low or "ava ->" in low:
                        continue
                    if "entity data" in low or "found no elements matching" in low:
                        continue
                    if "located" in low or "nearest minecraft:" in low:
                        return line
                    if (
                        "could not" in low
                        or "unable" in low
                        or "no structures" in low
                        or "no such" in low
                        or "no entity was found" in low
                        or "incorrect argument for command" in low
                        or "unknown or incomplete command" in low
                    ):
                        return line
                    if requested_lower and requested_lower in low and (" at " in low or "(" in low):
                        return line
            return None

        for candidate in candidates:
            # Primary: anchor search around player's current position.
            if dimension:
                anchored_cmd = f"execute in {dimension} run locate structure {candidate}"
            else:
                anchored_cmd = f"execute at {player_name} run locate structure {candidate}"

            anchored = _run_and_wait(anchored_cmd, timeout=12.0)
            if anchored and "there is no structure with type" not in anchored.lower():
                return anchored

            # Fallback: run locate directly in case anchored command feedback was suppressed.
            fallback = _run_and_wait(f"locate structure {candidate}", timeout=10.0)
            if fallback and "there is no structure with type" not in fallback.lower():
                return fallback

        return None
    
    def get_stats(self):
        """Get server stats"""
        if not self.is_running():
            return {"running": False}
        
        import psutil
        try:
            proc = psutil.Process(self.process.pid)
            cpu = proc.cpu_percent(interval=0.1)
            mem = proc.memory_info().rss / (1024**3)
        except:
            cpu = 0
            mem = 0
        
        # Try to get player list from server using 'list' command (more reliable)
        players = self._get_online_players_from_server()
        
        return {
            "running": True,
            "cpu": round(cpu, 1),
            "memory": round(mem, 2),
            "max_ram": self._parse_ram(self.current_ram) if self.current_ram else 4,
            "players": players
        }
    
    def _get_server_port(self):
        """Get the server port from server.properties"""
        if not self.current_profile:
            return 25565
        
        props_path = os.path.join(self.current_profile, "server.properties")
        if os.path.exists(props_path):
            try:
                with open(props_path, "r") as f:
                    for line in f:
                        if line.startswith("server-port="):
                            port = int(line.split("=")[1].strip())
                            return port
            except:
                pass
        return 25565
    
    def _get_online_players_from_server(self):
        """Get list of online players using Query protocol (like Aternos)"""
        if not self.is_running():
            return []
        
        # Check cache first
        current_time = time.time()
        if current_time - self._players_cache_time < self._players_cache_ttl and self._players_cache:
            return self._players_cache
        
        port = self._get_server_port()
        
        JavaServer = None
        try:
            from mcstatus import JavaServer
        except ImportError:
            pass
        
        if JavaServer:
            try:
                # Try to query the server
                server = JavaServer.lookup(f"localhost:{port}")
                
                status = server.status()
                players = [p.name for p in status.players.sample] if status.players.sample else []
                
                # Update cache
                self._players_cache = players
                self._players_cache_time = current_time
                return players
            except Exception as e:
                # Query failed, try fallback
                pass
        else:
            # mcstatus not available
            pass
        
        # Fallback 1: Try basic TCP ping
        try:
            players = self._query_server_basic(port)
            if players is not None:
                self._players_cache = players
                self._players_cache_time = current_time
                return players
        except:
            pass
        
        # Fallback 2: Try parsing from console
        players = self._parse_players_from_console()
        if players:
            self._players_cache = players
            self._players_cache_time = current_time
            return players
        
        return []
    
    def _parse_players_from_console(self):
        """Parse player list from console output"""
        players = []
        for line in self.output_lines[-50:]:
            if "joined the game" in line.lower():
                name = line.split("joined")[0].split("]")[-1].strip()
                name = re.sub(r'\x1b\[[0-9;]*m', '', name)
                if name and name not in players:
                    players.append(name)
            elif "left the game" in line.lower():
                name = line.split("left")[0].split("]")[-1].strip()
                name = re.sub(r'\x1b\[[0-9;]*m', '', name)
                if name in players:
                    players.remove(name)
        return players
    
    def _query_server_basic(self, port=25565):
        """Basic server query using raw socket"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(("localhost", port))
            
            # Send handshake + status request
            # Handshake packet
            handshake = b'\x00\x00\x00\x00\x17\x00\x00\x00\x01localhost\x00\xbf\x00\x00\x00\x00\x00'
            sock.send(handshake)
            
            # Status request
            sock.send(b'\x00\x00\x00\x00')
            
            # Read response
            data = sock.recv(2048)
            sock.close()
            
            if data:
                # Try to parse JSON from response
                import json
                # Find JSON in response
                start = data.find(b'{')
                if start != -1:
                    resp = json.loads(data[start:].decode('utf-8', errors='ignore'))
                    if 'players' in resp and 'sample' in resp['players']:
                        return [p['name'] for p in resp['players']['sample']]
        except:
            pass
        
        return None
    
    def _parse_ram(self, ram_str):
        """Parse RAM string like '4G' to numeric GB"""
        if not ram_str:
            return 4
        try:
            return int(ram_str.replace("G", "").replace("M", ""))
        except:
            return 4
