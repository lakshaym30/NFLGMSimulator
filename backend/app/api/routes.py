from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import (
    CapEntry,
    FreeAgentListResponse,
    MarketOfferRequest,
    MarketOfferResponse,
    PlayerContract,
    PlayerDetailResponse,
    PlayerSummary,
    TeamCapResponse,
    TeamListResponse,
    TeamRosterResponse,
    TeamSummary,
    TransactionPreview,
    TransactionRecord,
    TransactionRequest,
    TradeTargetResponse,
)
from app.core.config import settings
from app.db.session import get_db
from app.models import Contract, Player, Team, Transaction
from app.services import cap as cap_service
from app.services import draft as draft_service
from app.services import market as market_service
from app.services import season as season_service
from app.services import transactions as transaction_service
from app.services.draft import DraftError
from app.services.season import SeasonSimError
from app.services.transactions import TransactionError
from app.services.market import MarketError

router = APIRouter()


def _decimal_to_float(value: Optional[Decimal]) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _serialize_team(team: Team) -> TeamSummary:
    return TeamSummary(
        code=team.abbreviation,
        display_name=team.display_name,
        short_display_name=team.short_display_name,
        location=team.location,
        nickname=team.nickname,
        logo=team.logo,
    )


def _serialize_contract(contract) -> Optional[PlayerContract]:
    if not contract:
        return None
    return PlayerContract(
        id=contract.id,
        source=contract.source,
        source_url=contract.source_url,
        signed_date=contract.signed_date,
        total_value=_decimal_to_float(contract.total_value),
        guaranteed=_decimal_to_float(contract.guaranteed),
        average_per_year=_decimal_to_float(contract.average_per_year),
        notes=contract.notes,
    )


def _serialize_player(player: Player) -> PlayerSummary:
    contract = player.contracts[0] if player.contracts else None
    return PlayerSummary(
        id=player.id,
        external_id=player.external_id,
        team_code=player.team_code,
        first_name=player.first_name,
        last_name=player.last_name,
        full_name=player.full_name,
        position=player.position,
        jersey_number=player.jersey_number,
        status=player.status,
        experience=player.experience,
        college=player.college,
        height=player.height,
        weight=player.weight,
        birthdate=player.birthdate,
        roster_date=player.roster_date,
        roster_source=player.roster_source,
        contract=_serialize_contract(contract),
    )


def _get_team_or_404(db: Session, team_code: str) -> Team:
    team = db.scalar(
        select(Team).where(func.lower(Team.abbreviation) == team_code.lower())
    )
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team '{team_code.upper()}' not found",
        )
    return team


