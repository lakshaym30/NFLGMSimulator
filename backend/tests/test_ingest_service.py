from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ingest.service import import_dataset, reset_database
from app.models import Contract, Player, Team


def build_roster_payload():
    return {
        "fetched_at": "2024-06-01T12:00:00Z",
        "source": {"name": "ESPN"},
        "teams": [
            {
                "team": {
                    "id": "22",
                    "abbreviation": "ARI",
                    "displayName": "Arizona Cardinals",
                    "shortDisplayName": "Cardinals",
                    "location": "Arizona",
                    "name": "Cardinals",
                },
                "players": [
                    {
                        "player_id": "espn-1",
                        "first_name": "Kyler",
                        "last_name": "Murray",
                        "position": "QB",
                        "jersey_number": 1,
                        "status": "active",
                        "height": "5-10",
                        "weight": 207,
                        "birthdate": "1997-08-07",
                        "college": "Oklahoma",
                        "experience": 5,
                    },
                    {
                        "player_id": "espn-2",
                        "first_name": "James",
                        "last_name": "Conner",
                        "position": "RB",
                        "jersey_number": 6,
                        "status": "active",
                        "height": "6-1",
                        "weight": 233,
                        "birthdate": "1995-05-05",
                        "college": "Pittsburgh",
                        "experience": 7,
                    },
                ],
            },
            {
                "team": {
                    "id": "23",
                    "abbreviation": "ATL",
                    "displayName": "Atlanta Falcons",
                    "shortDisplayName": "Falcons",
                    "location": "Atlanta",
                    "name": "Falcons",
                },
                "players": [
                    {
                        "player_id": "espn-3",
                        "first_name": "Bijan",
                        "last_name": "Robinson",
                        "position": "RB",
                        "jersey_number": 7,
                        "status": "active",
                        "height": "6-0",
                        "weight": 220,
                        "birthdate": "2002-01-30",
                        "college": "Texas",
                        "experience": 1,
                    }
                ],
            },
        ],
    }


def build_contract_payload():
    return {
        "as_of_date": "2024-06-01",
        "source": {"name": "Spotrac export"},
        "contracts": [
            {
                "player": "Kyler Murray",
                "team": "Cardinals",
                "total_value": 230500000,
                "apy": 46100000,
                "total_guaranteed": 160000000,
            },
            {
                "player": "Bijan Robinson",
                "team": "Falcons",
                "total_value": 21500000,
                "apy": 5375000,
                "total_guaranteed": 21500000,
            },
        ],
    }


def test_import_dataset_handles_league_payload():
    engine = create_engine(
        "sqlite:///:memory:", future=True, connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(bind=engine, future=True)

    reset_database(engine)

    roster_payload = build_roster_payload()
    contracts_payload = build_contract_payload()

    with SessionLocal() as session:
        summary = import_dataset(session, roster_payload, contracts_payload)

        assert summary.teams == 2
        assert summary.players == 3
        assert summary.contracts == 2

        teams = session.query(Team).all()
        assert {team.abbreviation for team in teams} == {"ARI", "ATL"}

        kyler = session.query(Player).filter_by(external_id="espn-1").one()
        assert kyler.team.abbreviation == "ARI"

        bijan_contract = session.query(Contract).join(Player).filter(
            Player.external_id == "espn-3"
        ).one()
        assert float(bijan_contract.total_value) == 21500000
