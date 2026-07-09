import asyncio
import logging
from typing import Dict, Any, Callable, List
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
        self.batch_size = 10
        self.batch_timeout = 2.0

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
            batch = []
            try:
                # Wait for at least one task
                first_task = await self._queue.get()
                if first_task is None:
                    self._queue.task_done()
                    break
                batch.append(first_task)
                
                # Try to collect more up to batch_size within batch_timeout
                end_time = asyncio.get_event_loop().time() + self.batch_timeout
                while len(batch) < self.batch_size:
                    timeout = end_time - asyncio.get_event_loop().time()
                    if timeout <= 0:
                        break
                    try:
                        task = await asyncio.wait_for(self._queue.get(), timeout=timeout)
                        if task is None:
                            self._queue.task_done()
                            # We put it back so other workers can stop too
                            await self._queue.put(None)
                            break
                        batch.append(task)
                    except asyncio.TimeoutError:
                        break

                if batch:
                    await self._process_batch(worker_id, batch)

            except Exception as e:
                logger.error(f"Worker {worker_id} error in batch collection: {e}")
            finally:
                for _ in batch:
                    self._queue.task_done()

    async def _process_batch(self, worker_id: int, batch: List[BackgroundTask]):
        logger.info(f"Worker {worker_id} processing batch of {len(batch)} tasks")
        
        summaries = []
        preferences = []
        
        for task in batch:
            try:
                if task.type == 'summary':
                    summary_data = await self._process_summary_logic(task)
                    if summary_data:
                        summaries.append(summary_data)
                elif task.type == 'memory':
                    pref_data = await self._process_memory_logic(task)
                    if pref_data:
                        preferences.append(pref_data)
                else:
                    logger.warning(f"Worker {worker_id} ignoring unknown task type: {task.type}")
            except Exception as e:
                logger.error(f"Worker {worker_id} error processing task {task.type}: {e}")

        # Batch write to DB to save I/O
        if hasattr(self._memory_repo, 'save_summaries_batch') and summaries:
            self._memory_repo.save_summaries_batch(summaries)
        elif summaries:
            for s in summaries:
                self._memory_repo.save_summary(**s)
                
        if hasattr(self._memory_repo, 'save_preferences_batch') and preferences:
            self._memory_repo.save_preferences_batch(preferences)
        elif preferences:
            for p in preferences:
                self._memory_repo.save_preference(**p)

    async def _process_summary_logic(self, task: BackgroundTask) -> Dict:
        session_id = task.session_id
        await asyncio.sleep(0.5) # Simulate LLM call
        return {
            'session_id': session_id,
            'summary_text': "Ngữ cảnh đã được thu gọn (Mock Queue).",
            'version': 1,
            'start_msg': "N/A",
            'end_msg': "N/A",
            'model': "gpt-4o-mini",
            'created_by': "SummaryWorker"
        }

    async def _process_memory_logic(self, task: BackgroundTask) -> Dict:
        session_id = task.session_id
        content = task.payload.get('content', '')
        await asyncio.sleep(0.5) # Simulate LLM call
        
        if "hãy nhớ" in content.lower():
            return {
                'user_id': session_id,
                'key': "user_instruction",
                'value': content,
                'importance': 5,
                'confidence': 0.9,
                'source': "user_explicit"
            }
        return {}
