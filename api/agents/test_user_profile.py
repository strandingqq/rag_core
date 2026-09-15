from api.agents.user_profile import run_user_profile_agent
from api.agents.user_profile_schemas import (
    UserProfileContext,
    UserProfileTurnSummary,
)

context = UserProfileContext(
    user_id="u1",
    session_id="s1",
    role="frontend",
    topics=["React"],
    total_score=65.0,
    level="及格但不稳定",
    turn_summaries=[
        UserProfileTurnSummary(
            index=0,
            question_id="q1",
            topic="React Hooks",
            score=62,
            reason="候选人知道 useEffect 会执行，但没有解释依赖数组变化机制。",
            hit_points=["知道 useEffect 与副作用有关"],
            missing_points=["没有说明空数组、不传数组、指定依赖的区别"],
            mistakes=[],
            suggestion="建议复习 useEffect 依赖数组和清理函数。",
        )
    ],
    learning_advice_summary="建议重点复习 React Hooks 的执行时机和边界场景。",
)

patch = run_user_profile_agent(context)
print(patch.model_dump())