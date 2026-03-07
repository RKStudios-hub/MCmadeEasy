import json
import os
import re
import time
import zipfile


BASE_COMMANDS = {
    "help", "list", "say", "tell", "msg", "me", "tellraw",
    "title", "time", "weather", "gamerule", "difficulty", "gamemode",
    "tp", "teleport", "spawnpoint", "setworldspawn", "give", "clear",
    "effect", "enchant", "xp", "experience", "kill", "summon", "data",
    "setblock", "fill", "clone", "replaceitem", "execute", "function",
    "scoreboard", "tag", "team", "particle", "playsound", "stopsound",
    "advancement", "ban", "pardon", "kick", "op", "deop", "whitelist",
    "save-all", "save-on", "save-off", "locate", "plugins", "version",
}


class CommandCatalog:
    def __init__(self):
        self._cache = {
            "commands": set(BASE_COMMANDS),
            "meta": {"profile_path": None, "sources": []},
            "timestamp": 0,
            "fingerprint": None,
        }
        self._ttl = 5

    def get_commands(self):
        self._refresh_if_needed()
        return sorted(self._cache["commands"])

    def get_meta(self):
        self._refresh_if_needed()
        return self._cache["meta"]

    def suggest(self, message, limit=6):
        self._refresh_if_needed()
        tokens = re.findall(r"[a-z0-9:_-]+", (message or "").lower())
        if not tokens:
            return []
        scored = []
        for cmd in self._cache["commands"]:
            score = 0
            if cmd in tokens:
                score += 4
            base = cmd.split(":")[-1]
            if base in tokens:
                score += 3
            for token in tokens:
                if token and (token in cmd or cmd.startswith(token)):
                    score += 1
            if score > 0:
                scored.append((score, cmd))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [name for _, name in scored[:limit]]

    def build_prompt_hint(self, limit=50):
        commands = self.get_commands()[:limit]
        if not commands:
            return ""
        return ", ".join(commands)

    def _refresh_if_needed(self):
        now = time.time()
        profile_path = self._get_current_profile_path()
        fingerprint = self._fingerprint(profile_path)
        if (
            self._cache["fingerprint"] == fingerprint
            and now - self._cache["timestamp"] < self._ttl
        ):
            return

        commands = set(BASE_COMMANDS)
        sources = []

        if profile_path:
            commands_txt = os.path.join(profile_path, "commands.txt")
            for cmd in self._load_from_commands_txt(commands_txt):
                commands.add(cmd)
            if os.path.exists(commands_txt):
                sources.append("commands.txt")

            plugins_dir = os.path.join(profile_path, "plugins")
            plugin_commands = self._load_from_plugin_jars(plugins_dir)
            if plugin_commands:
                commands.update(plugin_commands)
                sources.append("plugin_jars")

            mods_dir = os.path.join(profile_path, "mods")
            mod_aliases = self._load_mod_aliases(mods_dir)
            if mod_aliases:
                commands.update(mod_aliases)
                sources.append("mod_aliases")

        self._cache = {
            "commands": commands,
            "meta": {"profile_path": profile_path, "sources": sources},
            "timestamp": now,
            "fingerprint": fingerprint,
        }

    def _fingerprint(self, profile_path):
        if not profile_path:
            return None

        points = [os.path.join(profile_path, "commands.txt")]
        plugins_dir = os.path.join(profile_path, "plugins")
        mods_dir = os.path.join(profile_path, "mods")
        if os.path.isdir(plugins_dir):
            for name in os.listdir(plugins_dir):
                if name.lower().endswith(".jar"):
                    points.append(os.path.join(plugins_dir, name))
        if os.path.isdir(mods_dir):
            for name in os.listdir(mods_dir):
                if name.lower().endswith(".jar"):
                    points.append(os.path.join(mods_dir, name))

        stats = []
        for path in sorted(points):
            try:
                st = os.stat(path)
                stats.append((path, st.st_mtime, st.st_size))
            except OSError:
                continue
        return tuple(stats)

    def _load_from_commands_txt(self, commands_path):
        if not os.path.exists(commands_path):
            return []
        commands = []
        try:
            with open(commands_path, "r", encoding="utf-8") as f:
                for line in f:
                    raw = line.strip()
                    if not raw or raw.startswith("#") or raw.startswith("//"):
                        continue
                    cmd = self._extract_root_command(raw)
                    if cmd:
                        commands.append(cmd)
        except Exception:
            return []
        return commands

    def _load_from_plugin_jars(self, plugins_dir):
        if not os.path.isdir(plugins_dir):
            return []
        commands = set()
        for name in os.listdir(plugins_dir):
            if not name.lower().endswith(".jar"):
                continue
            jar_path = os.path.join(plugins_dir, name)
            try:
                with zipfile.ZipFile(jar_path, "r") as zf:
                    yml_name = None
                    for candidate in ("plugin.yml", "paper-plugin.yml"):
                        if candidate in zf.namelist():
                            yml_name = candidate
                            break
                    if not yml_name:
                        continue
                    text = zf.read(yml_name).decode("utf-8", errors="ignore")
                    commands.update(self._parse_plugin_yml_commands(text))
            except Exception:
                continue
        return sorted(commands)

    def _parse_plugin_yml_commands(self, yml_text):
        commands = set()
        in_commands = False
        commands_indent = None

        for line in yml_text.splitlines():
            raw = line.rstrip("\n")
            if not raw.strip() or raw.strip().startswith("#"):
                continue

            indent = len(raw) - len(raw.lstrip(" "))
            stripped = raw.strip()

            if re.match(r"^commands\s*:\s*$", stripped):
                in_commands = True
                commands_indent = indent
                continue

            if in_commands:
                if indent <= commands_indent:
                    in_commands = False
                    commands_indent = None
                    continue
                key_match = re.match(r"^([a-zA-Z0-9:_-]+)\s*:\s*$", stripped)
                if key_match:
                    commands.add(self._normalize_command_name(key_match.group(1)))
        return sorted(commands)

    def _load_mod_aliases(self, mods_dir):
        if not os.path.isdir(mods_dir):
            return []
        aliases = set()
        for name in os.listdir(mods_dir):
            if not name.lower().endswith(".jar"):
                continue
            stem = os.path.splitext(name)[0].lower()
            stem = re.sub(r"[%+]", "-", stem)
            stem = re.sub(r"[^a-z0-9._-]", "-", stem)
            parts = [p for p in re.split(r"[-_.]+", stem) if p and not p.isdigit()]
            if parts:
                aliases.add(parts[0])
        return sorted(aliases)

    def _extract_root_command(self, line):
        first = line.split()[0].lstrip("/")
        if not first:
            return None
        return self._normalize_command_name(first)

    def _normalize_command_name(self, command):
        cmd = command.strip().lower().lstrip("/")
        if ":" in cmd:
            cmd = cmd.split(":", 1)[1]
        return cmd

    def _get_current_profile_path(self):
        try:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            config_path = os.path.join(data_dir, "current_profile.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("path")
        except Exception:
            return None
        return None


command_catalog = CommandCatalog()
