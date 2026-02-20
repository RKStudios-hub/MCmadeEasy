import requests
import os
import json

def get_vanilla_versions():
    url = "https://piston-meta.mojang.com/mc/game/version_manifest.json"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return [{"version": v["id"], "url": v["url"]} for v in data["versions"] if v["type"] == "release"]
    except Exception:
        return []

def get_vanilla_server_url(version):
    url = "https://piston-meta.mojang.com/mc/game/version_manifest.json"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        for v in data["versions"]:
            if v["id"] == version:
                version_info = requests.get(v["url"], timeout=10).json()
                return version_info["downloads"]["server"]["url"]
    except Exception:
        return None
    return None

def download_vanilla(version, path):
    url = get_vanilla_server_url(version)
    if not url:
        return False, "Could not find version"

    resp = requests.get(url, timeout=60)
    if resp.status_code == 200:
        jar_path = os.path.join(path, "server.jar")
        with open(jar_path, "wb") as f:
            f.write(resp.content)
        return True, "Downloaded"
    return False, "Download failed"

def get_paper_versions():
    url = "https://api.papermc.io/v2/projects/paper"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return data.get("versions", [])
    except Exception:
        return []

def get_paper_builds(version):
    url = f"https://api.papermc.io/v2/projects/paper/versions/{version}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return data.get("builds", [])
    except Exception:
        return []

def download_paper(version, build, path):
    url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{build}/downloads/paper-{version}-{build}.jar"
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200:
            jar_path = os.path.join(path, "server.jar")
            with open(jar_path, "wb") as f:
                f.write(resp.content)
            return True, "Downloaded"
    except Exception as e:
        return False, str(e)
    return False, "Download failed"

def get_fabric_versions():
    url = "https://meta.fabricmc.net/v2/versions"
    try:
        resp = requests.get(url, timeout=10)
        return resp.json()
    except Exception:
        return []

def download_fabric(installer_version, path):
    url = f"https://meta.fabricmc.net/v2/versions/loader/1.20.1/0.15.11/server/jar"
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200:
            jar_path = os.path.join(path, "server.jar")
            with open(jar_path, "wb") as f:
                f.write(resp.content)
            return True, "Downloaded"
    except Exception:
        pass
    return False, "Use Fabric installer for now"
