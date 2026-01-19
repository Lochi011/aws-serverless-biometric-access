import boto3
import json


class SnsClient:
    def __init__(self, topic_arn: str):
        self._topic_arn = topic_arn
        self._client = boto3.client('sns')

    def publish_alert(self, payload: dict, subject: str):
        self._client.publish(
            TopicArn=self._topic_arn,
            Subject=subject,
            Message=json.dumps(payload)
        )
