import asyncio
import logging
from typing import Dict, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class BackgroundTask:
    type: str  # e.g., 'summary', 'memory'
    session_id: str
    payload: Dict[str, Any]

class BackgroundQueue:
    def __init__(self, memory_repo, conversation_repo):
        self._queue = asyncio.Queue()
        self._workers = []
        self._memory_repo = memory_repo
        self._conversation_repo = conversation_repo

    async def start_workers(self, num_workers: int = 2):
        for i in range(num_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self._workers.append(task)
        logger.info(f"Started {num_workers} background workers for AI Context tasks.")

    async def stop_workers(self):
        for _ in self._workers:
            await self.enqueue(None) # Sentinel to stop
        await asyncio.gather(*self._workers, return_exceptions=True)

    async def enqueue(self, task: BackgroundTask):
        await self._queue.put(task)

    async def _worker_loop(self, worker_id: int):
        while True:
            task: BackgroundTask = await self._queue.get()
            if task is None:
                self._queue.task_done()
                break
                
            try:
                if task.type == 'summary':
                    await self._process_summary(task)
                elif task.type == 'memory':
                    await self._process_memory(task)
                else:
                    logger.warning(f"Worker {worker_id} ignoring unknown task type: {task.type}")
            except Exception as e:
                logger.error(f"Worker {worker_id} error processing task {task.type}: {e}")
            finally:
                self._queue.task_done()

    async def _process_summary(self, task: BackgroundTask):
        session_id = task.session_id
        logger.info(f"[SummaryWorker] Processing summary for {session_id}")
        await asyncio.sleep(0.5) # Simulate LLM call
        # Mock logic for now
        self._memory_repo.save_summary(
            session_id=session_id,
            summary_text="Ngữ cảnh đã được thu gọn (Mock Queue).",
            version=1,
            start_msg="N/A",
            end_msg="N/A",
            model="gpt-4o-mini",
            created_by="SummaryWorker"
        )

    async def _process_memory(self, task: BackgroundTask):
        session_id = task.session_id
        content = task.payload.get('content', '')
        logger.info(f"[MemoryWorker] Extracting memory for {session_id} from content")
        await asyncio.sleep(0.5) # Simulate LLM call
        
        # Promotion Policy Check (Mock implementation for Sprint 10)
        # Condition: "Hãy nhớ rằng..." explicitly used, OR repeated >= 3 times, OR preference > 7 days
        if "hãy nhớ" in content.lower():
            # Explicit instruction -> high confidence
            self._memory_repo.save_preference(
                user_id=session_id,
                key="user_instruction",
                value=content,
                importance=5,
                confidence=0.9,
                source="user_explicit"
            )
            logger.info(f"[MemoryWorker] Promoted explicit memory for {session_id}")
        else:
            # Low confidence extraction
            pass
