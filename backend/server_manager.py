import subprocess
import os
import threading
import time

JAVA_PATH = r"C:\Users\hrupe\AppData\Local\Programs\Eclipse Adoptium\jdk-17.0.17.10-hotspot\bin\java.exe"

class ServerManager:
    def __init__(self):
        self.process = None
        self.current_profile = None
        self.output_lines = []
        self._reading = False
        self._reader_thread = None

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
        self.current_profile = None
        self._reading = False
        return True, "Server stopped"

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
        self.send_command(f"execute at {player_name} run locate {structure_type}")
        time.sleep(1)
        for line in reversed(self.output_lines[-20:]):
            if "Found" in line or "Located" in line:
                return line
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
        
        players = []
        for line in self.output_lines[-50:]:
            if "joined the game" in line.lower():
                name = line.split("joined")[0].split("]")[-1].strip()
                if name and name not in players:
                    players.append(name)
            elif "left the game" in line.lower():
                name = line.split("left")[0].split("]")[-1].strip()
                if name in players:
                    players.remove(name)
        
        return {
            "running": True,
            "cpu": round(cpu, 1),
            "memory": round(mem, 2),
            "players": players
        }
