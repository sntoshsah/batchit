from aiokafka import AIOKafkaConsumer
import json
import asyncio

class KafkaConsumerService:
    _instances = {}  # singleton per topic

    def __new__(cls, topic, bootstrap_servers="localhost:9092"):
        # reuse existing instance per topic
        if topic in cls._instances:
            return cls._instances[topic]
        instance = super().__new__(cls)
        cls._instances[topic] = instance
        return instance

    def __init__(self, topic: str, bootstrap_servers="localhost:9092"):
        if hasattr(self, "initialized"):  # avoid re-init
            return
        self.initialized = True
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.listeners = set()
        self.task = None

    async def _consume_loop(self):
        try:
            async for msg in self.consumer:
                # send message to all listeners
                for listener in self.listeners:
                    await listener(msg.value)
        finally:
            await self.consumer.stop()

    async def start(self, on_message):
        # Add the listener
        self.listeners.add(on_message)

        if self.consumer is None:
            # Only create consumer once
            self.consumer = AIOKafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda v: json.loads(v.decode("utf-8"))
            )
            await self.consumer.start()
            # Run consume loop in background
            self.task = asyncio.create_task(self._consume_loop())

    async def stop(self, on_message=None):
        # Remove listener if provided
        if on_message and on_message in self.listeners:
            self.listeners.remove(on_message)

        # If no listeners remain, stop consumer
        if not self.listeners and self.consumer:
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            await self.consumer.stop()
            self.consumer = None
            self.task = None
            # Remove from singleton instances
            KafkaConsumerService._instances.pop(self.topic, None)
