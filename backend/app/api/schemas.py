from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated


class TeamSummary(BaseModel):
    """Basic metadata about an NFL franchise."""

    model_config = ConfigDict(extra="forbid")

    code: str
    display_name: str
    short_display_name: Optional[str] = None
    location: Optional[str] = None
    nickname: Optional[str] = None
    logo: Optional[str] = None


class TeamListResponse(BaseModel):
    """Response payload for /teams."""

    model_config = ConfigDict(extra="forbid")

    teams: List[TeamSummary]


class PlayerContract(BaseModel):
    """High-level contract metadata for a player."""

    model_config = ConfigDict(extra="forbid")

    id: int
    source: str
    source_url: Optional[str] = None
    signed_date: Optional[date] = None
    total_value: Optional[float] = None
    guaranteed: Optional[float] = None
    average_per_year: Optional[float] = None
    notes: Optional[str] = None


class PlayerSummary(BaseModel):
    """Roster-facing view of a player."""

    model_config = ConfigDict(extra="forbid")

    id: int
    external_id: str
    team_code: str
    first_name: str
    last_name: str
    full_name: str
    position: str
    jersey_number: Optional[int] = None
    status: str
    experience: int
    college: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[int] = None
    birthdate: Optional[date] = None
    roster_date: Optional[date] = None
    roster_source: Optional[str] = None
    contract: Optional[PlayerContract] = None


class TeamRosterResponse(BaseModel):
    """Roster payload keyed to a given team."""

    model_config = ConfigDict(extra="forbid")

    team: TeamSummary
    roster_source: Optional[str] = None
    roster_date: Optional[date] = None
    player_count: int
    players: List[PlayerSummary]


class PlayerDetailResponse(BaseModel):
    """Detailed player information, including contracts."""

    model_config = ConfigDict(extra="forbid")

    team: TeamSummary
    player: PlayerSummary
    contracts: List[PlayerContract]


class CapEntry(BaseModel):
    """Single line item in a cap breakdown."""

    model_config = ConfigDict(extra="forbid")

    player_id: int
    player_name: str
    position: str
    cap_hit: float
    contract_id: Optional[int] = None


class TeamCapResponse(BaseModel):
    """Summary of a team's active cap charges."""

    model_config = ConfigDict(extra="forbid")

    team: TeamSummary
    cap_limit: float
    total_cap_hit: float
    cap_space: float
    player_count: int
    considered_player_count: int
    top51_applied: bool
    entries: List[CapEntry]


class FreeAgentProfile(BaseModel):
    """Snapshot of a street free agent with AI-evaluated scores."""

    id: str
    name: str
    position: str
    age: Optional[int] = None
    market_value: Optional[float] = None
    traits: List[str] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)
    last_team: Optional[str] = None
    preferred_years: List[int] = Field(default_factory=list)
    scheme_fits: List[str] = Field(default_factory=list)
    fit_score: int
    contender_score: int
    value_score: float
    notes: List[str] = Field(default_factory=list)


class FreeAgentListResponse(BaseModel):
    """Response for /market/free-agents."""

    free_agents: List[FreeAgentProfile]


class TradeTarget(BaseModel):
    """Potential trade target with availability heuristics."""

    player_id: int
    name: str
    position: str
    team: Dict[str, Any]
    cap_hit: float
    years_remaining: int
    fit_score: int
    availability_score: int
    contender_score: int
    notes: List[str] = Field(default_factory=list)


class TradeTargetResponse(BaseModel):
    """Response for /market/trade-targets."""

    trade_targets: List[TradeTarget]


class MarketOfferResponse(BaseModel):
    """Outcome of a market offer evaluation."""

    accepted: bool
    type: Literal["free_agent", "trade"]
    notes: List[str]
    counter: Optional[Dict[str, Any]] = None
    cap_space_after: Optional[float] = None
    transaction_id: Optional[int] = None


TransactionType = Literal["release", "sign", "trade"]


class TransactionRequest(BaseModel):
    """Incoming payload for transaction preview/commit."""

    team_code: str
    type: TransactionType
    payload: Dict[str, Any]


class TransactionPreview(BaseModel):
    """Result of a preview calculation before committing."""

    allowed: bool
    type: TransactionType
    team: str
    cap_limit: float
    total_cap: float
    cap_space_before: float
    cap_space_after: float
    cap_delta: float
    dead_money: float
    dead_money_future: float
    roster_delta: int
    roster_count_after: int
    notes: List[str]
    payload: Dict[str, Any]
    partner: Optional[Dict[str, Any]] = None


class TransactionRecord(BaseModel):
    """Logged transaction after commit."""

    id: int
    type: TransactionType
    team: TeamSummary
    cap_delta: float
    cap_space_after: float
    payload: Dict[str, Any]
    notes: List[str]
    status: str
    created_at: datetime


class FreeAgentOffer(BaseModel):
    """Offer payload for a free-agent negotiation."""

    type: Literal["free_agent"]
    team_code: str
    free_agent_id: str
    years: int
    apy: float
    signing_bonus: float = 0.0
    roster_bonus: float = 0.0
    workout_bonus: float = 0.0


class TradeOffer(BaseModel):
    """Offer payload for a trade negotiation."""

    type: Literal["trade"]
    team_code: str
    partner_team_code: str
    send_player_ids: List[int]
    receive_player_ids: List[int]
    post_june_1: bool = False


MarketOfferRequest = Annotated[Union[FreeAgentOffer, TradeOffer], Field(discriminator="type")]
