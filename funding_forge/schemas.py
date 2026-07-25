"""Funding Forge Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from funding_forge.models import utc_now


class FunderBrief(BaseModel):
    """Minimal funder reference to avoid recursion."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class ContactBrief(BaseModel):
    """Minimal contact reference."""

    id: int
    name: str
    role: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OpportunityBrief(BaseModel):
    """Minimal opportunity reference."""

    id: int
    title: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class FunderCreate(BaseModel):
    """Payload to create or update a funding entity."""

    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=50)
    status: str = Field(default="researching", max_length=50)
    website: str | None = Field(default=None, max_length=500)
    focus: str | None = None
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class FunderUpdate(BaseModel):
    """Payload to update a funding entity."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: str | None = Field(default=None, min_length=1, max_length=50)
    status: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=500)
    focus: str | None = None
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class FunderResponse(FunderCreate):
    """Funding entity response."""

    id: int
    created_at: datetime
    updated_at: datetime
    contact_count: int = 0
    opportunity_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ContactCreate(BaseModel):
    """Payload to create or update a contact."""

    funder_id: int | None = None
    name: str = Field(..., min_length=1, max_length=255)
    role: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=100)
    status: str = Field(default="active", max_length=50)
    notes: str | None = None


class ContactUpdate(BaseModel):
    """Payload to update a contact."""

    funder_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class ContactResponse(ContactCreate):
    """Contact response."""

    id: int
    created_at: datetime
    updated_at: datetime
    funder: FunderBrief | None = None

    model_config = ConfigDict(from_attributes=True)


class OpportunityCreate(BaseModel):
    """Payload to create or update an opportunity."""

    funder_id: int | None = None
    title: str = Field(..., min_length=1, max_length=500)
    opportunity_type: str = Field(..., min_length=1, max_length=50)
    status: str = Field(default="prospect", max_length=50)
    amount: str | None = Field(default=None, max_length=100)
    deadline: datetime | None = None
    decision_date: datetime | None = None
    description: str | None = None
    requirements: str | None = None
    outcome: str | None = Field(default="pending", max_length=50)
    notes: str | None = None


class OpportunityUpdate(BaseModel):
    """Payload to update an opportunity."""

    funder_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=500)
    opportunity_type: str | None = Field(default=None, min_length=1, max_length=50)
    status: str | None = Field(default=None, max_length=50)
    amount: str | None = Field(default=None, max_length=100)
    deadline: datetime | None = None
    decision_date: datetime | None = None
    description: str | None = None
    requirements: str | None = None
    outcome: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class OpportunityResponse(OpportunityCreate):
    """Opportunity response."""

    id: int
    created_at: datetime
    updated_at: datetime
    funder: FunderBrief | None = None

    model_config = ConfigDict(from_attributes=True)


class OpportunityStepCreate(BaseModel):
    """Payload to create or update an opportunity step."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    status: str = Field(default="pending", max_length=50)
    due_date: datetime | None = None
    sort_order: int = 0


class OpportunityStepUpdate(BaseModel):
    """Payload to update an opportunity step."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = Field(default=None, max_length=50)
    due_date: datetime | None = None
    completed_at: datetime | None = None
    sort_order: int | None = None


class OpportunityStepResponse(OpportunityStepCreate):
    """Opportunity step response."""

    id: int
    completed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InteractionCreate(BaseModel):
    """Payload to create or update an interaction."""

    contact_id: int | None = None
    opportunity_id: int | None = None
    interaction_type: str = Field(..., min_length=1, max_length=50)
    date: datetime = Field(default_factory=utc_now)
    subject: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    follow_up_date: datetime | None = None


class InteractionUpdate(BaseModel):
    """Payload to update an interaction."""

    contact_id: int | None = None
    opportunity_id: int | None = None
    interaction_type: str | None = Field(default=None, min_length=1, max_length=50)
    date: datetime | None = None
    subject: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    follow_up_date: datetime | None = None


class InteractionResponse(InteractionCreate):
    """Interaction response."""

    id: int
    created_at: datetime
    contact: ContactBrief | None = None
    opportunity: OpportunityBrief | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    """Payload to create or update a task."""

    title: str = Field(..., min_length=1, max_length=500)
    status: str = Field(default="open", max_length=50)
    due_date: datetime | None = None
    related_type: str | None = Field(default=None, max_length=50)
    related_id: int | None = None
    notes: str | None = None


class TaskUpdate(BaseModel):
    """Payload to update a task."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    status: str | None = Field(default=None, max_length=50)
    due_date: datetime | None = None
    related_type: str | None = Field(default=None, max_length=50)
    related_id: int | None = None
    notes: str | None = None


class TaskResponse(TaskCreate):
    """Task response."""

    id: int
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminLogin(BaseModel):
    """Admin login payload."""

    username: str
    password: str
    totp_code: str | None = None


class DocumentResponse(BaseModel):
    """Uploaded document response."""

    id: int
    opportunity_id: int | None = None
    filename: str
    original_filename: str
    storage_type: str
    storage_key: str
    mime_type: str | None = None
    file_size: int | None = None
    description: str | None = None
    related_type: str | None = None
    related_id: int | None = None
    created_at: datetime
    opportunity: OpportunityBrief | None = None

    model_config = ConfigDict(from_attributes=True)


class OpportunityDetail(OpportunityResponse):
    """Opportunity with full related records."""

    steps: list[OpportunityStepResponse] = []
    interactions: list[InteractionResponse] = []
    documents: list[DocumentResponse] = []

    model_config = ConfigDict(from_attributes=True)


class FunderDetail(FunderResponse):
    """Funder with contacts and opportunities."""

    contacts: list[ContactResponse] = []
    opportunities: list[OpportunityResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ContactDetail(ContactResponse):
    """Contact with interactions."""

    interactions: list[InteractionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    """Summary counts for the dashboard."""

    funder_count: int
    contact_count: int
    opportunity_count: int
    open_task_count: int
    upcoming_deadline_count: int
    recent_interaction_count: int
