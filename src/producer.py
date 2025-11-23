from aiokafka import AIOKafkaProducer
import json

class KafkaProducerService:
    def __init__(self, bootstrap_servers="localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None

    async def start(self):
        # ✅ Create producer inside async function (after loop is running)
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        await self.producer.start()

    async def stop(self):
        if self.producer:
            await self.producer.stop()

    async def send_message(self, topic: str, message: dict):
        if not self.producer:
            raise RuntimeError("Producer not started. Call start() first.")
        await self.producer.send_and_wait(topic, message)
