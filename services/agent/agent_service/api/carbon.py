"""Carbon management REST API — 5 route groups."""
import time
from datetime import datetime

from fastapi import APIRouter, Request, Query, HTTPException, Depends
from pydantic import BaseModel, Field

router = APIRouter()


# ── Dependencies ──
def get_market(request: Request):
    return request.app.state.carbon_market


# ── Request/Response models ──
class AllocationRequest(BaseModel):
    plant_id: str
    period: str
    qty: float = Field(gt=0)
    allowance_type: str = "CEA"
    source: str = "free_allocation"


class TransferRequest(BaseModel):
    from_plant: str
    to_plant: str
    qty: float = Field(gt=0)
    allowance_type: str = "CEA"


class OrderRequest(BaseModel):
    plant_id: str
    side: str  # buy | sell
    allowance_type: str  # CEA | CCER
    order_type: str = "limit"  # market | limit | iceberg
    qty: float = Field(gt=0)
    price: float = Field(ge=0, default=0.0)
    peak_qty: float = None
    expire_at: str | None = None


class SurrenderRequest(BaseModel):
    plant_id: str
    period: str
    qty_cea: float = Field(ge=0, default=0.0)
    qty_ccer: float = Field(ge=0, default=0.0)


class AuctionBidRequest(BaseModel):
    plant_id: str
    bid_qty: float = Field(gt=0)
    bid_price: float = Field(ge=0)


# ══════════════════════════════════════════════════
# 1. Emissions  /api/carbon/emissions
# ══════════════════════════════════════════════════
emissions = APIRouter()


@emissions.get("/realtime")
async def emissions_realtime(
    plant_id: str = Query(...),
    market=Depends(get_market),
):
    h = await market.get_holdings(plant_id, time.strftime("%Y"))
    return {
        "plant_id": plant_id,
        "timestamp": time.time(),
        "holdings": h,
        "latest_price": await market.get_latest_price("CEA"),
    }


@emissions.get("/history")
async def emissions_history(
    plant_id: str = Query(...),
    start: float = Query(None),
    end: float = Query(None),
    interval: str = Query("1h"),
):
    raise HTTPException(501, "Emissions history endpoint not yet implemented")


@emissions.get("/summary")
async def emissions_summary(
    plant_id: str = Query(...),
    period: str = Query("month"),
):
    raise HTTPException(501, "Emissions summary endpoint not yet implemented")


@emissions.get("/factors")
async def emission_factors():
    from ..carbon.emission.factor_registry import CEA_REGIONAL_FACTORS
    return {"regions": CEA_REGIONAL_FACTORS}


# ══════════════════════════════════════════════════
# 2. Holdings  /api/carbon/holdings
# ══════════════════════════════════════════════════
holdings = APIRouter()


@holdings.get("")
async def get_holdings(
    plant_id: str = Query(...),
    period: str = Query(None),
    market=Depends(get_market),
):
    if period is None:
        period = time.strftime("%Y")
    return await market.get_holdings(plant_id, period)


@holdings.post("/allocate")
async def allocate_allowance(body: AllocationRequest, market=Depends(get_market)):
    return await market.receive_allocation(
        body.plant_id, body.period, body.qty, body.source
    )


@holdings.post("/transfer")
async def transfer_allowance(body: TransferRequest, market=Depends(get_market)):
    return await market.transfer(
        body.from_plant, body.to_plant, body.qty, body.allowance_type
    )


# ══════════════════════════════════════════════════
# 3. Trading  /api/carbon/trading
# ══════════════════════════════════════════════════
trading = APIRouter()


@trading.get("/order-book")
async def order_book(
    allowance_type: str = Query("CEA"),
    depth: int = Query(10),
    market=Depends(get_market),
):
    return await market.get_order_book(allowance_type, depth)


@trading.post("/orders")
async def place_order(body: OrderRequest, market=Depends(get_market)):
    return await market.place_order(body.model_dump())


@trading.delete("/orders/{order_id}")
async def cancel_order(order_id: str, market=Depends(get_market)):
    ok = await market.cancel_order(order_id)
    if not ok:
        raise HTTPException(404, "Order not found or already filled/cancelled")
    return {"status": "cancelled"}


@trading.get("/orders")
async def my_orders(
    plant_id: str = Query(...),
    status: str = Query(None),
    market=Depends(get_market),
):
    return {"orders": await market.get_my_orders(plant_id, status)}


@trading.get("/orders/{order_id}")
async def get_order(order_id: str, market=Depends(get_market)):
    order = await market.get_order(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@trading.get("/trades")
async def my_trades(
    plant_id: str = Query(...),
    start: float = Query(None),
    end: float = Query(None),
    market=Depends(get_market),
):
    return {"trades": await market.get_my_trades(plant_id, start, end)}


# ══════════════════════════════════════════════════
# 4. Compliance  /api/carbon/compliance
# ══════════════════════════════════════════════════
compliance = APIRouter()


@compliance.get("/status")
async def compliance_status(
    plant_id: str = Query(...),
    period: str = Query(None),
    market=Depends(get_market),
):
    if period is None:
        period = time.strftime("%Y")
    deadline = await market.get_compliance_deadline(period)
    h = await market.get_holdings(plant_id, period)
    return {"plant_id": plant_id, "period": period, "holdings": h, "deadline": deadline}


@compliance.post("/surrender")
async def surrender(body: SurrenderRequest, market=Depends(get_market)):
    results = []
    if body.qty_cea > 0:
        results.append(await market.surrender(body.plant_id, body.period, body.qty_cea, "CEA"))
    if body.qty_ccer > 0:
        results.append(await market.surrender(body.plant_id, body.period, body.qty_ccer, "CCER"))
    return {"surrenders": results}


@compliance.get("/history")
async def compliance_history(plant_id: str = Query(...)):
    raise HTTPException(501, "Compliance history endpoint not yet implemented")


@compliance.get("/report")
async def mrv_report(plant_id: str = Query(...), period: str = Query(None)):
    raise HTTPException(501, "MRV report endpoint not yet implemented")


# ══════════════════════════════════════════════════
# 5. Market  /api/carbon/market
# ══════════════════════════════════════════════════
market_api = APIRouter()


@market_api.get("/price")
async def latest_price(
    allowance_type: str = Query("CEA"),
    market=Depends(get_market),
):
    price = await market.get_latest_price(allowance_type)
    return {"allowance_type": allowance_type, "price": price}


@market_api.get("/ohlcv")
async def ohlcv(
    allowance_type: str = Query("CEA"),
    interval: str = Query("1h"),
    start: float = Query(None),
    end: float = Query(None),
    market=Depends(get_market),
):
    data = await market.get_ohlcv(allowance_type, interval, start, end)
    return {"allowance_type": allowance_type, "interval": interval, "data": data}


@market_api.get("/calendar")
async def market_calendar(market=Depends(get_market)):
    return await market.get_market_calendar()


@market_api.get("/auctions")
async def auctions(period: str = Query(None)):
    raise HTTPException(501, "Auctions endpoint not yet implemented")


@market_api.post("/auctions/{auction_id}/bid")
async def bid_auction(auction_id: str, body: AuctionBidRequest, market=Depends(get_market)):
    return await market.participate_auction(body.plant_id, body.bid_qty, body.bid_price, auction_id)