@router.get("/health")
def read_health():
    """Return minimal health metadata for smoke checks."""
    return {
        "status": "ok",
        "service": settings.project_name,
        "version": settings.version,
        "environment": settings.environment,
        "commit": settings.commit_sha,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


@router.get("/teams", response_model=TeamListResponse)
def list_teams(db: Session = Depends(get_db)):
    teams = db.scalars(select(Team).order_by(Team.display_name)).all()
    return TeamListResponse(teams=[_serialize_team(team) for team in teams])


@router.get("/market/free-agents", response_model=FreeAgentListResponse)
def list_free_agents(team_code: str = Query(..., description="Team evaluating the market"), db: Session = Depends(get_db)):
    try:
        agents = market_service.list_free_agents(db, team_code)
    except MarketError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return FreeAgentListResponse(free_agents=agents)


@router.get("/market/trade-targets", response_model=TradeTargetResponse)
def list_trade_targets(team_code: str = Query(..., description="Team initiating trades"), db: Session = Depends(get_db)):
    try:
        targets = market_service.list_trade_targets(db, team_code)
    except MarketError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return TradeTargetResponse(trade_targets=targets)


@router.post("/market/offers", response_model=MarketOfferResponse)
def submit_market_offer(request: MarketOfferRequest, db: Session = Depends(get_db)):
    try:
        if request.type == "free_agent":
            result = market_service.evaluate_free_agent_offer(
                db,
                team_code=request.team_code,
                free_agent_id=request.free_agent_id,
                apy=request.apy,
                years=request.years,
                signing_bonus=request.signing_bonus,
                roster_bonus=request.roster_bonus,
                workout_bonus=request.workout_bonus,
            )
        else:
            result = market_service.evaluate_trade_offer(
                db,
                team_code=request.team_code,
                partner_team_code=request.partner_team_code,
                send_player_ids=request.send_player_ids,
                receive_player_ids=request.receive_player_ids,
                post_june_1=request.post_june_1,
            )
    except (MarketError, TransactionError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return MarketOfferResponse(**result)


@router.get("/teams/{team_code}/roster", response_model=TeamRosterResponse)
def get_team_roster(team_code: str, db: Session = Depends(get_db)):
    team = _get_team_or_404(db, team_code)
    players = db.scalars(
        select(Player)
        .where(Player.team_id == team.id)
        .options(selectinload(Player.contracts).selectinload(Contract.years))
        .order_by(Player.last_name, Player.first_name)
    ).all()

    roster_source = next((p.roster_source for p in players if p.roster_source), None)
    roster_dates = [p.roster_date for p in players if p.roster_date]
    roster_date = max(roster_dates) if roster_dates else None

    return TeamRosterResponse(
        team=_serialize_team(team),
        roster_source=roster_source,
        roster_date=roster_date,
        player_count=len(players),
        players=[_serialize_player(player) for player in players],
    )


@router.get("/players/{player_id}", response_model=PlayerDetailResponse)
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.scalar(
        select(Player)
        .where(Player.id == player_id)
        .options(
            selectinload(Player.contracts).selectinload(Contract.years),
            selectinload(Player.team),
        )
    )
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player '{player_id}' not found",
        )

    contracts = [
        _serialize_contract(contract) for contract in player.contracts if contract
    ]

    return PlayerDetailResponse(
        team=_serialize_team(player.team),
        player=_serialize_player(player),
        contracts=contracts,
    )


@router.get("/teams/{team_code}/cap", response_model=TeamCapResponse)
def get_team_cap(
    team_code: str,
    top51: bool = Query(default=True, description="Apply Top-51 offseason rule."),
    db: Session = Depends(get_db),
):
    team = _get_team_or_404(db, team_code)
    players = db.scalars(
        select(Player)
        .where(Player.team_id == team.id)
        .options(selectinload(Player.contracts).selectinload(Contract.years))
    ).all()

    entries = []
    total_cap_hit = 0.0
    for player in players:
        contract = player.contracts[0] if player.contracts else None
        cap_hit = cap_service.cap_hit_from_contract(contract)
        total_cap_hit += cap_hit
        entries.append(
            CapEntry(
                player_id=player.id,
                player_name=player.full_name,
                position=player.position,
                cap_hit=round(cap_hit, 2),
                contract_id=contract.id if contract else None,
            )
        )

    entries.sort(key=lambda entry: entry.cap_hit, reverse=True)
    considered_entries = entries[:51] if top51 else entries
    total_cap_hit = round(sum(entry.cap_hit for entry in considered_entries), 2)
    cap_limit = float(settings.salary_cap_limit)
    cap_space = cap_limit - total_cap_hit

    return TeamCapResponse(
        team=_serialize_team(team),
        cap_limit=cap_limit,
        total_cap_hit=round(total_cap_hit, 2),
        cap_space=round(cap_space, 2),
        player_count=len(players),
        considered_player_count=len(considered_entries),
        top51_applied=top51,
        entries=entries,
    )


def _serialize_transaction_record(record: Transaction) -> TransactionRecord:
    return TransactionRecord(
        id=record.id,
        type=record.type,
        team=_serialize_team(record.team),
        cap_delta=float(record.cap_delta or 0),
        cap_space_after=float(record.result.get("cap_space_after", 0)),
        payload=record.payload,
        notes=record.result.get("notes", []),
        status=record.status,
        created_at=record.created_at,
    )


def _preview_transaction(request: TransactionRequest, db: Session) -> TransactionPreview:
    payload = request.payload or {}
    if request.type == "release":
        player_id = payload.get("player_id")
        if player_id is None:
            raise TransactionError("player_id is required for release transactions")
        post_june_1 = bool(payload.get("post_june_1", False))
        preview = transaction_service.preview_release(
            db, request.team_code, int(player_id), post_june_1=post_june_1
        )
    elif request.type == "sign":
        required = ["full_name", "position", "apy"]
        missing = [field for field in required if field not in payload]
        if missing:
            raise TransactionError(f"Missing fields for signing: {', '.join(missing)}")
        preview = transaction_service.preview_sign(
            db,
            request.team_code,
            payload["full_name"],
            payload["position"],
            float(payload["apy"]),
            float(payload.get("guaranteed", payload["apy"])),
            int(payload.get("years", 1)),
            signing_bonus=float(payload.get("signing_bonus", 0)),
            roster_bonus=float(payload.get("roster_bonus", 0)),
            workout_bonus=float(payload.get("workout_bonus", 0)),
        )
    elif request.type == "trade":
        send_ids = payload.get("send_player_ids") or []
        receive_ids = payload.get("receive_player_ids") or []
        partner = payload.get("partner_team_code")
        if not send_ids or not partner:
            raise TransactionError("Trade requires send_player_ids and partner_team_code")
        preview = transaction_service.preview_trade(
            db,
            request.team_code,
            [int(pid) for pid in send_ids],
            [int(pid) for pid in receive_ids],
            partner_team_code=partner,
            post_june_1=bool(payload.get("post_june_1", False)),
        )
    else:
        raise TransactionError(f"Unsupported transaction type '{request.type}'")
    return TransactionPreview(**preview)


@router.post("/transactions/preview", response_model=TransactionPreview)
def preview_transaction(request: TransactionRequest, db: Session = Depends(get_db)):
    try:
        return _preview_transaction(request, db)
    except TransactionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/transactions", response_model=TransactionRecord)
def commit_transaction(request: TransactionRequest, db: Session = Depends(get_db)):
    try:
        preview = _preview_transaction(request, db)
        if not preview.allowed:
            raise TransactionError("Transaction rejected by cap/roster rules.")

        if request.type == "release":
            record = transaction_service.commit_release(db, preview.model_dump())
        elif request.type == "sign":
            record = transaction_service.commit_sign(db, preview.model_dump())
        elif request.type == "trade":
            record = transaction_service.commit_trade(db, preview.model_dump())
        else:
            raise TransactionError("Unsupported transaction type.")

        return _serialize_transaction_record(record)
    except TransactionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/transactions", response_model=List[TransactionRecord])
def list_transactions(
    team_code: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.team))
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    if team_code:
        stmt = stmt.join(Transaction.team).where(
            func.lower(Team.abbreviation) == team_code.lower()
        )
    records = db.scalars(stmt).all()
    return [_serialize_transaction_record(record) for record in records]


@router.post("/transactions/{transaction_id}/undo", response_model=TransactionRecord)
def undo_transaction(transaction_id: int, db: Session = Depends(get_db)):
    try:
        record = transaction_service.undo_transaction(db, transaction_id)
        return _serialize_transaction_record(record)
    except TransactionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/draft/prospects")
def list_prospect_board():
    try:
        return draft_service.load_prospect_board()
    except DraftError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


class DraftSimRequest(BaseModel):
    team_code: str
    rounds: int = 7


@router.post("/draft/simulate")
def simulate_draft(request: DraftSimRequest, db: Session = Depends(get_db)):
    try:
        return draft_service.simulate_draft(db, request.team_code, request.rounds)
    except DraftError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


class SeasonSimRequest(BaseModel):
    team_code: str
    weeks: int = 17


@router.post("/season/simulate")
def simulate_season(request: SeasonSimRequest, db: Session = Depends(get_db)):
    try:
        return season_service.simulate_season(db, request.team_code, request.weeks)
    except SeasonSimError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
