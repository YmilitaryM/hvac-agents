"""Add carbon domain tables

Revision ID: 0001_carbon_tables
Revises: None
Create Date: 2026-05-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_carbon_tables'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # carbon_ledger
    op.create_table(
        'carbon_ledger',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('plant_id', sa.String(32), index=True, nullable=False),
        sa.Column('period', sa.String(10), index=True, nullable=False),
        sa.Column('entry_type', sa.String(32), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('allowance_type', sa.String(10), nullable=False),
        sa.Column('qty_tco2', sa.Float(), nullable=False),
        sa.Column('unit_price', sa.Float(), default=0.0),
        sa.Column('balance_after', sa.Float(), nullable=False),
        sa.Column('trade_id', sa.String(32), nullable=True),
        sa.Column('emission_id', sa.String(32), nullable=True),
        sa.Column('compliance_id', sa.String(32), nullable=True),
        sa.Column('note', sa.Text(), default=''),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_ledger_plant_period', 'carbon_ledger', ['plant_id', 'period'])
    op.create_index('ix_ledger_plant_type', 'carbon_ledger', ['plant_id', 'allowance_type'])
    op.create_index('ix_ledger_entry_type', 'carbon_ledger', ['entry_type', 'created_at'])

    # carbon_emissions
    op.create_table(
        'carbon_emissions',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('plant_id', sa.String(32), index=True, nullable=False),
        sa.Column('timestamp', sa.Float(), index=True, nullable=False),
        sa.Column('power_kw', sa.Float(), default=0.0),
        sa.Column('emission_factor', sa.Float(), default=0.50),
        sa.Column('tco2', sa.Float(), default=0.0),
        sa.Column('cooling_gj', sa.Float(), default=0.0),
        sa.Column('source', sa.String(20), default='grid'),
        sa.Column('period_tag', sa.String(10), default=''),
        sa.Column('chiller_id', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_emission_plant_ts', 'carbon_emissions', ['plant_id', 'timestamp'])
    op.create_index('ix_emission_period', 'carbon_emissions', ['period_tag', 'timestamp'])

    # carbon_orders
    op.create_table(
        'carbon_orders',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('plant_id', sa.String(32), index=True, nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('allowance_type', sa.String(10), nullable=False),
        sa.Column('order_type', sa.String(16), default='limit'),
        sa.Column('qty', sa.Float(), nullable=False),
        sa.Column('remaining', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('peak_qty', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), index=True, default='pending'),
        sa.Column('expire_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_orders_status_created', 'carbon_orders', ['status', 'created_at'])
    op.create_index('ix_orders_plant_side_type', 'carbon_orders', ['plant_id', 'side', 'allowance_type', 'status'])

    # carbon_trades
    op.create_table(
        'carbon_trades',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('buy_order_id', sa.String(32), index=True, nullable=False),
        sa.Column('sell_order_id', sa.String(32), index=True, nullable=False),
        sa.Column('buy_plant_id', sa.String(32), index=True, nullable=False),
        sa.Column('sell_plant_id', sa.String(32), index=True, nullable=False),
        sa.Column('allowance_type', sa.String(10), nullable=False),
        sa.Column('qty_tco2', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('total_value', sa.Float(), nullable=False),
        sa.Column('fee', sa.Float(), default=0.0),
        sa.Column('settlement_status', sa.String(20), default='settled'),
        sa.Column('settled_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_trades_buy_plant', 'carbon_trades', ['buy_plant_id', 'created_at'])
    op.create_index('ix_trades_sell_plant', 'carbon_trades', ['sell_plant_id', 'created_at'])

    # carbon_holdings_snapshot
    op.create_table(
        'carbon_holdings_snapshot',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('plant_id', sa.String(32), index=True, nullable=False),
        sa.Column('period', sa.String(10), nullable=False),
        sa.Column('allowance_type', sa.String(10), nullable=False),
        sa.Column('total_held', sa.Float(), default=0.0),
        sa.Column('used', sa.Float(), default=0.0),
        sa.Column('available', sa.Float(), default=0.0),
        sa.Column('locked', sa.Float(), default=0.0),
        sa.Column('snapshot_time', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_holdings_plant_period_type', 'carbon_holdings_snapshot', ['plant_id', 'period', 'allowance_type'], unique=True)

    # carbon_compliance
    op.create_table(
        'carbon_compliance',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('plant_id', sa.String(32), index=True, nullable=False),
        sa.Column('period', sa.String(10), nullable=False),
        sa.Column('required_surrender', sa.Float(), nullable=False),
        sa.Column('actual_surrender', sa.Float(), default=0.0),
        sa.Column('ccer_used', sa.Float(), default=0.0),
        sa.Column('deficit', sa.Float(), default=0.0),
        sa.Column('penalty_yuan', sa.Float(), default=0.0),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_compliance_plant_period', 'carbon_compliance', ['plant_id', 'period'], unique=True)

    # carbon_price_history
    op.create_table(
        'carbon_price_history',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('allowance_type', sa.String(10), nullable=False),
        sa.Column('interval', sa.String(10), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), default=0.0),
        sa.Column('timestamp', sa.Float(), index=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_price_type_interval_ts', 'carbon_price_history', ['allowance_type', 'interval', 'timestamp'])

    # carbon_auctions
    op.create_table(
        'carbon_auctions',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('period', sa.String(10), nullable=False),
        sa.Column('auction_type', sa.String(20), nullable=False),
        sa.Column('total_qty', sa.Float(), nullable=False),
        sa.Column('floor_price', sa.Float(), nullable=False),
        sa.Column('clearing_price', sa.Float(), nullable=True),
        sa.Column('bid_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('bid_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), default='upcoming'),
        sa.Column('winners', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table('carbon_auctions')
    op.drop_table('carbon_price_history')
    op.drop_table('carbon_compliance')
    op.drop_table('carbon_holdings_snapshot')
    op.drop_table('carbon_trades')
    op.drop_table('carbon_orders')
    op.drop_table('carbon_emissions')
    op.drop_table('carbon_ledger')
