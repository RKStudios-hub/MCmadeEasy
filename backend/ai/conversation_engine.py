import time
import random
from core.memory_engine import memory_engine
from ai.response_engine import response_engine

class ConversationEngine:
    def __init__(self):
        self.memory = memory_engine
        self.response_engine = response_engine
        self.last_initiation = 0
        self.initiation_cooldown = 60
        self.greeting_cooldown = 30
    
    def should_respond(self):
        return random.random() > 0.1
    
    def can_initiate(self):
        now = time.time()
        if now - self.last_initiation > self.initiation_cooldown:
            self.last_initiation = now
            return True
        return False
    
    def process_message(self, message, player_name, intent_result=None, context=None):
        if not self.should_respond():
            return None
        
        self.memory.increment_conversation(player_name)
        
        if intent_result and intent_result.get("intent") != "none" and intent_result.get("intent") != "unknown":
            self.memory.set_last_intent(player_name, intent_result.get("intent"), intent_result.get("parameters", {}).get("target"))
        
        response = self.response_engine.generate(
            message, 
            player_name, 
            intent_result, 
            context
        )
        
        self.memory.add_conversation(player_name, message, response)
        
        return response
    
    def should_greet(self, player_name):
        player = self.memory.get_player(player_name)
        return player.get("conversation_count", 0) <= 1
    
    def initiate(self, trigger, player_name=None, context=None):
        if not self.can_initiate():
            return None
        
        response = self.response_engine.generate_autonomous(trigger, player_name, context)
        return response
    
    def get_active_players(self):
        now = time.time()
        active = []
        for name, data in self.memory.player_memories.items():
            if now - data.get("last_seen", 0) < 300:
                active.append(name)
        return active


conversation_engine = ConversationEngine()
