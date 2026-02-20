import json
import re
from core.gateway import gateway
from core.memory_engine import memory_engine


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
        
        user_text_lower = user_text.lower().strip()
        
        # Check cache
        if user_text_lower in self._item_cache:
            return self._item_cache[user_text_lower]
        
        # First try exact match in common items
        for item in self.common_items:
            if item.replace("_", " ") == user_text_lower or item == user_text_lower.replace(" ", "_"):
                self._item_cache[user_text_lower] = item
                return item
        
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
                # Validate it's a reasonable item name
                if item and len(item) > 1:
                    return item.replace(" ", "_")
        except:
            pass
        
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
- gamemode: Change mode (mode: creative/survival/adventure/spectator)
- heal: Heal player
- god_mode: God mode (enable: true/false)
- kill: Kill entities
- fly: Toggle fly (enable: true/false)
- feed: Feed player
- xp: Give XP (amount: number)
- effect: Potion effect
- scan: Scan terrain/area (returns info, NO command to execute)

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
    "end city": "endcity",
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
    
    def parse(self, message, player_name, context=None):
        message_lower = message.lower().strip()
        
        player = self.memory.get_player(player_name)
        last_target = player.get("last_target", player_name)
        
        resolved_message = self._resolve_pronouns(message_lower, player_name, last_target)
        
        pattern_result = self._try_patterns(resolved_message)
        if pattern_result:
            pattern_result["confidence"] = 0.95
            return pattern_result
        
        return self._parse_with_ai(message, player_name, context or {})
    
    def _resolve_pronouns(self, message, player_name, last_target):
        message = message.replace("me", player_name)
        message = message.replace("my", f"{player_name}'s")
        message = message.replace("i ", f"{player_name} ")
        
        if "him" in message or "her" in message:
            message = message.replace("him", last_target)
            message = message.replace("her", last_target)
        
        if "more" in message or "again" in message:
            if last_target:
                message = message.replace("more", f"{last_target}")
                message = message.replace("again", f"{last_target}")
        
        message = message.replace(" @a", " @a")
        message = message.replace(" @e", " @e")
        
        return message
    
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
            
            # Try AI resolver
            item = item_resolver.resolve(message)
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
                return {
                    "intent": "teleport",
                    "parameters": {"target": "@a", "destination": dest_match.group(2).strip()},
                    "confidence": 0.8,
                    "source": "pattern"
                }
        
        # Structure names
        for struct_name, struct_id in STRUCTURE_MAP.items():
            if struct_name in message:
                return {
                    "intent": "teleport",
                    "parameters": {"target": "@a", "destination": struct_name},
                    "confidence": 0.9,
                    "source": "pattern"
                }
        
        return None
    
    def _parse_with_ai(self, message, player_name, context):
        player = self.memory.get_player(player_name)
        
        context_str = ""
        if context:
            context_str = f"\nServer context: {json.dumps(context)}"
        
        prompt = f"""Player: {player_name}
Message: {message}{context_str}

IMPORTANT: The player may describe items or mobs in natural language. Use AI to determine the best Minecraft item/entity ID that matches their description.

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
        
        return {"intent": "none", "confidence": 0, "source": "ai"}


intent_engine = IntentEngine()
