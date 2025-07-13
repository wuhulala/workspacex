import asyncio
import traceback
from abc import abstractmethod

from workspacex.utils.logger import logger


class BaseTask:
    def __init__(self, id: str):
        self.id = id
        self.status: str = "pending"
        self.error_count: int = 0
        self.error_infos: list[str] = []
        self.total_subtasks: int = 0

    def get_status(self):
        return self.status

    def add_error(self, error_info: str):
        self.error_count += 1
        self.error_infos.append(error_info)

    def get_error_count(self):
        return self.error_count

    def get_status_info(self):
        if self.total_subtasks == 0:
            return f"finished"
        elif self.total_subtasks == self.error_count:
            return f"failed"
        elif self.error_count > 0:
            return f"part_failed"
        else:
            return f"finished"

    def set_total_subtasks(self, total_subtasks: int):
        self.total_subtasks = total_subtasks


class BaseTaskExecutor:
    def __init__(self, name: str, max_concurrent_tasks: int = 1):
        self.name = name
        self.task_queue = asyncio.Queue()
        self.running_tasks = {}
        self.tasks = []
        self.max_concurrent_tasks = max_concurrent_tasks

    async def add_task(self, task: BaseTask):
        self.task_queue.put_nowait(task)
        self.tasks.append(task)

    async def start(self):
        asyncio.create_task(self._process_task())

    async def get_task_status(self, extract_task_id: str):
        for task in self.tasks:
            if task.id == extract_task_id:
                return {"status": task.get_status()}
        return {"status": "not found"}

    async def stop(self):
        self.task_queue.put_nowait(None)

    async def get_task(self, extract_task_id: str):
        for task in self.tasks:
            if task.id == extract_task_id:
                return task
        return None

    async def cancel_task(self, extract_task_id: str):
        if extract_task_id in self.running_tasks:
            try:
                self.running_tasks[extract_task_id].cancel()
            except Exception as e:
                logger.warning(f"[TaskExecutor#{self.name}]🛑 Cancel task#{extract_task_id} failed, error: {e}")

            task = self.get_task(extract_task_id)
            if task:
                task.status = "canceled"
            self.running_tasks.pop(extract_task_id, None)
            logger.info(f"[TaskExecutor]🛑 Task#{extract_task_id} canceled successfully")

    async def wait_for_all_tasks(self):
        while not self.task_queue.empty():
            await asyncio.sleep(1)

    async def _process_task(self):
        """
        Process tasks in the queue.
        """
        while True:
            if len(self.running_tasks) >= self.max_concurrent_tasks:
                await asyncio.sleep(10)
                logger.info(f"[TaskExecutor#{self.name}]⏳ Waiting, running tasks: {len(self.running_tasks)}")
                continue
            task = await self.task_queue.get()
            if task is None:
                logger.info(f"[TaskExecutor#{self.name}]🛑 Stop signal received, exiting task processor.")
                break  # Stop signal
            logger.info(f"[TaskExecutor#{self.name}]📥 Got task#{task.id}")
            if task.id in self.running_tasks:
                logger.warning(f"[TaskExecutor]⚠️ Task#{task.id} is already running, skipping.")
                continue
            task.status = "running"
            logger.info(f"[TaskExecutor]🟢 Task#{task.id} started.")
            asyncio_task = asyncio.create_task(self._run(task), name=f"extract_task_{task.id}")

            def _on_task_done(t: asyncio.Task) -> None:
                """
                Callback function to remove the finished task from running_tasks.
                Args:
                    t (asyncio.Task): The finished asyncio task.
                Returns:
                    None
                """
                try:
                    # 触发异常抛出（如果有的话）
                    t.result()
                except Exception as e:
                    logger.error(f"[TaskExecutor]🚨 Task#{t.get_name()} failed: {e} \n trace is {traceback.print_exc()}")
                    task.status = "failed"
                else:
                    task.status = task.get_status_info()
                    logger.info(f"[TaskExecutor]✅ Task#{task.id} finished with status: {task.status}")
                self.running_tasks.pop(task.id, None)

            asyncio_task.add_done_callback(_on_task_done)
            self.running_tasks[task.id] = asyncio_task

    @abstractmethod
    async def _run(self, task: BaseTask):
        pass
