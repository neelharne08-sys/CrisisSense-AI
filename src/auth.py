from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel

class UserRole(str, Enum):
    DUTY_OFFICER = "Duty Officer"
    INCIDENT_COMMANDER = "Incident Commander"
    AUDITOR = "Operations Auditor"

class UserProfile(BaseModel):
    username: str
    name: str
    role: UserRole
    badge_id: str
    sector: str
    clearance_level: str
    avatar: str

DEMO_USERS: Dict[str, UserProfile] = {
    "officer104": UserProfile(
        username="officer104",
        name="Senior Officer Sarah Chen",
        role=UserRole.DUTY_OFFICER,
        badge_id="MEMA-DO-104",
        sector="North Drainage & Arterial Basin",
        clearance_level="Tier-3 Operational",
        avatar="👮‍♀️"
    ),
    "commander_evans": UserProfile(
        username="commander_evans",
        name="Incident Commander Marcus Evans",
        role=UserRole.INCIDENT_COMMANDER,
        badge_id="MEMA-IC-012",
        sector="Citywide Unified Command",
        clearance_level="Tier-1 Executive Authority",
        avatar="🎖️"
    ),
    "analyst_zhang": UserProfile(
        username="analyst_zhang",
        name="Lead Data Auditor Dr. Alex Zhang",
        role=UserRole.AUDITOR,
        badge_id="MEMA-AU-409",
        sector="Operations & Forensic Intelligence",
        clearance_level="Tier-2 Analytical & Audit",
        avatar="🔬"
    )
}

def verify_credentials(username: str, password: str) -> Optional[UserProfile]:
    """
    Validates user credentials against pre-configured EOC profiles or demo fallback.
    """
    clean_user = username.strip().lower()
    if clean_user in DEMO_USERS:
        return DEMO_USERS[clean_user]
    
    # Generic fallback for custom usernames
    if len(username.strip()) >= 3:
        return UserProfile(
            username=clean_user,
            name=f"Officer {username.strip().title()}",
            role=UserRole.DUTY_OFFICER,
            badge_id=f"MEMA-DO-{hash(username) % 900 + 100}",
            sector="General Municipal Sector",
            clearance_level="Tier-3 Operational",
            avatar="🛡️"
        )
    return None
