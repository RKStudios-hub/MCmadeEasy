import re
import random

from core.gateway import gateway
from core.role_engine import role_engine
from core.memory_engine import memory_engine
from core.audit_logger import audit_logger

from ai.intent_engine import intent_engine
from ai.response_engine import response_engine
from ai.personality_engine import personality_engine
from ai.conversation_engine import conversation_engine

from engine.command_builder import command_builder
from engine.validator import validator, simulator
from engine.executor import executor

from world.world_intelligence import world_intelligence


class MC_AI:
    def __init__(self):
        self.gateway = gateway
        self.role_engine = role_engine
        self.memory = memory_engine
        self.audit = audit_logger
        
        self.intent_engine = intent_engine
        self.response_engine = response_engine
        self.personality_engine = personality_engine
        self.conversation_engine = conversation_engine
        
        self.command_builder = command_builder
        self.validator = validator
        self.simulator = simulator
        self.executor = executor
        
        self.world = world_intelligence
        
        self.enabled = True
        self.mode = "chat"
        self._load_config()
    
    def _load_config(self):
        config_path = "config.json"
        if hasattr(self.gateway, 'config'):
            self.enabled = self.gateway.enabled
            self.mode = self.gateway.mode
    
    def reload(self):
        self.gateway.reload()
        self.role_engine.reload()
        self.personality_engine.reload()
        self._load_config()
    
    @property
    def ai_name(self):
        return self.personality_engine.ai_name
    
    @property
    def is_enabled(self):
        return self.gateway.is_enabled()
    
    def process_message(self, message, player_name, server_name=None):
        if not self.is_enabled:
            return None
        
        if message.startswith('!'):
            return None
        
        player = self.memory.get_player(player_name, server_name)
        
        context = self.world.get_state()
        
        intent_result = self.intent_engine.parse(message, player_name, context)

        # Fallback: never drop obvious direct command phrasing like "tp me to stronghold".
        if intent_result.get("intent") in ["none", "unknown", "error"] and re.search(r"^\s*(tp|teleport)\s+me\b", message, re.IGNORECASE):
            intent_result = {
                "intent": "raw_command",
                "parameters": {"command": message.strip(), "target": "@a"},
                "confidence": 0.95,
                "source": "fallback_direct",
                "raw": message
            }
        
        should_execute = self._should_execute(intent_result, player_name)
        
        commands_executed = []
        response_text = ""
        
        # Handle multiple commands
        if intent_result.get("intent") == "multi" and should_execute:
            commands = intent_result.get("commands", [])
            for cmd_intent in commands:
                cmd = self._build_and_validate_command(cmd_intent, player_name)
                if not cmd:
                    continue
                if isinstance(cmd, list):
                    commands_executed.extend(cmd)
                else:
                    commands_executed.append(cmd)
        
        # Handle single command (original behavior) - skip scan intent
        elif should_execute and intent_result.get("intent") not in ["none", "unknown", "error", "scan"]:
            command_to_run = self._build_and_validate_command(intent_result, player_name)
            if command_to_run:
                if isinstance(command_to_run, list):
                    commands_executed.extend(command_to_run)
                else:
                    commands_executed.append(command_to_run)
        
        # Pass execution status to response generator
        if commands_executed:
            intent_result["executed"] = True
        intent_result["task_series"] = self._build_task_series(intent_result, commands_executed, player_name)
        
        # Set server_name on engines for server-specific memory/prompts
        self.response_engine.server_name = server_name
        self.conversation_engine.server_name = server_name
        
        response = self.conversation_engine.process_message(message, player_name, intent_result, context)
        
        return {
            "response": response,
            "command": commands_executed[0] if commands_executed else None,
            "commands": commands_executed,  # All executed commands
            "executed": len(commands_executed) > 0,
            "intent": intent_result,
            "player_role": self.role_engine.get_player_role(player_name)
        }
    
    def _should_execute(self, intent_result, player_name):
        if self.mode == "off":
            return False
        if self.mode == "chat":
            return False
        if self.mode == "suggest":
            return False
        
        if self.mode in ["auto-safe", "auto-admin"]:
            confidence = intent_result.get("confidence", 0)
            if confidence < 0.7:
                return False
        
        return self.role_engine.is_admin(player_name)
    
    def _build_and_validate_command(self, intent_result, player_name):
        intent = intent_result.get("intent")
        params = intent_result.get("parameters", {})
        
        params.setdefault("target", "@a")
        
        command = self.command_builder.build(intent, params)
        
        if not command:
            print(f"[AI] Command build failed for intent: {intent}")
            return None
        
        # Handle multiple commands (list)
        if isinstance(command, list):
            print(f"[AI] Building {len(command)} commands")
            commands_to_run = []
            for cmd in command:
                can_execute = self.role_engine.can_execute(player_name, intent, intent_result.get("confidence", 0.8))
                if can_execute:
                    success, msg = self.executor.execute(cmd, player_name, {
                        "intent": intent,
                        "confidence": intent_result.get("confidence", 0),
                        "original_message": intent_result.get("raw", ""),
                        "parameters": params
                    })
                    if success:
                        resolved = self.executor.get_last_resolved_command() or cmd
                        commands_to_run.append(resolved)
                        print(f"[AI] Executed: {resolved}")
            return commands_to_run if commands_to_run else None
        
        print(f"[AI] Built command: {command}")
        
        can_execute = self.role_engine.can_execute(player_name, intent, intent_result.get("confidence", 0.8))
        
        print(f"[AI] can_execute: {can_execute} for player {player_name} with intent {intent}")
        
        if not can_execute:
            return None
        
        success, msg = self.executor.execute(command, player_name, {
            "intent": intent,
            "original_message": intent_result.get("raw", ""),
            "confidence": intent_result.get("confidence", 0),
            "parameters": params
        })
        
        print(f"[AI] Execution result: {success}, {msg}")
        
        if success:
            return self.executor.get_last_resolved_command() or command
        
        return None
    
    def _build_task_series(self, intent_result, commands_executed, player_name):
        intent = intent_result.get("intent")
        if not intent or intent in ["none", "unknown", "error", "scan"]:
            return []
        steps = []
        if intent == "multi":
            for cmd in commands_executed:
                steps.append({"title": cmd, "status": "done"})
            return steps
        # Single intent
        command = commands_executed[0] if commands_executed else None
        if isinstance(command, str) and command.startswith("LOCATE_TP:"):
            parts = command.split(":", 2)
            structure = parts[1] if len(parts) > 1 else "structure"
            target = parts[2] if len(parts) > 2 else player_name
            steps.append({"title": f"Locate nearest {structure}", "status": "done" if commands_executed else "pending"})
            steps.append({"title": f"Teleport {target}", "status": "done" if commands_executed else "pending"})
        elif isinstance(command, str) and command.startswith("LOCATE:"):
            parts = command.split(":", 1)
            structure = parts[1] if len(parts) > 1 else "structure"
            steps.append({"title": f"Locate nearest {structure}", "status": "done" if commands_executed else "pending"})
        elif command:
            steps.append({"title": f"Execute {command}", "status": "done" if commands_executed else "pending"})
        else:
            steps.append({"title": f"Execute intent {intent}", "status": "pending"})
        return steps
    def process_console_line(self, line):
        if not self.is_enabled:
            return None
        
        if "joined the game" in line:
            player_match = re.search(r'([^\s]+) joined', line)
            if player_match:
                player = player_match.group(1)
                self.world.add_event("join", player)
                if self.conversation_engine.should_greet(player):
                    return self.conversation_engine.initiate("join", player, self.world.get_state())
        
        if "left the game" in line:
            player_match = re.search(r'([^\s]+) left', line)
            if player_match:
                player = player_match.group(1)
                self.world.add_event("leave", player)
        
        if "died" in line.lower():
            player_match = re.search(r'([^\s]+) died', line, re.IGNORECASE)
            if player_match:
                player = player_match.group(1)
                self.world.add_event("death", player)
                return self.conversation_engine.initiate("death", player, self.world.get_state())
        
        if "achievement" in line.lower() or "made the advancement" in line.lower():
            player_match = re.search(r'([^\s]+) has made the advancement', line)
            if player_match:
                player = player_match.group(1)
                self.world.add_event("advancement", player)
                return self.conversation_engine.initiate("achievement", player, self.world.get_state())
        
        if "time" in line.lower() and "set" in line.lower():
            time_match = re.search(r'time to (\d+)', line)
            if time_match:
                ticks = int(time_match.group(1))
                self.world.update_time(ticks)
        
        if "weather" in line.lower():
            if "clear" in line.lower():
                self.world.update_weather("clear")
            elif "rain" in line.lower():
                self.world.update_weather("rain")
            elif "thunder" in line.lower():
                self.world.update_weather("thunder")
        
        if self.mode in ["overseer", "auto-safe"]:
            return self._check_autonomous()
        
        return None
    
    def _check_autonomous(self):
        if random.random() > self.personality_engine.get_autonomous_chance():
            return None
        
        if not self.conversation_engine.can_initiate():
            return None
        
        active = self.conversation_engine.get_active_players()
        if not active:
            return None
        
        player = random.choice(active)
        
        if self.world.should_autonomous_trigger("night"):
            return self.conversation_engine.initiate("night", player, self.world.get_state())
        
        if self.world.should_autonomous_trigger("rain"):
            return self.conversation_engine.initiate("rain", player, self.world.get_state())
        
        if self.world.should_autonomous_trigger("lonely"):
            return self.conversation_engine.initiate("lonely", player, self.world.get_state())
        
        return None
    
    def update_player_list(self, players):
        self.world.update_player_list(players)
    
    def get_status(self):
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "ai_name": self.ai_name,
            "personality": self.personality_engine.get_personality(),
            "available_personalities": self.personality_engine.get_available_personalities()
        }
    
    def set_mode(self, mode):
        valid_modes = ["off", "chat", "suggest", "auto-safe", "auto-admin", "overseer"]
        if mode in valid_modes:
            self.mode = mode
            self.gateway.set_mode(mode)
            return True
        return False
    
    def toggle(self):
        self.enabled = self.gateway.toggle()
        return self.enabled


mc_ai = MC_AI()
