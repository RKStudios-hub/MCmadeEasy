import datetime
import json
import os
import threading
import time
import uuid
import zipfile
from pathlib import Path
from urllib import request as urlrequest
from urllib import parse as urlparse
import requests


class CloudBackupManager:
    def __init__(self):
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        root_dir = os.path.dirname(backend_dir)
        self.servers_dir = os.path.join(root_dir, "servers")
        self.backups_dir = os.path.join(root_dir, "backups")
        data_dir = os.path.join(backend_dir, "data")
        self.config_path = os.path.join(data_dir, "backup_config.json")
        self.history_path = os.path.join(data_dir, "backup_history.json")
        os.makedirs(self.backups_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        self.config = self._load_config()
        self.history = self._load_history()

        self._lock = threading.Lock()
        self._scheduler_started = False
        self._profile_resolver = None
        self.progress = {}

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    cfg.setdefault("profiles", {})
                    cfg.setdefault("provider_tokens", {})
                    cfg.setdefault("oauth_states", {})
                    cfg.setdefault("provider_oauth", {})
                    return cfg
            except Exception:
                pass
        return {
            "profiles": {},
            "provider_tokens": {},
            "oauth_states": {},
            "provider_oauth": {},
            "defaults": {
                "enabled": False,
                "backup_type": "full_server",
                "providers": ["google_drive"],
                "backup_interval_hours": 24,
                "backup_on_stop_count": 10,
                "stop_counter": 0,
                "last_auto_backup_ts": 0
            }
        }

    def _save_config(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

    def _set_progress(self, profile, **fields):
        if not profile:
            return
        with self._lock:
            existing = dict(self.progress.get(profile, {}))
            existing.update(fields)
            existing.setdefault("profile", profile)
            existing["updated_at"] = int(time.time())
            self.progress[profile] = existing

    def _clear_progress(self, profile):
        if not profile:
            return
        with self._lock:
            self.progress.pop(profile, None)

    def get_progress(self, profile):
        if not profile:
            return {"success": False, "error": "Profile is required"}
        with self._lock:
            current = dict(self.progress.get(profile, {}))
        if not current:
            return {
                "success": True,
                "active": False,
                "profile": profile,
                "phase": "idle",
                "progress": 0,
                "message": "No active backup upload."
            }
        current.setdefault("success", True)
        return current

    def _provider_token_cfg(self):
        return self.config.setdefault("provider_tokens", {})

    def _oauth_states_cfg(self):
        return self.config.setdefault("oauth_states", {})

    def _provider_oauth_cfg(self):
        return self.config.setdefault("provider_oauth", {})

    def _cfg_or_env(self, provider, key, env_name):
        cfg = self._provider_oauth_cfg().get(provider, {})
        val = str(cfg.get(key, "")).strip()
        if val:
            return val
        return str(os.getenv(env_name, "")).strip()

    def _set_provider_tokens(self, provider, token_data):
        if not provider or not isinstance(token_data, dict):
            return
        tokens = self._provider_token_cfg()
        now = int(time.time())
        expires_in = int(token_data.get("expires_in", 0) or 0)
        entry = {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_at": now + expires_in if expires_in > 0 else 0,
            "updated_at": now
        }
        tokens[provider] = entry
        self._save_config()

    def _get_provider_access_token(self, provider):
        # Priority: explicit env var fallback, then stored OAuth token.
        env_map = {
            "google_drive": "GOOGLE_DRIVE_ACCESS_TOKEN",
            "dropbox": "DROPBOX_ACCESS_TOKEN",
            "onedrive": "ONEDRIVE_ACCESS_TOKEN"
        }
        env_name = env_map.get(provider)
        env_token = os.getenv(env_name, "").strip() if env_name else ""
        if env_token:
            return env_token
        entry = self._provider_token_cfg().get(provider, {})
        token = (entry or {}).get("access_token", "")
        if not token:
            return ""
        expires_at = int((entry or {}).get("expires_at", 0) or 0)
        if expires_at and int(time.time()) >= expires_at:
            return ""
        return token

    def _is_provider_connected(self, provider):
        return bool(self._get_provider_access_token(provider))

    def get_provider_oauth_config(self, provider):
        p = str(provider or "").strip().lower()
        if p not in {"google_drive", "dropbox", "onedrive"}:
            return {"success": False, "error": "Unknown provider"}
        cfg = dict(self._provider_oauth_cfg().get(p, {}))
        return {
            "success": True,
            "provider": p,
            "config": {
                "client_id": cfg.get("client_id", ""),
                "client_secret_set": bool(cfg.get("client_secret")),
                "redirect_uri": cfg.get("redirect_uri", "")
            }
        }

    def set_provider_oauth_config(self, provider, data):
        p = str(provider or "").strip().lower()
        if p not in {"google_drive", "dropbox", "onedrive"}:
            return {"success": False, "error": "Unknown provider"}
        cfgs = self._provider_oauth_cfg()
        current = dict(cfgs.get(p, {}))
        if "client_id" in data:
            current["client_id"] = str(data.get("client_id") or "").strip()
        if "client_secret" in data:
            current["client_secret"] = str(data.get("client_secret") or "").strip()
        if "redirect_uri" in data:
            current["redirect_uri"] = str(data.get("redirect_uri") or "").strip()
        cfgs[p] = current
        self._save_config()
        return self.get_provider_oauth_config(p)

    def _load_history(self):
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except Exception:
                pass
        return []

    def _save_history(self):
        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump(self.history[-500:], f, indent=2)

    def _profile_cfg(self, profile):
        defaults = dict(self.config.get("defaults", {}))
        profile_cfg = dict(self.config.get("profiles", {}).get(profile, {}))
        defaults.update(profile_cfg)
        return defaults

    def get_settings(self, profile):
        cfg = self._profile_cfg(profile)
        return {
            "profile": profile,
            "enabled": bool(cfg.get("enabled", False)),
            "backup_type": cfg.get("backup_type", "full_server"),
            "providers": cfg.get("providers", ["google_drive"]),
            "backup_interval_hours": int(cfg.get("backup_interval_hours", 24)),
            "backup_on_stop_count": int(cfg.get("backup_on_stop_count", 10)),
            "stop_counter": int(cfg.get("stop_counter", 0)),
            "last_auto_backup_ts": int(cfg.get("last_auto_backup_ts", 0))
        }

    def update_settings(self, profile, settings):
        if not profile:
            return {"success": False, "error": "Profile is required"}
        profiles_cfg = self.config.setdefault("profiles", {})
        existing = dict(profiles_cfg.get(profile, {}))
        existing["enabled"] = bool(settings.get("enabled", existing.get("enabled", False)))
        existing["backup_type"] = settings.get("backup_type", existing.get("backup_type", "full_server"))
        existing["providers"] = self._normalize_providers(settings.get("providers", existing.get("providers", ["google_drive"])))
        existing["backup_interval_hours"] = max(1, int(settings.get("backup_interval_hours", existing.get("backup_interval_hours", 24))))
        existing["backup_on_stop_count"] = max(1, int(settings.get("backup_on_stop_count", existing.get("backup_on_stop_count", 10))))
        existing["stop_counter"] = int(existing.get("stop_counter", 0))
        existing["last_auto_backup_ts"] = int(existing.get("last_auto_backup_ts", 0))
        profiles_cfg[profile] = existing
        self._save_config()
        return {"success": True, "settings": self.get_settings(profile)}

    def _normalize_providers(self, providers):
        allowed = {"google_drive", "dropbox", "onedrive"}
        if not providers:
            return ["google_drive"]
        normalized = []
        for p in providers:
            low = str(p).strip().lower()
            if low in allowed and low not in normalized:
                normalized.append(low)
        return normalized or ["google_drive"]

    def _next_default_backup_name(self, profile):
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        base = f"{profile}_{date_str}"
        counter = 1
        existing = {str(h.get("name", "")) for h in self.history if h.get("profile") == profile}
        while f"{base}_{counter}" in existing:
            counter += 1
        return f"{base}_{counter}"

    def _archive_profile(self, profile, backup_name, backup_type):
        profile_path = os.path.join(self.servers_dir, profile)
        if not os.path.isdir(profile_path):
            raise FileNotFoundError("Server profile not found")

        safe_name = "".join(c for c in backup_name if c.isalnum() or c in ("-", "_")).strip() or self._next_default_backup_name(profile)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{safe_name}_{ts}.zip"
        output_path = os.path.join(self.backups_dir, file_name)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            base_path = Path(profile_path)
            if backup_type == "world":
                world_dirs = []
                for item in base_path.iterdir():
                    if item.is_dir() and item.name.lower().startswith("world"):
                        world_dirs.append(item)
                if not world_dirs:
                    raise FileNotFoundError("No world folders found in profile")
                for world_dir in world_dirs:
                    for root, _, files in os.walk(world_dir):
                        for filename in files:
                            fp = os.path.join(root, filename)
                            rel = os.path.relpath(fp, profile_path)
                            zf.write(fp, rel)
            else:
                for root, dirs, files in os.walk(profile_path):
                    rel_root = os.path.relpath(root, profile_path)
                    if rel_root.startswith("logs") or rel_root.startswith("crash-reports"):
                        continue
                    for filename in files:
                        if filename.endswith(".lck"):
                            continue
                        fp = os.path.join(root, filename)
                        rel = os.path.relpath(fp, profile_path)
                        zf.write(fp, rel)

        return output_path, file_name, os.path.getsize(output_path)

    def create_backup(self, profile, backup_name=None, backup_type="full_server", providers=None, source="manual"):
        if not profile:
            return {"success": False, "error": "Profile is required"}
        backup_type = "world" if str(backup_type).lower() == "world" else "full_server"
        providers = self._normalize_providers(providers)
        if not backup_name:
            backup_name = self._next_default_backup_name(profile)
        self._set_progress(
            profile,
            success=True,
            active=True,
            phase="archiving",
            provider=None,
            progress=2,
            uploaded_bytes=0,
            total_bytes=0,
            message="Creating backup archive..."
        )

        try:
            zip_path, zip_name, size = self._archive_profile(profile, backup_name, backup_type)
        except Exception as e:
            self._set_progress(
                profile,
                success=True,
                active=False,
                phase="failed",
                progress=0,
                message=f"Backup failed: {e}"
            )
            return {"success": False, "error": str(e)}
        self._set_progress(
            profile,
            success=True,
            active=True,
            phase="uploading",
            provider=None,
            progress=8,
            uploaded_bytes=0,
            total_bytes=size,
            message="Archive ready. Starting cloud upload..."
        )
        uploads = self._upload_to_providers(profile, zip_path, zip_name, providers)
        now_ts = int(time.time())
        info = {
            "id": str(uuid.uuid4()),
            "name": backup_name,
            "file_name": zip_name,
            "profile": profile,
            "created_at": now_ts,
            "backup_type": backup_type,
            "providers": providers,
            "uploads": uploads,
            "size": size,
            "source": source,
            "local_path": zip_path,
            "status": "completed"
        }
        success_count = 0
        for provider_result in uploads.values():
            if isinstance(provider_result, dict) and provider_result.get("success"):
                success_count += 1
        total_targets = len(providers or [])
        info["cloud_upload"] = {
            "requested_providers": total_targets,
            "succeeded": success_count,
            "failed": max(0, total_targets - success_count),
            "status": "uploaded" if total_targets and success_count == total_targets else ("partial" if success_count > 0 else ("skipped" if total_targets == 0 else "failed"))
        }
        with self._lock:
            self.history.append(info)
            self.history = self.history[-500:]
            self._save_history()
        if total_targets > 0 and success_count == 0:
            self._set_progress(
                profile,
                success=True,
                active=False,
                phase="failed",
                progress=100,
                message="Backup archive created locally, but cloud upload failed."
            )
            return {
                "success": False,
                "error": "Backup archive created locally, but cloud upload failed for all selected providers.",
                "backup": info
            }
        self._set_progress(
            profile,
            success=True,
            active=False,
            phase="completed",
            progress=100,
            message="Backup upload completed."
        )
        return {"success": True, "backup": info, "partial": total_targets > 0 and success_count < total_targets}

    def list_backups(self, profile=None):
        records = list(reversed(self.history))
        if profile:
            records = [b for b in records if b.get("profile") == profile]
        return records

    def restore_backup(self, profile, backup_name):
        return {"success": False, "error": "Restore not implemented in this version."}

    def on_server_stop(self, profile):
        if not profile:
            return {"success": False, "reason": "no_profile"}
        cfg = self._profile_cfg(profile)
        if not cfg.get("enabled", False):
            return {"success": False, "reason": "auto_backup_disabled"}

        profiles_cfg = self.config.setdefault("profiles", {})
        state = dict(profiles_cfg.get(profile, {}))
        state["stop_counter"] = int(state.get("stop_counter", 0)) + 1
        profiles_cfg[profile] = state
        self._save_config()

        threshold = max(1, int(cfg.get("backup_on_stop_count", 10)))
        if state["stop_counter"] >= threshold:
            result = self.create_backup(
                profile=profile,
                backup_name=None,
                backup_type=cfg.get("backup_type", "full_server"),
                providers=cfg.get("providers", ["google_drive"]),
                source="auto_stop_cycle"
            )
            state["stop_counter"] = 0
            state["last_auto_backup_ts"] = int(time.time())
            profiles_cfg[profile] = state
            self._save_config()
            return result
        return {"success": True, "message": "Stop cycle counted", "stop_counter": state["stop_counter"]}

    def start_scheduler(self, profile_resolver):
        if self._scheduler_started:
            return
        self._scheduler_started = True
        self._profile_resolver = profile_resolver

        def _loop():
            while True:
                try:
                    profile = self._profile_resolver() if self._profile_resolver else None
                    if profile:
                        cfg = self._profile_cfg(profile)
                        if cfg.get("enabled", False):
                            now = int(time.time())
                            interval_sec = max(1, int(cfg.get("backup_interval_hours", 24))) * 3600
                            last = int(cfg.get("last_auto_backup_ts", 0))
                            if now - last >= interval_sec:
                                result = self.create_backup(
                                    profile=profile,
                                    backup_name=None,
                                    backup_type=cfg.get("backup_type", "full_server"),
                                    providers=cfg.get("providers", ["google_drive"]),
                                    source="auto_interval"
                                )
                                if result.get("success"):
                                    profiles_cfg = self.config.setdefault("profiles", {})
                                    state = dict(profiles_cfg.get(profile, {}))
                                    state["last_auto_backup_ts"] = now
                                    profiles_cfg[profile] = state
                                    self._save_config()
                except Exception:
                    pass
                time.sleep(60)

        thread = threading.Thread(target=_loop, daemon=True)
        thread.start()

    def _upload_to_providers(self, profile, file_path, file_name, providers):
        out = {}
        total = max(1, len(providers))
        for idx, provider in enumerate(providers):
            try:
                base_progress = 8 + int((idx / total) * 84)
                self._set_progress(
                    profile,
                    success=True,
                    active=True,
                    phase="uploading",
                    provider=provider,
                    progress=base_progress,
                    message=f"Uploading to {provider}..."
                )
                if provider == "google_drive":
                    out[provider] = self._upload_google_drive(profile, file_path, file_name, base_progress, total)
                elif provider == "dropbox":
                    out[provider] = self._upload_dropbox(file_path, file_name)
                elif provider == "onedrive":
                    out[provider] = self._upload_onedrive(file_path, file_name)
                else:
                    out[provider] = {"success": False, "error": "Unsupported provider"}
                done_progress = 8 + int(((idx + 1) / total) * 84)
                if out[provider].get("success"):
                    self._set_progress(
                        profile,
                        success=True,
                        active=True,
                        phase="uploading",
                        provider=provider,
                        progress=done_progress,
                        message=f"Uploaded to {provider}."
                    )
                else:
                    self._set_progress(
                        profile,
                        success=True,
                        active=True,
                        phase="uploading",
                        provider=provider,
                        progress=done_progress,
                        message=f"{provider} upload failed."
                    )
            except Exception as e:
                out[provider] = {"success": False, "error": str(e)}
        self._set_progress(
            profile,
            success=True,
            active=True,
            phase="finalizing",
            provider=None,
            progress=96,
            message="Finalizing backup record..."
        )
        return out

    def _upload_google_drive(self, profile, file_path, file_name, base_progress=8, provider_count=1):
        token = self._get_provider_access_token("google_drive")
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
        if not token:
            return {"success": False, "error": "Missing GOOGLE_DRIVE_ACCESS_TOKEN"}
        metadata = {"name": file_name}
        if folder_id:
            metadata["parents"] = [folder_id]
        file_size = os.path.getsize(file_path)
        try:
            start_resp = requests.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&fields=id,webViewLink",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Type": "application/zip",
                    "X-Upload-Content-Length": str(file_size),
                },
                json=metadata,
                timeout=(20, 120),
            )
            if start_resp.status_code >= 400:
                return {"success": False, "error": f"Google upload init failed: {start_resp.text}"}
            session_url = start_resp.headers.get("Location")
            if not session_url:
                return {"success": False, "error": "Google upload init returned no session URL"}
            chunk_size = 8 * 1024 * 1024
            uploaded = 0
            final_resp = None
            with open(file_path, "rb") as fh:
                while True:
                    chunk = fh.read(chunk_size)
                    if not chunk:
                        break
                    start = uploaded
                    end = uploaded + len(chunk) - 1
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/zip",
                        "Content-Length": str(len(chunk)),
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                    }
                    upload_resp = requests.put(
                        session_url,
                        headers=headers,
                        data=chunk,
                        timeout=(20, 900),
                    )
                    if upload_resp.status_code in (200, 201):
                        uploaded = end + 1
                        final_resp = upload_resp
                        self._set_progress(
                            profile,
                            success=True,
                            active=True,
                            phase="uploading",
                            provider="google_drive",
                            progress=base_progress + int((uploaded / max(1, file_size)) * (84 / max(1, provider_count))),
                            uploaded_bytes=uploaded,
                            total_bytes=file_size,
                            message=f"Uploading to google_drive... {int((uploaded / max(1, file_size)) * 100)}%"
                        )
                        break
                    if upload_resp.status_code == 308:
                        uploaded = end + 1
                        self._set_progress(
                            profile,
                            success=True,
                            active=True,
                            phase="uploading",
                            provider="google_drive",
                            progress=base_progress + int((uploaded / max(1, file_size)) * (84 / max(1, provider_count))),
                            uploaded_bytes=uploaded,
                            total_bytes=file_size,
                            message=f"Uploading to google_drive... {int((uploaded / max(1, file_size)) * 100)}%"
                        )
                        continue
                    return {"success": False, "error": f"Google upload failed: {upload_resp.text}"}

            if not final_resp:
                return {"success": False, "error": "Google upload failed: no completion response"}
            data = final_resp.json()
            file_id = data.get("id")
            web_link = data.get("webViewLink")
            return {
                "success": True,
                "file_id": file_id,
                "url": web_link or (f"https://drive.google.com/file/d/{file_id}/view" if file_id else None),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _upload_dropbox(self, file_path, file_name):
        token = self._get_provider_access_token("dropbox")
        if not token:
            return {"success": False, "error": "Missing DROPBOX_ACCESS_TOKEN"}
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        dbx_path = f"/MCmadeEasy Backups/{file_name}"
        req = urlrequest.Request(
            "https://content.dropboxapi.com/2/files/upload",
            data=file_bytes,
            method="POST"
        )
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/octet-stream")
        req.add_header("Dropbox-API-Arg", json.dumps({
            "path": dbx_path,
            "mode": "add",
            "autorename": True,
            "mute": False
        }))
        with urlrequest.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "path": data.get("path_display")}

    def _upload_onedrive(self, file_path, file_name):
        token = self._get_provider_access_token("onedrive")
        if not token:
            return {"success": False, "error": "Missing ONEDRIVE_ACCESS_TOKEN"}
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        target_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/MCmadeEasy Backups/{file_name}:/content"
        req = urlrequest.Request(target_url, data=file_bytes, method="PUT")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/zip")
        with urlrequest.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "file_id": data.get("id"), "web_url": data.get("webUrl")}

    def get_provider_connection_status(self, providers):
        normalized = self._normalize_providers(providers)
        status = {}
        for p in normalized:
            connected = self._is_provider_connected(p)
            status[p] = {
                "connected": connected,
                "auth_url": self.get_provider_auth_url(p).get("auth_url", None),
            }
        return {"success": True, "providers": status}

    def get_provider_auth_url(self, provider):
        p = str(provider or "").strip().lower()
        state = str(uuid.uuid4())
        states = self._oauth_states_cfg()
        states[state] = {"provider": p, "created_at": int(time.time())}
        self._save_config()

        backend_base = os.getenv("BACKEND_BASE_URL", "http://localhost:8001").rstrip("/")
        if p == "google_drive":
            client_id = self._cfg_or_env("google_drive", "client_id", "GOOGLE_DRIVE_CLIENT_ID")
            redirect_uri = self._cfg_or_env("google_drive", "redirect_uri", "GOOGLE_DRIVE_REDIRECT_URI") or f"{backend_base}/backup/oauth/callback/google_drive"
            if client_id and redirect_uri:
                url = (
                    "https://accounts.google.com/o/oauth2/v2/auth"
                    f"?client_id={client_id}"
                    f"&redirect_uri={redirect_uri}"
                    "&response_type=code"
                    "&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.file"
                    f"&state={state}"
                    "&access_type=offline&prompt=consent"
                )
            else:
                return {"success": False, "provider": p, "auth_url": None, "error": "Missing GOOGLE_DRIVE_CLIENT_ID"}
            return {"success": True, "provider": p, "auth_url": url, "state": state}
        if p == "dropbox":
            client_id = self._cfg_or_env("dropbox", "client_id", "DROPBOX_APP_KEY")
            redirect_uri = self._cfg_or_env("dropbox", "redirect_uri", "DROPBOX_REDIRECT_URI") or f"{backend_base}/backup/oauth/callback/dropbox"
            if client_id and redirect_uri:
                url = (
                    "https://www.dropbox.com/oauth2/authorize"
                    f"?client_id={client_id}"
                    "&response_type=code"
                    f"&redirect_uri={redirect_uri}"
                    f"&state={state}"
                )
            else:
                return {"success": False, "provider": p, "auth_url": None, "error": "Missing DROPBOX_APP_KEY"}
            return {"success": True, "provider": p, "auth_url": url, "state": state}
        if p == "onedrive":
            client_id = self._cfg_or_env("onedrive", "client_id", "ONEDRIVE_CLIENT_ID")
            redirect_uri = self._cfg_or_env("onedrive", "redirect_uri", "ONEDRIVE_REDIRECT_URI") or f"{backend_base}/backup/oauth/callback/onedrive"
            if client_id and redirect_uri:
                url = (
                    "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
                    f"?client_id={client_id}"
                    "&response_type=code"
                    f"&redirect_uri={redirect_uri}"
                    "&scope=offline_access%20Files.ReadWrite.AppFolder"
                    f"&state={state}"
                )
            else:
                return {"success": False, "provider": p, "auth_url": None, "error": "Missing ONEDRIVE_CLIENT_ID"}
            return {"success": True, "provider": p, "auth_url": url, "state": state}
        return {"success": False, "error": "Unknown provider", "provider": p, "auth_url": None}

    def _post_form(self, url, form_data):
        payload = urlparse.urlencode(form_data).encode("utf-8")
        req = urlrequest.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urlrequest.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def handle_oauth_callback(self, provider, code, state=None, error=None):
        p = str(provider or "").strip().lower()
        if error:
            return {"success": False, "provider": p, "error": error}
        if not code:
            return {"success": False, "provider": p, "error": "Missing authorization code"}

        if state:
            states = self._oauth_states_cfg()
            st = states.get(state)
            if not st or st.get("provider") != p:
                return {"success": False, "provider": p, "error": "Invalid OAuth state"}
            states.pop(state, None)
            self._save_config()

        backend_base = os.getenv("BACKEND_BASE_URL", "http://localhost:8001").rstrip("/")
        try:
            if p == "google_drive":
                client_id = self._cfg_or_env("google_drive", "client_id", "GOOGLE_DRIVE_CLIENT_ID")
                client_secret = self._cfg_or_env("google_drive", "client_secret", "GOOGLE_DRIVE_CLIENT_SECRET")
                redirect_uri = self._cfg_or_env("google_drive", "redirect_uri", "GOOGLE_DRIVE_REDIRECT_URI") or f"{backend_base}/backup/oauth/callback/google_drive"
                if not client_id or not client_secret:
                    return {"success": False, "provider": p, "error": "Missing GOOGLE_DRIVE_CLIENT_ID/SECRET"}
                token_data = self._post_form("https://oauth2.googleapis.com/token", {
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                })
                self._set_provider_tokens("google_drive", token_data)
                return {"success": True, "provider": p}

            if p == "dropbox":
                client_id = self._cfg_or_env("dropbox", "client_id", "DROPBOX_APP_KEY")
                client_secret = self._cfg_or_env("dropbox", "client_secret", "DROPBOX_APP_SECRET")
                redirect_uri = self._cfg_or_env("dropbox", "redirect_uri", "DROPBOX_REDIRECT_URI") or f"{backend_base}/backup/oauth/callback/dropbox"
                if not client_id or not client_secret:
                    return {"success": False, "provider": p, "error": "Missing DROPBOX_APP_KEY/SECRET"}
                token_data = self._post_form("https://api.dropboxapi.com/oauth2/token", {
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                })
                self._set_provider_tokens("dropbox", token_data)
                return {"success": True, "provider": p}

            if p == "onedrive":
                client_id = self._cfg_or_env("onedrive", "client_id", "ONEDRIVE_CLIENT_ID")
                client_secret = self._cfg_or_env("onedrive", "client_secret", "ONEDRIVE_CLIENT_SECRET")
                redirect_uri = self._cfg_or_env("onedrive", "redirect_uri", "ONEDRIVE_REDIRECT_URI") or f"{backend_base}/backup/oauth/callback/onedrive"
                if not client_id or not client_secret:
                    return {"success": False, "provider": p, "error": "Missing ONEDRIVE_CLIENT_ID/SECRET"}
                token_data = self._post_form("https://login.microsoftonline.com/common/oauth2/v2.0/token", {
                    "client_id": client_id,
                    "scope": "offline_access Files.ReadWrite.AppFolder",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "client_secret": client_secret
                })
                self._set_provider_tokens("onedrive", token_data)
                return {"success": True, "provider": p}
        except Exception as e:
            return {"success": False, "provider": p, "error": str(e)}

        return {"success": False, "provider": p, "error": "Unknown provider"}


backup_manager = CloudBackupManager()
