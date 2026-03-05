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
            # Forge/NeoForge - ensure valid runnable JAR
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
                    self.output_lines.append(line.strip())
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

    def _query_entity_data(self, player_name, path, timeout=2.0):
        if not self.is_running():
            return None
        
        # Send the command and wait a bit
        start_idx = len(self.output_lines)
        self.send_command(f"data get entity {player_name} {path}")
        
        # Wait a moment for the command to execute
        time.sleep(0.2)
        
        # Look through recent output for the data
        search_lines = self.output_lines[max(0, start_idx-10):]
        
        for line in reversed(search_lines):
            # Strip ANSI codes
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
            if player_name in clean_line and path.lower() in clean_line.lower():
                # Found the entity data
                return clean_line
        
        # If not found, try a second search with broader criteria
        for line in reversed(self.output_lines[-30:]):
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
            if 'entity data' in clean_line.lower() and path in clean_line:
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
        
        # Try multiple patterns to match inventory data
        # Pattern 1: Slot-based (newer Minecraft versions)
        pattern1 = r'Slot:(\d+)b,id:"([^"]+)",Count:(\d+)b'
        matches = re.findall(pattern1, data)
        if matches:
            for slot, item_id, count in matches:
                name = item_id.replace("minecraft:", "")
                items.append({
                    "slot": int(slot),
                    "item": name,
                    "count": int(count)
                })
            return items
        
        # Pattern 2: Simple id:count format (older or simpler output)
        pattern2 = r'id:"([^"]+)",Count:(\d+)b'
        matches = re.findall(pattern2, data)
        if matches:
            counts = {}
            for item_id, count in matches:
                name = item_id.replace("minecraft:", "")
                counts[name] = counts.get(name, 0) + int(count)
            # Add slot numbers
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
        
        # Get additional stats
        health_line = self._query_entity_data(player_name, "Health")
        food_line = self._query_entity_data(player_name, "foodLevel")
        xp_line = self._query_entity_data(player_name, "xpLevel")
        xp_total_line = self._query_entity_data(player_name, "totalExperience")

        pos = self._parse_pos(self._parse_entity_data(pos_line))
        gamemode = self._parse_gamemode(self._parse_entity_data(gm_line))
        inventory = self._parse_inventory_full(self._parse_entity_data(inv_line))
        
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

    def get_players_details(self):
        """Get details for currently online players with basic stats"""
        stats = self.get_stats()
        players = stats.get("players", [])
        
        # Ensure players is always a list
        if not isinstance(players, list):
            players = []
        
        # Only query detailed info for a limited number of players
        # to avoid console spam
        details = []
        for name in players[:5]:  # Limit to 5 players max
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
                
                pos = self._parse_pos(pos_line)
                gm_data = gm_line.replace("entity data: ", "") if gm_line else ""
                gamemode = self._parse_gamemode(gm_data)
                
                # Parse health
                health = None
                if health_line:
                    health_data = health_line.replace("entity data: ", "") if health_line else ""
                    health_match = re.search(r"(\d+\.?\d*)f?", health_data)
                    if health_match:
                        health = float(health_match.group(1))
                
                # Parse food/hunger
                hunger = None
                if food_line:
                    food_data = food_line.replace("entity data: ", "") if food_line else ""
                    hunger_match = re.search(r"(\d+)", food_data)
                    if hunger_match:
                        hunger = int(hunger_match.group(1))
                
                # Parse XP level
                xp_level = None
                if xp_line:
                    xp_data = xp_line.replace("entity data: ", "") if xp_line else ""
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
        commands = [
            f"execute at {player_name} run locate structure {structure_type}",
            f"execute at {player_name} run locate {structure_type}"
        ]
        for cmd in commands:
            self.send_command(cmd)
            time.sleep(0.2)
        deadline = time.time() + 4.5
        seen = set()
        while time.time() < deadline:
            lines = list(reversed(self.output_lines[-200:]))
            for line in lines:
                if line in seen:
                    continue
                seen.add(line)
                low = line.lower()
                if "found" in low or "located" in low:
                    return line
                if "could not" in low or "unable" in low or "no structures" in low or "no such" in low:
                    return line
            time.sleep(0.2)
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
