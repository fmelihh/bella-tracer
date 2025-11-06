import os
from aiokafka import AIOKafkaConsumer


async def retrieve_aio_kafka_consumer(
    topic: str, consumer_group: str
) -> AIOKafkaConsumer:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")

    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset="earliest",
        group_id=consumer_group,
    )

    return consumer


__all__ = ["retrieve_aio_kafka_consumer"]
