import os
import json

BASE_DIR = "servers"

def get_base_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def create_profile(name):
    base = os.path.join(get_base_dir(), BASE_DIR)
    path = os.path.join(base, name)
    os.makedirs(path, exist_ok=True)

    config = {
        "name": name,
        "software": None,
        "version": None,
        "port": 25565
    }

    with open(os.path.join(path, "profile.json"), "w") as f:
        json.dump(config, f, indent=2)

    return path

def list_profiles():
    base = os.path.join(get_base_dir(), BASE_DIR)
    if not os.path.exists(base):
        return []
    profiles = []
    for item in os.listdir(base):
        profile_path = os.path.join(base, item)
        if os.path.isdir(profile_path):
            config_path = os.path.join(profile_path, "profile.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    profiles.append(json.load(f))
            else:
                profiles.append({"name": item, "software": None, "version": None})
    return profiles

def get_profile(name):
    base = os.path.join(get_base_dir(), BASE_DIR)
    path = os.path.join(base, name)
    config_path = os.path.join(path, "profile.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return None

def update_profile(name, data):
    base = os.path.join(get_base_dir(), BASE_DIR)
    path = os.path.join(base, name)
    config_path = os.path.join(path, "profile.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
        config.update(data)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return config
    return None
