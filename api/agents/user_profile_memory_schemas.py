from typing import TypedDict, Optional, Dict, Any

from api.agents.user_profile_schemas import UserProfilePatch


class UserProfileMemoryState(TypedDict):
    user_id: str
    session_id: str

    interview_summary: Dict[str, Any] # 本次面试总结

    old_profile: Optional[Dict[str, Any]]
    profile_patch: Optional[UserProfilePatch]
    saved_profile: Optional[Dict[str, Any]]
