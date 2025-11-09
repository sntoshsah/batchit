import asyncio
import json
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

class KafkaManager:
    def __init__(self):
        self.producer = None
        self.consumers = {}

    async def start_producer(self):
        """Initialize Kafka producer."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        await self.producer.start()
        print("✅ Kafka Producer started")

    async def stop_producer(self):
        """Gracefully close Kafka producer."""
        if self.producer:
            await self.producer.stop()
            print("🛑 Kafka Producer stopped")

    async def create_consumer(self, topic: str, group_id: str):
        """Create and return Kafka consumer for a topic."""
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
        )
        await consumer.start()
        print(f"✅ Kafka Consumer started for topic '{topic}'")
        return consumer

    async def produce_message(self, topic: str, message: dict):
        """Send message to Kafka."""
        if not self.producer:
            await self.start_producer()
        await self.producer.send_and_wait(topic, message)
