import logging
from typing import TYPE_CHECKING

from core.repositories.conversation_repository import ConversationRepository
from core.repositories.memory_repository import MemoryRepository
from core.repositories.house_repository import HouseRepository
from core.background_queue import BackgroundQueue, BackgroundTask

from core.builders.thread_builder import SimpleThreadBuilder
from core.builders.intent_extractor import IntentExtractor
from core.builders.device_context_builder import DeviceContextBuilder
from core.builders.house_context_builder import HouseContextBuilder
from core.builders.user_memory_builder import UserMemoryBuilder
from core.builders.conflict_resolver import ConflictResolver
from core.builders.token_optimizer import TokenOptimizer
from core.builders.prompt_builder import PromptBuilder

if TYPE_CHECKING:
    from core.device_service import DeviceService
    from core.event_bus import EventBus
    from pathlib import Path

logger = logging.getLogger(__name__)

class ContextBuilder:
    """
    ContextCoordinator: Orchestrates the Read/Write Path of the context pipeline.
    Maintains backward compatibility for the `build_context` API.
    """
    def __init__(self, device_service: "DeviceService", event_bus: "EventBus", db_path: "Path"):
        db_str = str(db_path)
        # Initialize Repositories
        self.conv_repo = ConversationRepository(db_str)
        self.memory_repo = MemoryRepository(db_str)
        self.house_repo = HouseRepository(device_service, None) # Assuming state_manager is not strictly needed for house modes
        
        # Initialize Write Path Queue
        self.queue = BackgroundQueue(self.memory_repo, self.conv_repo)
        
        # Initialize Read Path Builders
        self.thread_builder = SimpleThreadBuilder()
        self.intent_extractor = IntentExtractor()
        self.device_context_builder = DeviceContextBuilder(device_service, None)
        self.house_context_builder = HouseContextBuilder(self.house_repo)
        self.user_memory_builder = UserMemoryBuilder(self.memory_repo)
        self.conflict_resolver = ConflictResolver()
        self.token_optimizer = TokenOptimizer()
        self.prompt_builder = PromptBuilder()

    def save_message(self, session_id: str, role: str, content: str, 
                     platform: str = 'unknown', user_id: str = None, 
                     message_id: str = None, reply_to_message_id: str = None):
        """
        Write Path: Saves message to repository and enqueues background tasks.
        Maintains backward compatibility.
        """
        count = self.conv_repo.save_message(
            session_id, role, content, platform, user_id, message_id, reply_to_message_id
        )
        
        import asyncio
        if count > 0 and count % 10 == 0:
            asyncio.create_task(self.queue.enqueue(BackgroundTask(
                type="summary", session_id=session_id, payload={}
            )))
            
        if role == "user":
            asyncio.create_task(self.queue.enqueue(BackgroundTask(
                type="memory", session_id=session_id, payload={"content": content}
            )))

    def build_context(self, session_id: str = "default", query: str = "") -> str:
        """
        Read Path: Coordinates the 9-step pipeline to generate the Prompt context.
        """
        # 1 & 2. Conversation Thread (includes Storage read and Thread Builder)
        recent_messages = self.conv_repo.get_recent_messages(session_id, limit=100, since_minutes=30)
        working_memory = self.thread_builder.build(recent_messages)
        
        # 3. Summary Injection
        summary = self.memory_repo.get_latest_summary(session_id) or {}
        
        # 4. Device Context (Intent Extraction + Device Builder)
        intent = self.intent_extractor.extract(query)
        device_state = self.device_context_builder.build(intent)
        
        # 5. House Context
        house_memory = self.house_context_builder.build()
        
        # 6. User Memory
        user_memory = self.user_memory_builder.build(session_id) # Using session_id as user_id for now
        
        # Active Automations
        automations = self.house_repo.get_active_automations()
        
        # 7. Conflict Resolver
        resolved_context = self.conflict_resolver.resolve(
            current_request=query,
            working_memory=working_memory,
            device_state=device_state,
            summary=summary,
            user_memory=user_memory,
            house_memory=house_memory,
            automations=automations
        )
        
        # 8. Token Budget Optimizer
        optimized_context = self.token_optimizer.optimize(resolved_context["resolved_context"])
        
        # Include decision graph in final payload for auditing
        optimized_context["decision_graph"] = resolved_context["decision_graph"]
        
        # 9. Prompt Builder
        final_prompt = self.prompt_builder.build(optimized_context)
        
        return final_prompt
