import hashlib
import hmac
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    WECOM = "wecom"
    DINGTALK = "dingtalk"
    FEISHU = "feishu"
    SMS = "sms"


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DeliveryConfig:
    wecom_webhook: str = ""
    dingtalk_webhook: str = ""
    dingtalk_secret: str = ""
    feishu_webhook: str = ""
    feishu_secret: str = ""
    sms_endpoint: str = ""
    sms_api_key: str = ""
    sms_phones: list[str] = field(default_factory=list)
    sms_min_level: AlertLevel = AlertLevel.CRITICAL
    enabled_channels: list[ChannelType] = field(default_factory=lambda: [ChannelType.WECOM])


class DeliveryChannel(ABC):
    @abstractmethod
    async def send(self, title: str, content: str, level: AlertLevel) -> bool:
        ...


class WeComChannel(DeliveryChannel):
    """企业微信机器人 webhook."""

    def __init__(self, webhook_url: str):
        self._url = webhook_url

    async def send(self, title: str, content: str, level: AlertLevel) -> bool:
        color = {"info": "info", "warning": "warning", "critical": "warning"}.get(level, "info")
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"## {title}\n> 级别: <font color=\"{color}\">{level.upper()}</font>\n{content}"
            },
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._url, json=payload)
                return resp.status_code == 200
        except Exception:
            logger.warning("WeCom webhook delivery failed", exc_info=True)
            return False


class DingTalkChannel(DeliveryChannel):
    """钉钉机器人 webhook (加签模式)."""

    def __init__(self, webhook_url: str, secret: str = ""):
        self._url = webhook_url
        self._secret = secret

    def _sign(self) -> tuple[str, str]:
        ts = str(round(time.time() * 1000))
        if not self._secret:
            return ts, ""
        sign_str = f"{ts}\n{self._secret}"
        sign = hmac.new(
            self._secret.encode(), sign_str.encode(), hashlib.sha256
        ).digest()
        return ts, sign.hex()

    async def send(self, title: str, content: str, level: AlertLevel) -> bool:
        ts, sign = self._sign()
        url = self._url
        if sign:
            url = f"{self._url}&timestamp={ts}&sign={sign}"
        payload = {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": f"### {title}\n**级别:** {level.upper()}\n\n{content}"},
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                return resp.status_code == 200
        except Exception:
            logger.warning("DingTalk webhook delivery failed", exc_info=True)
            return False


class FeishuChannel(DeliveryChannel):
    """飞书机器人 webhook."""

    def __init__(self, webhook_url: str, secret: str = ""):
        self._url = webhook_url
        self._secret = secret

    def _sign(self) -> tuple[str, str]:
        ts = str(int(time.time()))
        if not self._secret:
            return ts, ""
        sign_str = f"{ts}\n{self._secret}"
        sign = hmac.new(
            self._secret.encode(), sign_str.encode(), hashlib.sha256
        ).digest()
        return ts, sign.hex()

    async def send(self, title: str, content: str, level: AlertLevel) -> bool:
        ts, sign = self._sign()
        color = {"info": "blue", "warning": "yellow", "critical": "red"}.get(level, "blue")
        payload = {
            "msg_type": "interactive",
            "timestamp": ts,
            "sign": sign,
            "card": {
                "header": {"title": {"tag": "plain_text", "content": title}, "template": color},
                "elements": [{"tag": "markdown", "content": f"**级别:** {level.upper()}\n\n{content}"}],
            },
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._url, json=payload)
                return resp.status_code == 200
        except Exception:
            logger.warning("Feishu webhook delivery failed", exc_info=True)
            return False


class SmsChannel(DeliveryChannel):
    """SMS escalation channel — sends to configured phone numbers for critical alerts only."""

    def __init__(self, endpoint: str, api_key: str, phones: list[str], min_level: AlertLevel = AlertLevel.CRITICAL):
        self._endpoint = endpoint
        self._api_key = api_key
        self._phones = phones
        self._min_level = min_level

    def _level_value(self, level: AlertLevel) -> int:
        return {"info": 0, "warning": 1, "critical": 2}[level]

    async def send(self, title: str, content: str, level: AlertLevel) -> bool:
        if self._level_value(level) < self._level_value(self._min_level):
            return True  # below escalation threshold, skip silently
        if not self._phones:
            return False
        payload = {
            "api_key": self._api_key,
            "phones": self._phones,
            "message": f"[{level.upper()}] {title}: {content[:160]}",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._endpoint, json=payload)
                return resp.status_code == 200
        except Exception:
            logger.warning("SMS delivery failed", exc_info=True)
            return False


class AlertDeliveryManager:
    """Manages multiple delivery channels and routes alerts based on severity."""

    def __init__(self, config: Optional[DeliveryConfig] = None):
        self._channels: dict[ChannelType, DeliveryChannel] = {}
        self._config = config or DeliveryConfig()
        self._init_channels()

    def _init_channels(self):
        if ChannelType.WECOM in self._config.enabled_channels and self._config.wecom_webhook:
            self._channels[ChannelType.WECOM] = WeComChannel(self._config.wecom_webhook)
        if ChannelType.DINGTALK in self._config.enabled_channels and self._config.dingtalk_webhook:
            self._channels[ChannelType.DINGTALK] = DingTalkChannel(
                self._config.dingtalk_webhook, self._config.dingtalk_secret
            )
        if ChannelType.FEISHU in self._config.enabled_channels and self._config.feishu_webhook:
            self._channels[ChannelType.FEISHU] = FeishuChannel(
                self._config.feishu_webhook, self._config.feishu_secret
            )
        if ChannelType.SMS in self._config.enabled_channels and self._config.sms_endpoint:
            self._channels[ChannelType.SMS] = SmsChannel(
                self._config.sms_endpoint, self._config.sms_api_key,
                self._config.sms_phones, self._config.sms_min_level,
            )

    async def deliver(self, title: str, content: str, level: AlertLevel) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for ctype, channel in self._channels.items():
            results[ctype.value] = await channel.send(title, content, level)
        return results

    async def deliver_alerts(self, alerts: list[dict]) -> list[dict]:
        deliveries = []
        for alert in alerts:
            title = alert.get("message", "HVAC Alert")
            content = json.dumps(alert.get("metadata", {}), ensure_ascii=False)
            level = AlertLevel(alert.get("level", "info"))
            results = await self.deliver(title, content, level)
            deliveries.append({"alert": alert.get("rule_name", ""), "channels": results})
        return deliveries

    def update_config(self, config: DeliveryConfig):
        self._config = config
        self._channels.clear()
        self._init_channels()
