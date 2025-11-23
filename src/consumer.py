from aiokafka import AIOKafkaConsumer
import json

class KafkaConsumerService:
    def __init__(self, topic: str, bootstrap_servers="localhost:9092"):
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None

    async def start(self, on_message):
        # ✅ Create inside async context
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda v: json.loads(v.decode("utf-8"))
        )

        await self.consumer.start()
        try:
            async for msg in self.consumer:
                await on_message(msg.value)
        finally:
            await self.consumer.stop()
