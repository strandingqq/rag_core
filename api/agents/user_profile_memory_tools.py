def get_default_user_profile() -> dict:
    """ 
    初始化一个空画像
    """
    return {
        "weak_topics": [],
        "strong_topics": [],
        "common_mistakes": [],
        "latest_scores": {},
        "recommended_focus": [],
        "learning_stage": "unknown",
        "summary": "",
        "confidence": 0.0,
    }

def get_user_profile_from_store(store, user_id: str) -> dict:
    """
    读取之前已有的画像Profile
    """
    namespace = (user_id, "profile")
    item = store.get(namespace, "user_profile")

    if item is None:
        default_profile = get_default_user_profile()
        store.put(namespace, "user_profile", default_profile)
        return default_profile

    return item.value


def save_user_profile_to_store(store, user_id: str, profile: dict) -> None:
    """ 
    保存新画像
    """
    namespace = (user_id, "profile")
    store.put(namespace, "user_profile", profile)


def merge_user_profile(old_profile: dict, profile_patch) -> dict:
    patch = profile_patch.model_dump()

    merged = old_profile.copy()

    merged["weak_topics"] = list(
        dict.fromkeys(
            old_profile.get("weak_topics", []) + patch.get("weak_topics", [])
        )
    )

    merged["strong_topics"] = list(
        dict.fromkeys(
            old_profile.get("strong_topics", []) + patch.get("strong_topics", [])
        )
    )

    merged["common_mistakes"] = list(
        dict.fromkeys(
            old_profile.get("common_mistakes", []) + patch.get("common_mistakes", [])
        )
    )

    latest_scores = old_profile.get("latest_scores", {}).copy()
    latest_scores.update(patch.get("latest_scores", {}))
    merged["latest_scores"] = latest_scores

    merged["recommended_focus"] = patch.get(
        "recommended_focus",
        old_profile.get("recommended_focus", []),
    )

    merged["learning_stage"] = patch.get(
        "learning_stage",
        old_profile.get("learning_stage", "unknown"),
    )

    merged["summary"] = patch.get("summary", old_profile.get("summary", ""))
    merged["confidence"] = patch.get("confidence", old_profile.get("confidence", 0.0))

    return merged