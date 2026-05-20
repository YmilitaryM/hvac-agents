from unittest.mock import AsyncMock, MagicMock
import pytest
from acquisition_service.edge_sync import EdgeSync


@pytest.mark.asyncio
async def test_edge_sync_no_pending_data():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    syncer = EdgeSync(mock_factory, None, "http://cloud:8005")
    count = await syncer.sync_pending()
    assert count == 0
