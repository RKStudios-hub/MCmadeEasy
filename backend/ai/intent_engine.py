import json
import re
import os
import time
import difflib
from core.gateway import gateway
from core.memory_engine import memory_engine
from engine.command_catalog import command_catalog


COMMON_ITEMS = [
    # Ores & Ingots
    "diamond", "gold_ingot", "iron_ingot", "copper_ingot", "netherite_scrap", "netherite_ingot", "emerald", "lapis_lazuli", "redstone", "coal", "quartz", "amethyst_shard", "raw_copper", "raw_iron", "raw_gold",
    # Blocks - Ores
    "diamond_block", "gold_block", "iron_block", "emerald_block", "redstone_block", "lapis_block", "coal_block", "quartz_block", "copper_block", "raw_copper_block", "raw_iron_block", "raw_gold_block",
    # Building Blocks
    "cobblestone", "stone", "granite", "diorite", "andesite", "sandstone", "prismarine", "nether_brick", "mossy_cobblestone", "deepslate", "cobbled_deepslate", " Blackstone", "polished_blackstone", "deepslate_bricks", "cracked_deepslate_bricks",
    "oak_log", "spruce_log", "birch_log", "jungle_log", "acacia_log", "dark_oak_log", "mangrove_log", "cherry_log", "crimson_stem", "warped_stem",
    "oak_planks", "spruce_planks", "birch_planks", "jungle_planks", "acacia_planks", "dark_oak_planks", "mangrove_planks", "cherry_planks", "crimson_planks", "warped_planks",
    "oak_wood", "spruce_wood", "birch_wood", "jungle_wood", "acacia_wood", "dark_oak_wood", "mangrove_wood", "cherry_wood", "stripped_oak_wood", "stripped_spruce_wood",
    "grass_block", "dirt", "coarse_dirt", "podzol", "netherrack", "end_stone", "bedrock", "clay", "gravel", "sand", "red_sand", "snow", "ice", "snow_block", "powder_snow",
    "glass", "glass_pane", "obsidian", "crying_obsidian", "glowstone", "sea_lantern", "shroomlight", "respawn_anchor", "bone_block", "netherite_block",
    # Colored Blocks
    "white_wool", "orange_wool", "magenta_wool", "light_blue_wool", "yellow_wool", "lime_wool", "pink_wool", "gray_wool", "light_gray_wool", "cyan_wool", "purple_wool", "blue_wool", "brown_wool", "green_wool", "red_wool", "black_wool",
    "white_carpet", "orange_carpet", "magenta_carpet", "light_blue_carpet", "yellow_carpet", "lime_carpet", "pink_carpet", "gray_carpet", "light_gray_carpet", "cyan_carpet", "purple_carpet", "blue_carpet", "brown_carpet", "green_carpet", "red_carpet", "black_carpet",
    "white_concrete", "orange_concrete", "magenta_concrete", "light_blue_concrete", "yellow_concrete", "lime_concrete", "pink_concrete", "gray_concrete", "light_gray_concrete", "cyan_concrete", "purple_concrete", "blue_concrete", "brown_concrete", "green_concrete", "red_concrete", "black_concrete",
    "white_terracotta", "orange_terracotta", "magenta_terracotta", "light_blue_terracotta", "yellow_terracotta", "lime_terracotta", "pink_terracotta", "gray_terracotta", "light_gray_terracotta", "cyan_terracotta", "purple_terracotta", "blue_terracotta", "brown_terracotta", "green_terracotta", "red_terracotta", "black_terracotta",
    # Food
    "apple", "golden_apple", "enchanted_golden_apple", "bread", "carrot", "golden_carrot", "cooked_beef", "cooked_porkchop", "cooked_chicken", "cooked_mutton", "cooked_rabbit", "rabbit_stew", "suspicious_stew", "beetroot", "beetroot_soup", "pumpkin_pie", "cake", "cookie", "melon_slice", "sweet_berries", "honey_bottle", "milk_bucket", "honeycomb",
    "porkchop", "beef", "chicken", "mutton", "rabbit", "cod", "salmon", "tropical_fish", "pufferfish",
    "cooked_cod", "cooked_salmon", "dried_kelp", "glow_berries",
    # Tools & Weapons - Diamond
    "diamond_sword", "diamond_pickaxe", "diamond_axe", "diamond_shovel", "diamond_hoe", "diamond_horse_armor",
    # Tools & Weapons - Gold
    "golden_sword", "golden_pickaxe", "golden_axe", "golden_shovel", "golden_hoe", "golden_horse_armor",
    # Tools & Weapons - Iron
    "iron_sword", "iron_pickaxe", "iron_axe", "iron_shovel", "iron_hoe", "iron_horse_armor",
    # Tools & Weapons - Stone
    "stone_sword", "stone_pickaxe", "stone_axe", "stone_shovel", "stone_hoe",
    # Tools & Weapons - Wood
    "wooden_sword", "wooden_pickaxe", "wooden_axe", "wooden_shovel", "wooden_hoe",
    # Tools & Weapons - Netherite
    "netherite_sword", "netherite_pickaxe", "netherite_axe", "netherite_shovel", "netherite_hoe",
    # Ranged
    "bow", "crossbow", "trident", "shield", "totem_of_undying", "fishing_rod", "carrot_on_a_stick", "warped_fungus_on_a_stick",
    # Armor - Diamond
    "diamond_helmet", "diamond_chestplate", "diamond_leggings", "diamond_boots",
    # Armor - Gold
    "golden_helmet", "golden_chestplate", "golden_leggings", "golden_boots",
    # Armor - Iron
    "iron_helmet", "iron_chestplate", "iron_leggings", "iron_boots",
    # Armor - Chainmail
    "chainmail_helmet", "chainmail_chestplate", "chainmail_leggings", "chainmail_boots",
    # Armor - Leather
    "leather_helmet", "leather_chestplate", "leather_leggings", "leather_boots", "leather_horse_armor",
    # Armor - Other
    "turtle_helmet", "netherite_helmet", "netherite_chestplate", "netherite_leggings", "netherite_boots",
    # Materials
    "stick", "string", "feather", "leather", "rabbit_hide", "phantom_membrane", "scute", "nautilus_shell", "heart_of_the_sea",
    "paper", "book", "written_book", "writable_book", "book_and_quill", "writable_book",
    "bookshelf", "lectern", "enchanted_book", "knowledge_book",
    "slime_ball", "slime_block", "honey_block",
    "ender_pearl", "ender_eye", "shulker_shell", "shulker_box",
    "blaze_rod", "blaze_powder", "ghast_tear", "magma_cream", "nether_star", "nether_wart", "soul_sand", "soul_soil", "warped_wart", "shroomlight",
    # Potions & Brewing
    "potion", "splash_potion", "lingering_potion", "glass_bottle", "bucket", "water_bucket", "lava_bucket", "milk_bucket", "pufferfish_bucket", "salmon_bucket", "cod_bucket", "tropical_fish_bucket", "axolotl_bucket", "powder_snow_bucket",
    "dragon_breath", "fermented_spider_eye", "rabbit_foot", "spider_eye", "glistering_melon_slice", "glowstone_dust", "gunpowder",
    "cauldron", "brewing_stand", "dragon_egg",
    # Lighting
    "torch", "soul_torch", "redstone_torch", "candle", "soul_candle", "lantern", "soul_lantern", "glow_item_frame", "item_frame", "sea_pickle", "glow_ink_sack",
    "jack_o_lantern", "lit_pumpkin", "end_rod", "beacon", "conduit",
    # Utility
    "compass", "clock", "map", "filled_map", "spyglass", "recovery_compass", "compass", "lodestone_compass",
    "music_disc_13", "music_disc_cat", "music_disc_blocks", "music_disc_chirp", "music_disc_far", "music_disc_mall", "music_disc_mellohi", "music_disc_stal", "music_disc_strad", "music_disc_ward", "music_disc_11", "music_disc_wait", "music_disc_otherside", "music_disc_pigstep", "music_disc_5", "music_disc_3",
    "saddle", "name_tag", "lead", "minecart", "chest_minecart", "furnace_minecart", "tnt_minecart", "hopper_minecart", "command_block_minecart",
    "fire_charge", "firework_rocket", "firework_star", "sparkler",
    "shears", "flint_and_steel", "flint", "coal", "charcoal", "bone", "bone_meal",
    "loom", "cartography_table", "fletching_table", "smithing_table", "grindstone", "stonecutter", "bell", "campfire", "soul_campfire",
    "enchanting_table", "anvil", "chipped_anvil", "damaged_anvil",
    "crafting_table", "furnace", "blast_furnace", "smoker", "dropper", "dispenser", "hopper", "observer", "piston", "sticky_piston", "note_block", "jukebox",
    "head", "skull", "wither_skeleton_skull", "zombie_head", "creeper_head", "player_head", "dragon_head", "piglin_head",
    "banner_pattern", "white_banner", "orange_banner", "magenta_banner", "light_blue_banner", "yellow_banner", "lime_banner", "pink_banner", "gray_banner", "light_gray_banner", "cyan_banner", "purple_banner", "blue_banner", "brown_banner", "green_banner", "red_banner", "black_banner",
    "flower_pot", "armor_stand", "painting", "frame", "item_frame", "glow_item_frame",
    # Spawn Eggs
    "zombie_spawn_egg", "skeleton_spawn_egg", "creeper_spawn_egg", "spider_spawn_egg", "pig_spawn_egg", "cow_spawn_egg", "sheep_spawn_egg", "chicken_spawn_egg", "villager_spawn_egg", "wandering_trader_spawn_egg", "horse_spawn_egg", "donkey_spawn_egg", "llama_spawn_egg", "trader_llama_spawn_egg", "rabbit_spawn_egg", "wolf_spawn_egg", "cat_spawn_egg", "ocelot_spawn_egg", "parrot_spawn_egg", "bat_spawn_egg", "silverfish_spawn_egg", "enderman_spawn_egg", "cave_spider_spawn_egg", "witch_spawn_egg", "zombie_pigman_spawn_egg", "slime_spawn_egg", "ghast_spawn_egg", "blaze_spawn_egg", "magma_cube_spawn_egg", "wither_skeleton_spawn_egg", "shulker_spawn_egg", "elder_guardian_spawn_egg", "guardian_spawn_egg", "turtle_spawn_egg", "dolphin_spawn_egg", "drowned_spawn_egg", "polar_bear_spawn_egg", "panda_spawn_egg", "pillager_spawn_egg", "ravager_spawn_egg", "vindicator_spawn_egg", "evoker_spawn_egg", "vex_spawn_egg", "hoglin_spawn_egg", "piglin_spawn_egg", "piglin_brute_spawn_egg", "strider_spawn_egg", "zoglin_spawn_egg", "axolotl_spawn_egg", "glow_squid_spawn_egg", "goat_spawn_egg", "frog_spawn_egg", "allay_spawn_egg", "warden_spawn_egg", "breeze_spawn_egg", "bogged_spawn_egg", "breeze_ice_ball",
    # mobs
    "zombie", "skeleton", "creeper", "spider", "pig", "cow", "sheep", "chicken", "villager", "wandering_trader", "horse", "donkey", "llama", "rabbit", "wolf", "cat", "ocelot", "parrot", "bat", "silverfish", "enderman", "cave_spider", "witch", "zombie_pigman", "slime", "ghast", "blaze", "magma_cube", "wither_skeleton", "shulker", "elder_guardian", "guardian", "turtle", "dolphin", "drowned", "polar_bear", "panda", "pillager", "ravager", "vindicator", "evoker", "vex", "hoglin", "piglin", "piglin_brute", "strider", "zoglin", "axolotl", "glow_squid", "goat", "frog", "allay", "warden", "breeze", "phantom", "husk", "stray", "polar_bear", "vex",
    # Effects
    "speed", "slowness", "haste", "mining_fatigue", "strength", "jump_boost", "regeneration", "resistance", "fire_resistance", "water_breathing", "invisibility", "blindness", "night_vision", "glowing", "levitation", "luck", "slow_falling", "conduit_power", "dolphins_grace", "bad_omen", "hero_of_the_village",
]


