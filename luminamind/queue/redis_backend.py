import json
import redis
from typing import Optional
from datetime import datetime

from .task_queue import Task, TaskStatus, Priority, QueueBackend, QueueMetrics, TaskQueue


class RedisBackend(QueueBackend):
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.queue_key = "luminamind:queue:tasks"
        self.priority_key = "luminamind:queue:priority"
        self.running_key = "luminamind:queue:running"
        self.dead_letter_key = "luminamind:queue:dead_letter"
        self.meta_key = "luminamind:queue:meta"
    
    def _task_to_dict(self, task: Task) -> dict:
        return {
            "id": task.id,
            "type": task.type,
            "payload": task.payload,
            "priority": task.priority.value,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "attempts": task.attempts,
            "max_attempts": task.max_attempts,
            "error": task.error,
            "idempotency_key": task.idempotency_key,
        }
    
    def _dict_to_task(self, data: dict) -> Task:
        task = Task()
        task.id = data["id"]
        task.type = data["type"]
        task.payload = data["payload"]
        task.priority = Priority(data["priority"])
        task.status = TaskStatus(data["status"])
        task.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("scheduled_at"):
            task.scheduled_at = datetime.fromisoformat(data["scheduled_at"])
        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])
        task.attempts = data["attempts"]
        task.max_attempts = data["max_attempts"]
        task.error = data.get("error")
        task.idempotency_key = data.get("idempotency_key")
        return task
    
    def enqueue(self, task: Task, delay_seconds: int = 0) -> str:
        data = self._task_to_dict(task)
        data["status"] = TaskStatus.PENDING.value
        
        if delay_seconds > 0:
            # Delayed task: store in sorted set with score = execute_at timestamp
            execute_at = datetime.utcnow().timestamp() + delay_seconds
            self.redis.zadd(self.queue_key, {task.id: execute_at})
            self.redis.hset(self.meta_key, task.id, json.dumps(data))
        else:
            # Immediate task: push to priority queue
            self.redis.hset(self.meta_key, task.id, json.dumps(data))
            # Higher priority = higher score (for zpopmax to return highest priority first)
            score = (task.priority.value * 1e9) - task.created_at.timestamp()
            self.redis.zadd(self.priority_key, {task.id: score})
        
        return task.id
    
    def dequeue(self, timeout_seconds: int = 0) -> Optional[Task]:
        # Check delayed tasks first
        now = datetime.utcnow().timestamp()
        due = self.redis.zrangebyscore(self.queue_key, 0, now, start=0, num=1)
        if due:
            task_id = due[0]
            data = self.redis.hget(self.meta_key, task_id)
            if data:
                task = self._dict_to_task(json.loads(data))
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                self.redis.hset(self.meta_key, task_id, json.dumps(self._task_to_dict(task)))
                self.redis.zrem(self.queue_key, task_id)
                self.redis.zrem(self.priority_key, task_id)
                self.redis.hset(self.running_key, task_id, json.dumps(self._task_to_dict(task)))
                return task
        
        # Get from priority queue
        result = self.redis.zpopmax(self.priority_key, 1)
        if not result:
            return None
        
        task_id = result[0][0]
        data = self.redis.hget(self.meta_key, task_id)
        if not data:
            return None
        
        task = self._dict_to_task(json.loads(data))
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        self.redis.hset(self.meta_key, task_id, json.dumps(self._task_to_dict(task)))
        self.redis.hset(self.running_key, task_id, json.dumps(self._task_to_dict(task)))
        return task
    
    def ack(self, task_id: str) -> None:
        self.redis.hdel(self.meta_key, task_id)
        self.redis.hdel(self.running_key, task_id)
    
    def nack(self, task_id: str, error: str) -> None:
        data = self.redis.hget(self.running_key, task_id)
        if not data:
            # Fallback: try meta_key (for tasks not in running)
            data = self.redis.hget(self.meta_key, task_id)
            if not data:
                return
        
        task = self._dict_to_task(json.loads(data))
        task.attempts += 1
        task.error = error
        
        if task.attempts >= task.max_attempts:
            task.status = TaskStatus.DEAD_LETTER
            self.redis.hset(self.meta_key, task_id, json.dumps(self._task_to_dict(task)))
            self.redis.hdel(self.running_key, task_id)
            self.redis.zadd(self.dead_letter_key, {task_id: datetime.utcnow().timestamp()})
        else:
            # Re-queue with delay
            task.status = TaskStatus.PENDING
            task.started_at = None
            self.redis.hset(self.meta_key, task_id, json.dumps(self._task_to_dict(task)))
            self.redis.hdel(self.running_key, task_id)
            execute_at = datetime.utcnow().timestamp() + (2 ** task.attempts)  # exponential backoff
            self.redis.zadd(self.queue_key, {task_id: execute_at})
    
    def cancel(self, task_id: str) -> bool:
        # Check running first, then pending
        data = self.redis.hget(self.running_key, task_id)
        if not data:
            data = self.redis.hget(self.meta_key, task_id)
        if not data:
            return False
        
        task = self._dict_to_task(json.loads(data))
        task.status = TaskStatus.CANCELLED
        self.redis.hset(self.meta_key, task_id, json.dumps(self._task_to_dict(task)))
        self.redis.hdel(self.running_key, task_id)
        self.redis.zrem(self.queue_key, task_id)
        self.redis.zrem(self.priority_key, task_id)
        return True
    
    def get_status(self, task_id: str) -> TaskStatus:
        data = self.redis.hget(self.meta_key, task_id)
        if not data:
            return TaskStatus.PENDING
        return TaskStatus(json.loads(data)["status"])
    
    def get_metrics(self) -> QueueMetrics:
        pending = self.redis.zcount(self.priority_key, "-inf", "+inf")
        running = self.redis.hlen(self.running_key)
        dead_letter = self.redis.zcount(self.dead_letter_key, "-inf", "+inf")
        return QueueMetrics(
            pending=pending,
            running=running,
            completed=0,  # completed tasks are deleted
            failed=0,
            dead_letter=dead_letter,
        )