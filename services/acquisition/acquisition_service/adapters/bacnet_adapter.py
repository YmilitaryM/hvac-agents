from .base import ProtocolAdapter, ProtocolBinding, CommunicationError, WriteError


class BacnetAdapter(ProtocolAdapter):
    protocol = "bacnet"

    def __init__(self):
        self._device: object | None = None
        self._config: dict = {}

    async def connect(self, binding: ProtocolBinding) -> None:
        if self._device is not None:
            await self.disconnect()
        self._config = binding.config
        device_id = self._config.get("device_id")
        try:
            import BAC0
            self._device = BAC0.lite(device_id)
        except ImportError:
            raise CommunicationError("BAC0 library not installed")
        except Exception as e:
            raise CommunicationError(f"BACnet connect failed: device={device_id} — {e}") from e

    async def read_point(self, point_id: str, binding: ProtocolBinding) -> float:
        if self._device is None:
            raise CommunicationError("Not connected")
        obj_type = binding.config.get("object_type", "analog_input")
        instance = binding.config.get("instance")
        try:
            if obj_type == "analog_input":
                value = self._device.read(f"analogInput {instance} presentValue")
            elif obj_type == "analog_output":
                value = self._device.read(f"analogOutput {instance} presentValue")
            elif obj_type == "analog_value":
                value = self._device.read(f"analogValue {instance} presentValue")
            else:
                raise CommunicationError(f"Unsupported BACnet object type: {obj_type}")
            return float(value)
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(f"BACnet read failed: {e}") from e

    async def write_point(self, point_id: str, binding: ProtocolBinding, value: float) -> None:
        if self._device is None:
            raise CommunicationError("Not connected")
        obj_type = binding.config.get("object_type", "analog_output")
        instance = binding.config.get("instance")
        try:
            self._device.write(f"{obj_type} {instance} presentValue {value}")
        except CommunicationError:
            raise
        except Exception as e:
            raise WriteError(f"BACnet write failed: {e}") from e

    async def disconnect(self) -> None:
        if self._device:
            try:
                self._device.disconnect()
            except Exception:
                pass
            self._device = None