class ItemResolver:
    """AI-powered item resolver that finds the best Minecraft item match"""
    
    def __init__(self):
        self.gateway = gateway
        self.common_items = COMMON_ITEMS
        self._item_cache = {}
    
    def resolve(self, user_text):
        """
        Use AI to find the best item match from user text.
        Returns the Minecraft item ID.
        """
        if not user_text:
            return None
        
        user_text_lower = user_text.lower().strip().replace("netharite", "netherite")
        user_text_lower = self._normalize_item_text(user_text_lower)
        
        # Check cache
        if user_text_lower in self._item_cache:
            return self._item_cache[user_text_lower]
        
        # First try exact match in common items
        for item in self.common_items:
            if item.replace("_", " ") == user_text_lower or item == user_text_lower.replace(" ", "_"):
                self._item_cache[user_text_lower] = item
                return item

        # Fuzzy local match for misspellings/aliases
        fuzzy = self._resolve_fuzzy_local(user_text_lower)
        if fuzzy:
            self._item_cache[user_text_lower] = fuzzy
            return fuzzy
        
        # Try AI-powered matching for complex/named items
        item_id = self._resolve_with_ai(user_text)
        if item_id:
            self._item_cache[user_text_lower] = item_id
            return item_id
        
        return None
    
    def _resolve_with_ai(self, user_text):
        """Use AI to find the best matching item"""
        try:
            items_list = ", ".join(self.common_items[:100])  # Limit for prompt
            
            prompt = f"""User wants to give/spawn this item: "{user_text}"

Available Minecraft items (first 100): {items_list}

Find the BEST matching Minecraft item ID. Consider:
- Common names (e.g., "golden apple" -> "golden_apple")
- Alternate names (e.g., "coal block" -> "coal_block")
- Partial matches (e.g., "diamond sword" -> "diamond_sword")
- Modded items should match similar vanilla equivalents

Return ONLY the item ID (e.g., "golden_apple"), nothing else. If unsure, return the most likely item ID."""

            response, error = self.gateway.call_ai(prompt, user_text, temperature=0.3)
            
            if response:
                # Clean up response
                item = response.strip().strip('"').strip("'").lower()
                item = item.replace("netharite", "netherite")
                item = self._normalize_item_text(item)
                # Reject invalid outputs like "30" or single token garbage
                if not re.match(r"^[a-z][a-z0-9_]*$", item):
                    return None
                if item.isdigit():
                    return None
                # Validate it's a reasonable item name
                if item and len(item) > 1:
                    candidate = item.replace(" ", "_")
                    # If AI guessed near-match, snap to local closest known item.
                    exactish = self._resolve_fuzzy_local(candidate.replace("_", " "))
                    return exactish or candidate
        except:
            pass
        
        return None

    def _normalize_item_text(self, text):
        t = text.lower().strip()
        # Strip command words and amount prefixes.
        t = re.sub(r"^(give|gimme|spawn|summon|create|get|i want|i need|want|need)\s+", "", t)
        t = re.sub(r"^(me|us|player|myself)\s+", "", t)
        t = re.sub(r"^\d+\s+", "", t)
        t = re.sub(r"^(a|an|the|some)\s+", "", t)
        t = re.sub(r"\bof\b", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        # Common aliases
        alias = {
            "ender eye": "ender_eye",
            "eye ender": "ender_eye",
            "eye of ender": "ender_eye",
            "endereye": "ender_eye",
            "totem undying": "totem_of_undying",
            "god apple": "enchanted_golden_apple",
            "gold apple": "golden_apple",
        }
        if t in alias:
            return alias[t]
        return t

    def _resolve_fuzzy_local(self, normalized_text):
        if not normalized_text:
            return None
        candidates = {}
        for item in self.common_items:
            candidates[item] = item
            candidates[item.replace("_", " ")] = item
        keys = list(candidates.keys())
        # Use permissive threshold so minor spelling errors still map.
        match = difflib.get_close_matches(normalized_text, keys, n=1, cutoff=0.72)
        if match:
            return candidates[match[0]]
        return None


item_resolver = ItemResolver()

INTENT_SYSTEM_PROMPT = """You are a Minecraft command intent parser. Analyze player messages and extract the intended command.

Return ONLY valid JSON. No explanation.

CRITICAL: You can parse MULTIPLE items/requests in one message. Use "items" (array) instead of "item" for give commands.

Supported intents:
- set_time: Set time (value: day, night, noon, sunset, sunrise, or number)
- set_weather: Change weather (type: clear, rain, thunder)
- give_item: Give items. Use "items": [{"item": "id", "amount": n}, ...] for multiple items
- give_multi: Same as give_item but for multiple different items at once
- summon: Spawn mobs (entity: mob name, amount: number)
- summon_multi: Spawn multiple different mobs at once
- teleport: Teleport (destination: player/location/coordinates)
- locate: Find nearest structure without teleporting (structure: name)
- gamemode: Change mode (mode: creative/survival/adventure/spectator)
- heal: Heal player
- god_mode: God mode (enable: true/false)
- kill: Kill entities
- fly: Toggle fly (enable: true/false)
- feed: Feed player
- xp: Give XP (amount: number)
- effect: Potion effect
- scan: Scan terrain/area (returns info, NO command to execute)
- raw_command: Execute a direct command string (for plugin/mod commands). Use parameters: {"command":"..."}.

MULTIPLE COMMANDS: If player wants multiple things, return MULTIPLE intents in an array:
[{"intent": "give_item", "parameters": {"item": "diamond", "amount": 1}}, {"intent": "teleport", "parameters": {"destination": "village"}}]

For give_multi with multiple items:
{"intent": "give_multi", "parameters": {"items": [{"item": "diamond_block", "amount": 64}, {"item": "obsidian", "amount": 32}]}}

If player asks to scan, look around, describe area, terrain, what's around - use scan intent (NO command execution):
"scan the area" → {"intent": "scan", "parameters": {}, "confidence": 0.95}
"what's around me" → {"intent": "scan", "parameters": {}, "confidence": 0.95}
"describe this area" → {"intent": "scan", "parameters": {}, "confidence": 0.95}

KEY: Use exact Minecraft item IDs (diamond_sword, golden_apple, netherite_helmet, etc.)

If no command needed: {"intent": "none", "confidence": 0}

Examples:
"give me 1 diamond and 4 obsidian" → {"intent": "give_multi", "parameters": {"items": [{"item": "diamond", "amount": 1}, {"item": "obsidian", "amount": 4}]}, "confidence": 0.95}
"give me 64 dirt and tp me to village" → [{"intent": "give_item", "parameters": {"item": "dirt", "amount": 64}}, {"intent": "teleport", "parameters": {"destination": "village"}}]
"spawn 5 zombies and give me a diamond sword" → [{"intent": "summon", "parameters": {"entity": "zombie", "amount": 5}}, {"intent": "give_item", "parameters": {"item": "diamond_sword", "amount": 1}}]

"where is the nearest village" -> {"intent": "locate", "parameters": {"structure": "village"}}

Return JSON only:"""

SIMPLE_PATTERNS = {
    r"(make it|set|time|its?|it's?)\s*(day|morning|sunrise)": {"intent": "set_time", "params": {"value": "day"}},
    r"(make it|set|time|its?|it's?)\s*(night|dark|evening)": {"intent": "set_time", "params": {"value": "13000"}},
    r"(make it|set|time|its?|it's?)\s*noon": {"intent": "set_time", "params": {"value": "6000"}},
    r"(make it|set|time|its?|it's?)\s*(sunset|sundown)": {"intent": "set_time", "params": {"value": "12000"}},
    r"(clear|stop|make it)\s*(rain|weather)": {"intent": "set_weather", "params": {"type": "clear"}},
    r"(make it|set)\s*rain": {"intent": "set_weather", "params": {"type": "rain"}},
    r"(make it|set)\s*thunder": {"intent": "set_weather", "params": {"type": "thunder"}},
    r"save( all| everything)?": {"intent": "save", "params": {"scope": "all"}},
    r"(heal|restore)\s*(me|health)": {"intent": "heal", "params": {"target": "@a"}},
    r"(feed|satisfy)\s*(me|hunger)": {"intent": "feed", "params": {"target": "@a"}},
    r"(fly|flight)\s*(on|enable)?": {"intent": "fly", "params": {"target": "@a", "enable": True}},
    r"stop\s*(flying|fly)": {"intent": "fly", "params": {"target": "@a", "enable": False}},
    r"(creative|build)\s*mode": {"intent": "gamemode", "params": {"mode": "creative"}},
    r"(survival|survive)\s*mode": {"intent": "gamemode", "params": {"mode": "survival"}},
    r"(adventure)\s*mode": {"intent": "gamemode", "params": {"mode": "adventure"}},
    r"(spectator)\s*mode": {"intent": "gamemode", "params": {"mode": "spectator"}},
}

ITEM_MAP = {
    "diamond": "diamond", "diamonds": "diamond",
    "gold": "gold_ingot", "gold ingot": "gold_ingot",
    "iron": "iron_ingot", "iron ingot": "iron_ingot",
    "steak": "cooked_beef", "beef": "cooked_beef",
    "chicken": "chicken",
    "stick": "stick", "sticks": "stick",
    "wood": "oak_log", "logs": "oak_log",
    "cobble": "cobblestone", "cobblestone": "cobblestone",
    "torch": "torch", "torches": "torch",
    "apple": "apple", "bread": "bread",
    "sword": "diamond_sword", "pickaxe": "diamond_pickaxe",
    "book": "book", "bookshelf": "bookshelf",
    "potion": "potion", "potions": "potion",
    "arrow": "arrow", "arrows": "arrow",
    "bow": "bow", "crossbow": "crossbow",
    "trident": "trident",
    "horse": "horse", "wolf": "wolf", "cat": "cat",
    "cow": "cow", "pig": "pig", "sheep": "sheep",
    "golden apple": "golden_apple", "gold apple": "golden_apple", "apple of gold": "golden_apple",
    "enchanted golden apple": "enchanted_golden_apple", "enchanted apple": "enchanted_golden_apple",
}

STRUCTURE_MAP = {
    "village": "village",
    "nearest village": "village",
    "closest village": "village",
    "snowy village": "village_snowy",
    "snow village": "village_snowy",
    "showy village": "village_snowy",
    "desert village": "village_desert",
    "savanna village": "village_savanna",
    "taiga village": "village_taiga",
    "plains village": "village_plains",
    "pillager outpost": "pillager_outpost",
    "outpost": "pillager_outpost",
    "woodland mansion": "mansion",
    "mansion": "mansion",
    "desert temple": "desert_pyramid",
    "desert pyramid": "desert_pyramid",
    "pyramid": "desert_pyramid",
    "jungle temple": "jungle_temple",
    "witch hut": "swamp_hut",
    "swamp hut": "swamp_hut",
    "ocean monument": "ocean_monument",
    "monument": "ocean_monument",
    "stronghold": "stronghold",
    "fortress": "fortress",
    "nether fortress": "fortress",
    "bastion": "bastion",
    "end city": "end_city",
    "endcity": "end_city",
    "shipwreck": "shipwreck",
    "buried treasure": "buried_treasure",
    "ruined portal": "ruined_portal",
    "mineshaft": "mineshaft",
    "igloo": "igloo",
    "ocean ruin": "ocean_ruin",
}

MOB_MAP = {
    "zombie": "zombie", "zombies": "zombie",
    "skeleton": "skeleton", "skeletons": "skeleton",
    "creeper": "creeper", "creepers": "creeper",
    "spider": "spider", "spiders": "spider",
    "enderman": "enderman", "ender": "enderman",
    "pigman": "pig_zombie",
    "slime": "slime", "slimes": "slime",
    "phantom": "phantom",
    "witch": "witch",
    "ravager": "ravager",
    "vex": "vex",
    "hoglin": "hoglin",
    "pig": "pig", "cow": "cow", "sheep": "sheep",
    "chicken": "chicken",
    "wolf": "wolf", "cat": "cat",
    "horse": "horse", "donkey": "donkey",
    "villager": "villager",
    "iron_golem": "iron_golem",
    "snow_golem": "snow_golem",
}


class IntentEngine:
    def __init__(self):
        self.gateway = gateway
        self.memory = memory_engine
        self._commands_cache = None
        self._commands_cache_time = 0
        self._commands_cache_ttl = 10
    
    def parse(self, message, player_name, context=None):
        message_lower = message.lower().strip()

        forced_tp = self._force_tp_intent(message, player_name)
        if forced_tp:
            forced_tp.setdefault("raw", message)
            return forced_tp

        direct_result = self._try_direct_command(message)
        if direct_result:
            direct_result.setdefault("raw", message)
            return direct_result
        
        player = self.memory.get_player(player_name)
        last_target = player.get("last_target", player_name)
        
        resolved_message = self._resolve_pronouns(message_lower, player_name, last_target)
        
        pattern_result = self._try_patterns(resolved_message)
        if pattern_result:
            pattern_result["confidence"] = 0.95
            pattern_result.setdefault("raw", message)
            return pattern_result
        
        result = self._parse_with_ai(message, player_name, context or {})
        if isinstance(result, dict):
            result.setdefault("raw", message)
        if result and result.get("intent") in ["none", "unknown"]:
            suggestions = self._suggest_commands(message)
            if suggestions:
                result = {
                    "intent": "unknown",
                    "confidence": 0,
                    "source": "commands_catalog",
                    "command_suggestions": suggestions,
                    "raw": message
                }
        return result
    
    def _resolve_pronouns(self, message, player_name, last_target):
        # Avoid breaking teleport-style commands by injecting player name into destination
        if not re.search(r"\b(tp|teleport|warp|take me to|go to|travel to|find me the)\b", message):
            message = re.sub(r"\bme\b", player_name, message)
        message = re.sub(r"\bmy\b", f"{player_name}'s", message)
        message = re.sub(r"\bi\b", player_name, message)
        
        if re.search(r"\b(him|her)\b", message):
            message = re.sub(r"\bhim\b", last_target, message)
            message = re.sub(r"\bher\b", last_target, message)
        
        if re.search(r"\b(more|again)\b", message):
            if last_target:
                message = re.sub(r"\bmore\b", f"{last_target}", message)
                message = re.sub(r"\bagain\b", f"{last_target}", message)
        
        message = message.replace(" @a", " @a")
        message = message.replace(" @e", " @e")
        
        return message

    def _try_direct_command(self, message):
        if not message:
            return None
        raw = message.strip()
        if not raw:
            return None

        if raw.startswith("/"):
            command = raw.lstrip("/")
        else:
            lowered = f" {raw.lower()} "
            # If text looks conversational/natural-language, do NOT treat as raw command.
            natural_markers = [
                " me ", " my ", " i ", " please ", " can you ", " could you ",
                " nearest ", " closest ", " where ", " around ", " find ",
                " give me ", " tp me ", " teleport me ", " take me "
            ]
            if any(marker in lowered for marker in natural_markers):
                return None

            candidate = raw.split()[0].lower()
            known = set(command_catalog.get_commands())
            if candidate in known:
                # Require command-like second token to avoid "give me ..." as raw.
                parts = raw.split()
                if len(parts) >= 2:
                    second = parts[1].lower()
                    if second in {"me", "my", "to", "nearest", "closest"}:
                        return None
                command = raw
            elif ":" in candidate and candidate.split(":", 1)[1] in known:
                command = raw
            else:
                return None

        return {
            "intent": "raw_command",
            "parameters": {"command": command},
            "confidence": 0.95,
            "source": "direct"
        }

    def _force_tp_intent(self, message, player_name):
        if not message:
            return None
        raw = str(message).strip()
        if not raw:
            return None
        if not re.search(r"\b(tp|teleport)\b", raw, re.IGNORECASE):
            return None

        # Convert "tp/teleport ... to <dest>" style messages into teleport intent.
        m = re.search(r"\b(?:tp|teleport)\b\s*(?:me\s*)?(?:to\s*)?(.+)$", raw, re.IGNORECASE)
        if not m:
            return None
        destination = m.group(1).strip() if m.group(1) else ""
        destination = self._clean_destination(destination, player_name)
        if not destination:
            return None

        return {
            "intent": "teleport",
            "parameters": {"target": "@a", "destination": destination},
            "confidence": 0.98,
            "source": "forced_tp_keyword"
        }
    
    def _try_patterns(self, message):
        # Simple patterns first
        for pattern, result in SIMPLE_PATTERNS.items():
            if re.search(pattern, message):
                return {
                    "intent": result["intent"],
                    "parameters": result["params"],
                    "confidence": 0.9,
                    "source": "pattern"
                }
        
        # Multi-item give patterns (e.g., "give me a pickaxe and a sword")
        if re.search(r"\b(give|gimme)\b", message):
            cleaned = re.sub(r"^(give me|give|gimme)\s+", "", message, flags=re.IGNORECASE).strip()
            if " and " in cleaned or "," in cleaned:
                parts = re.split(r"\s+and\s+|,\s*", cleaned)
                items = []
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    part = re.sub(r"^(a|an|the|some)\s+", "", part, flags=re.IGNORECASE).strip()
                    amount = 1
                    amt_match = re.match(r"(\d+)\s+(.+)", part)
                    if amt_match:
                        amount = min(int(amt_match.group(1)), 64)
                        part = amt_match.group(2).strip()
                    item = item_resolver.resolve(part)
                    if item:
                        items.append({"item": item, "amount": amount})
                if len(items) >= 2:
                    return {
                        "intent": "give_multi",
                        "parameters": {"items": items, "target": "@a"},
                        "confidence": 0.9,
                        "source": "pattern"
                    }
        
        # For give/spawn requests, try AI resolver for better item matching
        give_keywords = ["give", "spawn", "want", "need", "get", "receive", "have", "can i get", "i want", "i need", "gimme", "summon", "create"]
        if any(kw in message.lower() for kw in give_keywords):
            # Check for amount
            amount = 1
            num_match = re.search(r"(\d+)\s+(?:of\s+)?(?:the\s+)?(?:a\s+)?(?:some\s+)?(.+)", message, re.IGNORECASE)
            if num_match:
                amount = min(int(num_match.group(1)), 64)
            elif "some" in message.lower() or "a " in message.lower():
                amount = 5
            elif "many" in message.lower() or "lots" in message.lower():
                amount = 32
            
            # Resolve item phrase (not the whole sentence) and tolerate misspellings.
            item_phrase = self._extract_item_phrase(message)
            item = item_resolver.resolve(item_phrase or message)
            if item:
                return {
                    "intent": "give_item",
                    "parameters": {"item": item, "amount": amount, "target": "@a"},
                    "confidence": 0.85,
                    "source": "ai_resolver"
                }
        
        # Summon - use AI for entity resolution
        if any(kw in message.lower() for kw in ["spawn", "summon", "create", "make"]):
            # Check for amount
            amount = 1
            num_match = re.search(r"(\d+)\s+(?:of\s+)?(.+)", message, re.IGNORECASE)
            if num_match and num_match.group(1).isdigit():
                amount = min(int(num_match.group(1)), 20)
            
            # Try AI resolver for entity
            entity = item_resolver.resolve(message)
            if entity:
                return {
                    "intent": "summon",
                    "parameters": {"entity": entity, "amount": amount},
                    "confidence": 0.8,
                    "source": "ai_resolver"
                }
        
        # Teleport patterns
        tp_match = re.search(r"(tp|teleport|warp)\s+(me\s+)?(to\s+)?(.+?)(?:\s*$|\s+please)", message)
        if tp_match:
            destination = tp_match.group(4).strip() if tp_match.group(4) else None
            if destination:
                destination = self._clean_destination(destination, player_name)
            return {
                "intent": "teleport",
                "parameters": {"target": "@a", "destination": destination} if destination else {"target": "@a"},
                "confidence": 0.85 if destination else 0.5,
                "source": "pattern"
            }
        
        # Location keywords
        if re.search(r"(go\s+to|travel\s+to|take\s+me\s+to|find\s+me\s+the|take me to)", message):
            dest_match = re.search(r"(go\s+to|travel\s+to|take\s+me\s+to|find\s+me\s+the)\s+(.+?)(?:\s*$|\s+please)", message)
            if dest_match:
                destination = self._clean_destination(dest_match.group(2).strip(), player_name)
                return {
                    "intent": "teleport",
                    "parameters": {"target": "@a", "destination": destination},
                    "confidence": 0.8,
                    "source": "pattern"
                }
        
        # Locate requests (where is/nearest/closest)
        if re.search(r"\b(where is|nearest|closest|locate)\b", message):
            fuzzy_structure = self._resolve_structure_fuzzy(message)
            if fuzzy_structure:
                return {
                    "intent": "locate",
                    "parameters": {"structure": fuzzy_structure},
                    "confidence": 0.88,
                    "source": "pattern"
                }
            for struct_name in STRUCTURE_MAP.keys():
                if struct_name in message:
                    return {
                        "intent": "locate",
                        "parameters": {"structure": struct_name},
                        "confidence": 0.9,
                        "source": "pattern"
                    }
        
        # Structure names
        fuzzy_structure = self._resolve_structure_fuzzy(message)
        if fuzzy_structure:
            return {
                "intent": "teleport",
                "parameters": {"target": "@a", "destination": fuzzy_structure},
                "confidence": 0.85,
                "source": "pattern"
            }
        for struct_name, struct_id in STRUCTURE_MAP.items():
            if struct_name in message:
                return {
                    "intent": "teleport",
                    "parameters": {"target": "@a", "destination": struct_name},
                    "confidence": 0.9,
                    "source": "pattern"
                }
        
        return None
    
    def _clean_destination(self, destination, player_name):
        if not destination:
            return destination
        dest = destination.strip()
        dest = re.sub(rf"^{re.escape(player_name)}\s+", "", dest, flags=re.IGNORECASE)
        dest = re.sub(rf"\s+{re.escape(player_name)}$", "", dest, flags=re.IGNORECASE)
        dest = re.sub(r"^to\s+", "", dest, flags=re.IGNORECASE)
        return dest.strip()

    def _extract_item_phrase(self, message):
        msg = message.lower().strip()
        msg = re.sub(r"^(can you|please)\s+", "", msg)
        msg = re.sub(r"^(give|gimme|get|i want|i need)\s+", "", msg)
        msg = re.sub(r"^(me|us)\s+", "", msg)
        msg = re.sub(r"^(\d+)\s+", "", msg)
        msg = re.sub(r"^(a|an|the|some)\s+", "", msg)
        # keep content before conjunction or action switch
        msg = re.split(r"\b(and|then|also|tp|teleport|locate|where)\b", msg)[0].strip()
        return msg

    def _resolve_structure_fuzzy(self, message):
        normalized = re.sub(r"[_-]+", " ", message.lower())
        normalized = re.sub(r"\b(locat(?:e|ing)?|where|is|the|nearest|closest|find|me|to|a|an)\b", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        tokens = re.findall(r"[a-z]+", normalized)
        if not tokens:
            return None
        text = " ".join(tokens)
        keys = list(STRUCTURE_MAP.keys())
        # Prefer explicit key containment first (specific phrases like "desert village").
        for key in sorted(keys, key=len, reverse=True):
            if key in text:
                return key
        m = difflib.get_close_matches(text, keys, n=1, cutoff=0.72)
        if m:
            return m[0]
        # also check short likely phrases from tail
        for n in [3, 2]:
            if len(tokens) >= n:
                tail = " ".join(tokens[-n:])
                m2 = difflib.get_close_matches(tail, keys, n=1, cutoff=0.72)
                if m2:
                    return m2[0]
        return None
    
    def _parse_with_ai(self, message, player_name, context):
        player = self.memory.get_player(player_name)
        
        context_str = ""
        if context:
            context_str = f"\nServer context: {json.dumps(context)}"
        
        prompt = f"""Player: {player_name}
Message: {message}{context_str}
Available dynamic command roots: {command_catalog.build_prompt_hint(80)}

IMPORTANT: The player may describe items or mobs in natural language. Use AI to determine the best Minecraft item/entity ID that matches their description.
If the user clearly asks for a plugin/mod command, return intent raw_command with command text.

Return JSON:"""
        
        response, error = self.gateway.call_ai(INTENT_SYSTEM_PROMPT, prompt, temperature=0.3)
        
        if error:
            return {"intent": "error", "parameters": {"error": error}, "confidence": 0}
        
        try:
            # Try to find JSON array or object in response - more robust matching
            json_match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', response)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
                
                # Check if we got multiple intents (array)
                if isinstance(result, list):
                    if len(result) == 1:
                        # Single result in array, unwrap it
                        result = result[0]
                        result["source"] = "ai"
                    else:
                        # Multiple commands
                        return {"intent": "multi", "commands": result, "confidence": 0.95, "source": "ai"}
                else:
                    result["source"] = "ai"
                
                # If the AI returned an item or entity, try to verify it exists
                if result.get("intent") in ["give_item", "summon"]:
                    params = result.get("parameters", {})
                    if "item" in params:
                        result["item_resolved"] = True
                    if "entity" in params:
                        result["entity_resolved"] = True
                
                return result
        except Exception as e:
            print(f"[IntentEngine] JSON parse error: {e}")
        
        return {"intent": "none", "confidence": 0, "source": "ai", "raw": message}

    def _suggest_commands(self, message):
        return command_catalog.suggest(message, limit=5)

    def _load_commands_catalog(self):
        now = time.time()
        if self._commands_cache and now - self._commands_cache_time < self._commands_cache_ttl:
            return self._commands_cache
        profile_path = self._get_current_profile_path()
        if not profile_path:
            self._commands_cache = []
            self._commands_cache_time = now
            return self._commands_cache
        commands_path = os.path.join(profile_path, "commands.txt")
        if not os.path.exists(commands_path):
            self._commands_cache = []
            self._commands_cache_time = now
            return self._commands_cache
        commands = []
        try:
            with open(commands_path, "r", encoding="utf-8") as f:
                for line in f:
                    raw = line.strip()
                    if not raw:
                        continue
                    if raw.startswith("#") or raw.startswith("//"):
                        continue
                    name = raw.split()[0].lstrip("/")
                    commands.append({"name": name.lower(), "line": raw})
        except Exception:
            commands = []
        self._commands_cache = commands
        self._commands_cache_time = now
        return commands

    def _get_current_profile_path(self):
        try:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            config_path = os.path.join(data_dir, "current_profile.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("path")
        except Exception:
            pass
        return None


intent_engine = IntentEngine()
