"""Kafka service — async producer, consumer, and topic registry for DurgasOS."""

from .producer import publish_json, close_producer
from .consumer import KafkaConsumerGroup
from . import topics

__all__ = ["publish_json", "close_producer", "KafkaConsumerGroup", "topics"]
