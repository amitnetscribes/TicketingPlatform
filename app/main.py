from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class TicketType(str, Enum):
    INCIDENT = "incident"
    SERVICE_REQUEST = "service_request"
    SUBSCRIPTION = "subscription"
    ASSET_ISSUE = "asset_issue"
    INVENTORY = "inventory"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(str, Enum):
    NEW = "new"
    AWAITING_APPROVAL = "awaiting_approval"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"


@dataclass
class Ticket:
    id: str
    title: str
    description: str
    requester_id: str
    ticket_type: TicketType
    priority: TicketPriority
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    asset_id: Optional[str] = None
    inventory_item_id: Optional[str] = None
    approval_state: Dict[str, str] = field(default_factory=dict)


@dataclass
class Asset:
    id: str
    name: str
    category: str
    owner_id: Optional[str]
    status: str
    serial_number: Optional[str]


@dataclass
class InventoryItem:
    id: str
    sku: str
    name: str
    quantity_on_hand: int
    reorder_threshold: int


class ApprovalStep(BaseModel):
    order: int
    approver_role: str


class ApprovalFlow(BaseModel):
    ticket_type: TicketType
    steps: List[ApprovalStep]


class TicketCreateRequest(BaseModel):
    title: str = Field(..., min_length=4)
    description: str = Field(..., min_length=8)
    requester_id: str
    ticket_type: TicketType
    priority: TicketPriority = TicketPriority.MEDIUM
    asset_id: Optional[str] = None
    inventory_item_id: Optional[str] = None


class TicketApprovalAction(BaseModel):
    approver_role: str
    approved: bool


class AssetCreateRequest(BaseModel):
    name: str
    category: str
    owner_id: Optional[str] = None
    status: str = "active"
    serial_number: Optional[str] = None


class InventoryCreateRequest(BaseModel):
    sku: str
    name: str
    quantity_on_hand: int = Field(..., ge=0)
    reorder_threshold: int = Field(..., ge=0)


class InventoryAdjustRequest(BaseModel):
    delta: int


class InMemoryStore:
    def __init__(self) -> None:
        self.tickets: Dict[str, Ticket] = {}
        self.assets: Dict[str, Asset] = {}
        self.inventory: Dict[str, InventoryItem] = {}
        self.approval_flows: Dict[TicketType, ApprovalFlow] = {}

    def create_ticket(self, request: TicketCreateRequest) -> Ticket:
        now = datetime.utcnow()
        ticket_id = str(uuid4())
        flow = self.approval_flows.get(request.ticket_type)
        status = TicketStatus.NEW if not flow else TicketStatus.AWAITING_APPROVAL

        approval_state: Dict[str, str] = {}
        if flow:
            for step in sorted(flow.steps, key=lambda s: s.order):
                approval_state[step.approver_role] = "pending"

        ticket = Ticket(
            id=ticket_id,
            title=request.title,
            description=request.description,
            requester_id=request.requester_id,
            ticket_type=request.ticket_type,
            priority=request.priority,
            status=status,
            created_at=now,
            updated_at=now,
            asset_id=request.asset_id,
            inventory_item_id=request.inventory_item_id,
            approval_state=approval_state,
        )
        self.tickets[ticket.id] = ticket
        return ticket


store = InMemoryStore()
app = FastAPI(title="Enterprise Ticketing Platform", version="1.0.0")


@app.get("/health")
def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/approval-flows", response_model=ApprovalFlow)
def upsert_approval_flow(flow: ApprovalFlow) -> ApprovalFlow:
    if flow.steps != sorted(flow.steps, key=lambda s: s.order):
        raise HTTPException(status_code=400, detail="Approval steps must be submitted in order.")
    store.approval_flows[flow.ticket_type] = flow
    return flow


@app.get("/approval-flows", response_model=List[ApprovalFlow])
def list_approval_flows() -> List[ApprovalFlow]:
    return list(store.approval_flows.values())


@app.post("/tickets")
def create_ticket(request: TicketCreateRequest) -> Dict[str, object]:
    if request.asset_id and request.asset_id not in store.assets:
        raise HTTPException(status_code=404, detail="Referenced asset not found")
    if request.inventory_item_id and request.inventory_item_id not in store.inventory:
        raise HTTPException(status_code=404, detail="Referenced inventory item not found")

    ticket = store.create_ticket(request)
    return ticket.__dict__


@app.get("/tickets")
def list_tickets(status: Optional[TicketStatus] = None, ticket_type: Optional[TicketType] = None) -> List[Dict[str, object]]:
    values = list(store.tickets.values())
    if status:
        values = [ticket for ticket in values if ticket.status == status]
    if ticket_type:
        values = [ticket for ticket in values if ticket.ticket_type == ticket_type]
    return [ticket.__dict__ for ticket in values]


@app.post("/tickets/{ticket_id}/approval")
def process_approval(ticket_id: str, action: TicketApprovalAction) -> Dict[str, object]:
    ticket = store.tickets.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status != TicketStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Ticket is not waiting for approval")
    if action.approver_role not in ticket.approval_state:
        raise HTTPException(status_code=403, detail="Role is not part of the configured flow")

    ticket.approval_state[action.approver_role] = "approved" if action.approved else "rejected"
    ticket.updated_at = datetime.utcnow()

    if not action.approved:
        ticket.status = TicketStatus.REJECTED
        return ticket.__dict__

    if all(step_status == "approved" for step_status in ticket.approval_state.values()):
        ticket.status = TicketStatus.IN_PROGRESS

    return ticket.__dict__


@app.post("/assets")
def create_asset(request: AssetCreateRequest) -> Dict[str, object]:
    asset = Asset(
        id=str(uuid4()),
        name=request.name,
        category=request.category,
        owner_id=request.owner_id,
        status=request.status,
        serial_number=request.serial_number,
    )
    store.assets[asset.id] = asset
    return asset.__dict__


@app.get("/assets")
def list_assets() -> List[Dict[str, object]]:
    return [asset.__dict__ for asset in store.assets.values()]


@app.post("/inventory")
def create_inventory_item(request: InventoryCreateRequest) -> Dict[str, object]:
    item = InventoryItem(
        id=str(uuid4()),
        sku=request.sku,
        name=request.name,
        quantity_on_hand=request.quantity_on_hand,
        reorder_threshold=request.reorder_threshold,
    )
    store.inventory[item.id] = item
    return item.__dict__


@app.post("/inventory/{item_id}/adjust")
def adjust_inventory(item_id: str, request: InventoryAdjustRequest) -> Dict[str, object]:
    item = store.inventory.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    new_quantity = item.quantity_on_hand + request.delta
    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="Adjustment would result in negative inventory")

    item.quantity_on_hand = new_quantity
    return {
        **item.__dict__,
        "below_reorder_threshold": item.quantity_on_hand <= item.reorder_threshold,
    }
