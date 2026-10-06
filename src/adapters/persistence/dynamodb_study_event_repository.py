"""Adaptador de persistência para histórico append-only de eventos de estudo via Amazon DynamoDB."""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import boto3
from boto3.dynamodb.conditions import Key

from src.application.ports.repositories import IStudyEventRepository
from src.infrastructure.config import settings


class DynamoDbStudyEventRepository(IStudyEventRepository):
    """Repositório DynamoDB para histórico append-only de eventos de estudo (study_events).

    Utiliza PK=USER#<user_id> e SK=EVENT#<reviewed_at_iso>#<event_id> com TTL nativo
    para expurgo automático em conformidade com a LGPD e custo zero de WCU no expurgo.
    """

    def __init__(
        self,
        table_name: str | None = None,
        region_name: str | None = None,
        endpoint_url: str | None = None,
        ttl_days: int | None = None,
        dynamodb_resource: Any = None,
    ) -> None:
        self._table_name = table_name or settings.DYNAMODB_TABLE_STUDY_EVENTS
        self._region = region_name or settings.AWS_REGION
        self._endpoint_url = endpoint_url or settings.DYNAMODB_ENDPOINT_URL
        self._ttl_days = ttl_days if ttl_days is not None else settings.DYNAMODB_TTL_DAYS

        if dynamodb_resource is not None:
            self._dynamodb = dynamodb_resource
        else:
            self._dynamodb = boto3.resource(
                "dynamodb",
                region_name=self._region,
                endpoint_url=self._endpoint_url,
            )
        self._table = self._dynamodb.Table(self._table_name)

    def bulk_insert(self, events: list[dict[str, Any]]) -> int:
        """Insere lote de eventos no DynamoDB com timestamp TTL calculado para expurgo."""
        if not events:
            return 0

        inserted_count = 0
        with self._table.batch_writer() as batch:
            for ev in events:
                user_id = ev.get("user_id")
                pk = f"USER#{user_id}" if user_id else "ANONYMOUS"
                reviewed_at = ev["reviewed_at"]
                if isinstance(reviewed_at, datetime):
                    reviewed_at_dt = reviewed_at
                    reviewed_at_str = reviewed_at.isoformat()
                else:
                    reviewed_at_str = str(reviewed_at)
                    reviewed_at_dt = datetime.fromisoformat(reviewed_at_str)

                event_id_str = str(ev["id"])
                sk = f"EVENT#{reviewed_at_str}#{event_id_str}"
                ttl_timestamp = int((reviewed_at_dt + timedelta(days=self._ttl_days)).timestamp())

                item: dict[str, Any] = {
                    "PK": pk,
                    "SK": sk,
                    "id": event_id_str,
                    "card_id": str(ev["card_id"]),
                    "session_id": str(ev["session_id"]),
                    "status": str(ev["status"]),
                    "reviewed_at": reviewed_at_str,
                    "ttl": ttl_timestamp,
                }
                if user_id:
                    item["user_id"] = str(user_id)
                if ev.get("device_id"):
                    item["device_id"] = str(ev["device_id"])

                batch.put_item(Item=item)
                inserted_count += 1

        return inserted_count

    def list_by_user(self, user_id: UUID, limit: int = 100) -> list[dict[str, Any]]:
        """Lista eventos históricos de um usuário ordenados cronologicamente reversos."""
        pk = f"USER#{user_id}"
        resp = self._table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with("EVENT#"),
            ScanIndexForward=False,
            Limit=limit,
        )
        items = resp.get("Items", [])
        results: list[dict[str, Any]] = []
        for item in items:
            dt = datetime.fromisoformat(item["reviewed_at"])
            results.append(
                {
                    "id": UUID(item["id"]),
                    "reviewed_at": dt,
                    "user_id": UUID(item["user_id"]) if item.get("user_id") else None,
                    "card_id": UUID(item["card_id"]),
                    "session_id": UUID(item["session_id"]),
                    "status": item["status"],
                    "device_id": item.get("device_id"),
                }
            )
        return results

    def anonymize_user_events(self, user_id: UUID) -> int:
        """Anonimiza eventos transferindo para partição ANONYMOUS (LGPD Art. 16, IV)."""
        pk = f"USER#{user_id}"
        resp = self._table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with("EVENT#"),
        )
        items = resp.get("Items", [])
        if not items:
            return 0

        anonymized_count = 0
        with self._table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
                anon_item = dict(item)
                anon_item["PK"] = "ANONYMOUS"
                anon_item.pop("user_id", None)
                anon_item.pop("device_id", None)
                batch.put_item(Item=anon_item)
                anonymized_count += 1

        return anonymized_count
