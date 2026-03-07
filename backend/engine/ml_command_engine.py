import json
import math
import os
import re
from typing import Dict, List, Optional

from engine.command_catalog import command_catalog


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return re.findall(r"[a-z0-9_:-]+", text.lower())


def _extract_root(command: str) -> str:
    if not command:
        return ""
    first = command.strip().split()[0].lstrip("/").lower()
    if ":" in first:
        # keep LOCATE:<x> style tokens untouched by returning full token marker
        if first.startswith("locate:") or first.startswith("locate_tp:"):
            return first
        first = first.split(":", 1)[1]
    return first


class MLCommandEngine:
    """
    Lightweight online learner:
    - Learns successful intent->command mappings.
    - Predicts command roots from intent/message features using cosine similarity.
    - Generates Minecraft-valid commands constrained by discovered command roots.
    """

    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.data_path = os.path.join(base_dir, "data", "ml_command_model.json")
        self.max_samples = 1000
        self.model = self._load_model()

    def generate(self, command: Optional[str], intent_data: Optional[dict], player_name: str) -> Optional[str]:
        intent_data = intent_data or {}
        if not intent_data:
            return command

        if command and self._is_special_token(command):
            return command

        # If we already have a command root, keep it unless malformed.
        if command:
            root = _extract_root(command)
            if root and self._is_allowed_root(root):
                return command

        predicted_root = self._predict_root(intent_data)
        if not predicted_root:
            return command

        generated = self._compose_from_root(predicted_root, intent_data, player_name)
        return generated or command

    def learn(self, intent_data: Optional[dict], command: Optional[str], success: bool):
        if not intent_data or not command or not success:
            return
        if self._is_special_token(command):
            return

        root = _extract_root(command)
        if not root:
            return

        features = self._features(intent_data)
        intent = (intent_data.get("intent") or "unknown").lower()

        self.model["samples"].append({
            "intent": intent,
            "command": command,
            "root": root,
            "features": features,
            "successes": 1
        })
        if len(self.model["samples"]) > self.max_samples:
            self.model["samples"] = self.model["samples"][-self.max_samples:]

        by_intent = self.model["by_intent"].setdefault(intent, {})
        by_intent[root] = by_intent.get(root, 0) + 1
        self._save_model()

    def _predict_root(self, intent_data: dict) -> Optional[str]:
        allowed = set(command_catalog.get_commands())
        if not allowed:
            return None

        intent = (intent_data.get("intent") or "unknown").lower()
        by_intent = self.model["by_intent"].get(intent, {})
        if by_intent:
            sorted_roots = sorted(by_intent.items(), key=lambda kv: kv[1], reverse=True)
            for root, _ in sorted_roots:
                if root in allowed:
                    return root

        features = self._features(intent_data)
        if not features:
            return None

        best_root = None
        best_score = 0.0
        for sample in self.model["samples"]:
            root = sample.get("root", "")
            if root not in allowed:
                continue
            score = self._cosine(features, sample.get("features", {}))
            score *= max(1, int(sample.get("successes", 1)))
            if score > best_score:
                best_score = score
                best_root = root

        if best_root and best_score > 0.20:
            return best_root

        # lexical hint from message tokens
        msg_tokens = set(_tokenize(intent_data.get("original_message", "")))
        for token in msg_tokens:
            if token in allowed:
                return token

        return None

    def _compose_from_root(self, root: str, intent_data: dict, player_name: str) -> Optional[str]:
        params = intent_data.get("parameters", {}) or {}
        msg = (intent_data.get("original_message", "") or "").lower()
        target = params.get("target", "@a")

        if root == "time":
            val = params.get("value")
            if not val:
                for candidate in ("day", "night", "noon", "midnight", "sunset", "sunrise"):
                    if candidate in msg:
                        val = candidate
                        break
            if not val:
                val = "day"
            return f"time set {val}"

        if root == "weather":
            val = params.get("type")
            if not val:
                for candidate in ("clear", "rain", "thunder"):
                    if candidate in msg:
                        val = candidate
                        break
            return f"weather {val or 'clear'}"

        if root in ("tp", "teleport"):
            destination = params.get("destination")
            if destination:
                return f"tp {target} {destination}"
            return f"tp {target} {player_name}"

        if root == "gamemode":
            mode = params.get("mode", "survival")
            return f"gamemode {mode} {target}"

        if root == "give":
            item = params.get("item")
            if item:
                amount = params.get("amount", 1)
                return f"give {target} {item} {amount}"
            return None

        if root == "locate":
            struct = params.get("structure") or params.get("destination")
            if struct:
                return f"locate structure {struct}"
            return "locate structure village"

        # Generic fallback
        if " " in root:
            return root
        return root

    def _features(self, intent_data: dict) -> Dict[str, float]:
        features: Dict[str, float] = {}
        intent = (intent_data.get("intent") or "unknown").lower()
        features[f"intent:{intent}"] = 2.0

        original = intent_data.get("original_message", "")
        for token in _tokenize(original):
            features[f"msg:{token}"] = features.get(f"msg:{token}", 0.0) + 1.0

        params = intent_data.get("parameters", {}) or {}
        for key, value in params.items():
            features[f"pk:{str(key).lower()}"] = features.get(f"pk:{str(key).lower()}", 0.0) + 1.0
            for token in _tokenize(str(value)):
                features[f"pv:{token}"] = features.get(f"pv:{token}", 0.0) + 1.0
        return features

    def _cosine(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        dot = 0.0
        for k, v in a.items():
            dot += v * b.get(k, 0.0)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def _is_special_token(self, command: str) -> bool:
        low = command.lower().strip()
        return low.startswith("locate:") or low.startswith("locate_tp:")

    def _is_allowed_root(self, root: str) -> bool:
        allowed = set(command_catalog.get_commands())
        return root in allowed or root.startswith("locate:")

    def _load_model(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        if not os.path.exists(self.data_path):
            return {"samples": [], "by_intent": {}}
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("samples", [])
                    data.setdefault("by_intent", {})
                    return data
        except Exception:
            pass
        return {"samples": [], "by_intent": {}}

    def _save_model(self):
        try:
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump(self.model, f, indent=2)
        except Exception:
            pass


ml_command_engine = MLCommandEngine()
