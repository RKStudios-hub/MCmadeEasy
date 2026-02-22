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

def get_fabric_loader_version(mc_version):
    url = "https://meta.fabricmc.net/v2/versions/loader/" + mc_version
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data:
            return data[0]["version"], data[0]["loader"]["version"]
    except Exception:
        pass
    return None, None

def download_fabric_mc(version, path):
    try:
        resp = requests.get(f"https://meta.fabricmc.net/v2/versions/loader/{version}", timeout=10)
        data = resp.json()
        if data:
            loader_ver = data[0]["loader"]["version"]
            url = f"https://meta.fabricmc.net/v2/versions/loader/{version}/{loader_ver}/server/jar"
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200:
                jar_path = os.path.join(path, "server.jar")
                with open(jar_path, "wb") as f:
                    f.write(resp.content)
                return True, "Downloaded"
    except Exception as e:
        return False, str(e)
    return False, "Download failed"

def get_forge_versions():
    try:
        resp = requests.get("https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json", timeout=10)
        data = resp.json()
        versions = []
        for k in data.get("promos", {}):
            if "-recommended" in k:
                mc_ver = k.replace("-recommended", "")
                if mc_ver not in versions:
                    versions.append(mc_ver)
        return versions
    except Exception:
        return []

def get_forge_builds(version):
    return ["recommended"]

def get_latest_forge_version(version):
    try:
        resp = requests.get("https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json", timeout=10)
        data = resp.json()
        key = f"{version}-recommended"
        if key in data.get("promos", {}):
            return f"{version}-{data['promos'][key]}"
    except Exception as e:
        print(f"Error getting Forge version: {e}")
    return None

def download_forge(version, full_version, path):
    # Download the installer JAR
    installer_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{full_version}/forge-{full_version}-installer.jar"
    try:
        # Download installer
        installer_path = os.path.join(path, f"forge-installer-{full_version}.jar")
        resp = requests.get(installer_url, timeout=180)
        if resp.status_code != 200:
            return False, "Failed to download Forge installer"
        
        with open(installer_path, "wb") as f:
            f.write(resp.content)
        
        # Import JAVA_PATH from server_manager
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from server_manager import JAVA_PATH
        
        # Run the installer to install the server
        import subprocess
        result = subprocess.run(
            [JAVA_PATH, "-jar", installer_path, "--installServer"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Check if installation was successful - installer creates forge-*-universal.jar
        import glob
        universal_jars = glob.glob(os.path.join(path, "forge-*-universal.jar"))
        if universal_jars:
            # Copy to server.jar
            import shutil
            shutil.copy(universal_jars[0], os.path.join(path, "server.jar"))
            return True, "Forge installed successfully"
        
        return True, "Forge installer downloaded. Please run the installer manually."
        
    except Exception as e:
        return False, f"Error installing Forge: {str(e)}"

def get_neoforge_versions():
    try:
        resp = requests.get("https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml", timeout=10)
        text = resp.text
        import re
        versions = re.findall(r'<version>(.*?)</version>', text)
        mc_versions = []
        for v in versions:
            if v.startswith("net.neoforged:neoforge:"):
                ver = v.replace("net.neoforged:neoforge:", "")
                mc_ver = ver.rsplit("-", 1)[0] if "-" in ver else ver
                if mc_ver not in mc_versions:
                    mc_versions.append(mc_ver)
        return sorted(mc_versions, reverse=True)
    except Exception as e:
        print(f"Error getting NeoForge versions: {e}")
        return []

def get_neoforge_builds(version):
    return ["latest"]

def get_latest_neoforge_version(version):
    try:
        resp = requests.get("https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml", timeout=10)
        text = resp.text
        import re
        mc_ver = version.replace("1.", "")
        pattern = rf'<version>({mc_ver}\.\d+[^<]*)</version>'
        versions = re.findall(pattern, text)
        if versions:
            return versions[0]
    except Exception as e:
        print(f"Error getting NeoForge version: {e}")
    return None

def download_neoforge(version, full_version, path):
    url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{full_version}/neoforge-{full_version}-server.jar"
    try:
        resp = requests.get(url, timeout=180)
        if resp.status_code == 200:
            jar_path = os.path.join(path, "server.jar")
            with open(jar_path, "wb") as f:
                f.write(resp.content)
            return True, "Downloaded"
    except Exception as e:
        return False, str(e)
    return False, "Download failed"

def download_neoforge_auto(version, path):
    build = get_latest_neoforge_version(version)
    if not build:
        return False, "Could not find NeoForge version"
    return download_neoforge(version, build, path)

def get_quilt_versions():
    url = "https://meta.fabricmc.net/v2/versions/loader"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        versions = list(set([v["version"] for v in data]))
        return sorted(versions, reverse=True)
    except Exception:
        return []

def get_quilt_builds(version):
    url = f"https://meta.fabricmc.net/v2/versions/loader/{version}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return [v["loader"]["version"] for v in data]
    except Exception:
        return []

def download_quilt(version, build, path):
    url = f"https://meta.fabricmc.net/v2/versions/loader/{version}/{build}/server/jar"
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

def get_latest_quilt_version(version):
    url = f"https://meta.fabricmc.net/v2/versions/loader/{version}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data:
            return data[0]["loader"]["version"]
    except Exception:
        pass
    return None

def download_quilt_auto(version, path):
    build = get_latest_quilt_version(version)
    if not build:
        return False, "Could not find Quilt version"
    return download_quilt(version, build, path)

def get_leaf_versions():
    url = "https://api.papermc.io/v2/projects/leaf"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return data.get("versions", [])
    except Exception:
        return []

def get_leaf_builds(version):
    url = f"https://api.papermc.io/v2/projects/leaf/versions/{version}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return data.get("builds", [])
    except Exception:
        return []

def download_leaf(version, build, path):
    url = f"https://api.papermc.io/v2/projects/leaf/versions/{version}/builds/{build}/downloads/leaf-{version}-{build}.jar"
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

def get_purpur_versions():
    url = "https://api.purpurmc.org/v2/purpur"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return data.get("versions", [])
    except Exception:
        return []

def get_purpur_builds(version):
    url = f"https://api.purpurmc.org/v2/purpur/{version}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return data.get("builds", {}).get("all", [])
    except Exception:
        return []

def download_purpur(version, build, path):
    url = f"https://api.purpurmc.org/v2/purpur/{version}/{build}/download"
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

def get_spigot_versions():
    url = "https://hub.spigotmc.org/versions/"
    try:
        resp = requests.get(url, timeout=10)
        import re
        versions = re.findall(r'(\d+\.\d+)', resp.text)
        return versions
    except Exception:
        return []

def download_spigot(version, path):
    url = f"https://hub.spigotmc.org/versions/{version}/spigot-{version}.jar"
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
