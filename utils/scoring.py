from typing import Dict, Any, List, Tuple

# Exact weights requested
WEIGHT_TOPIC = 0.35
WEIGHT_LEVEL = 0.20
WEIGHT_GOAL = 0.20
WEIGHT_FORMAT = 0.15
WEIGHT_TIME = 0.10

def calculate_topic_relevance(resource_topic: str, resource_title: str, resource_desc: str, query_subject: str, query_topic: str) -> float:
    """Calculate topic relevance between 0.0 and 1.0."""
    target_words = set((query_subject.lower() + " " + query_topic.lower()).replace(",", " ").split())
    text_content = (f"{resource_topic} {resource_title} {resource_desc}").lower()
    
    # Exact topic match in text
    if query_topic.lower() in text_content:
        return 1.0
    
    # Keyword overlap ratio
    matched = sum(1 for word in target_words if word in text_content and len(word) > 2)
    total = len([w for w in target_words if len(w) > 2]) or 1
    overlap = matched / total
    
    # Base relevance score
    return min(1.0, max(0.2, overlap))

def calculate_level_match(resource_level: str, learner_level: str, difficulty_feedback: str = "Appropriate") -> float:
    """
    Calculate level compatibility (0.0 - 1.0) factoring in user feedback.
    Difficulty feedback can be: 'Too Difficult', 'Appropriate', 'Too Easy'.
    """
    res_lvl = resource_level.strip().capitalize()
    target_lvl = learner_level.strip().capitalize()
    
    # Adjust target level if learner gave feedback
    if difficulty_feedback == "Too Difficult":
        if target_lvl == "Advanced":
            target_lvl = "Intermediate"
        elif target_lvl == "Intermediate":
            target_lvl = "Beginner"
    elif difficulty_feedback == "Too Easy":
        if target_lvl == "Beginner":
            target_lvl = "Intermediate"
        elif target_lvl == "Intermediate":
            target_lvl = "Advanced"
            
    levels = ["Beginner", "Intermediate", "Advanced"]
    try:
        idx_res = levels.index(res_lvl)
    except ValueError:
        idx_res = 0
        
    try:
        idx_target = levels.index(target_lvl)
    except ValueError:
        idx_target = 0
        
    distance = abs(idx_res - idx_target)
    if distance == 0:
        return 1.0
    elif distance == 1:
        return 0.65
    else:
        return 0.25

def calculate_goal_match(resource_goal: str, learner_goal: str, resource_type: str) -> float:
    """Calculate alignment between resource and learner goal."""
    res_g = resource_goal.strip().lower()
    learn_g = learner_goal.strip().lower()
    res_t = resource_type.strip().lower()
    
    if learn_g in res_g or res_g in learn_g:
        return 1.0
        
    # Semantic goal heuristics
    if "exam" in learn_g:
        if "notes" in res_t or "practice" in res_t or "exam" in res_g:
            return 0.90
        return 0.60
    elif "concept" in learn_g:
        if "video" in res_t or "article" in res_t or "concept" in res_g:
            return 0.95
        return 0.60
    elif "practice" in learn_g:
        if "practice" in res_t or "quiz" in res_t or "lab" in res_t:
            return 1.0
        return 0.40
    return 0.70

def calculate_format_match(resource_type: str, preferred_formats: List[str]) -> float:
    """Calculate format compatibility."""
    if not preferred_formats:
        return 0.8
    res_type_lower = resource_type.strip().lower()
    preferred_lower = [f.strip().lower() for f in preferred_formats]
    
    # Direct match or substring match
    for pref in preferred_lower:
        if pref in res_type_lower or res_type_lower in pref:
            return 1.0
        # Notes & Articles semantic similarity
        if pref in ["notes", "articles"] and res_type_lower in ["notes", "article", "articles", "text"]:
            return 0.9
        if pref == "practice" and res_type_lower in ["practice", "quiz", "exercise", "lab"]:
            return 1.0
        if pref == "video" and res_type_lower in ["video", "youtube", "lecture"]:
            return 1.0
            
    return 0.35

def calculate_time_compatibility(resource_duration: int, available_time_minutes: int) -> float:
    """Calculate if resource fits into study schedule."""
    if available_time_minutes <= 0:
        return 0.5
    if resource_duration <= available_time_minutes:
        # Ideal: takes between 15% and 50% of available study time
        ratio = resource_duration / available_time_minutes
        if 0.1 <= ratio <= 0.6:
            return 1.0
        elif ratio <= 0.9:
            return 0.85
        else:
            return 0.70
    else:
        # Exceeds total available time
        over_ratio = (resource_duration - available_time_minutes) / available_time_minutes
        return max(0.1, 0.5 - over_ratio * 0.4)

def score_resource(
    resource: Dict[str, Any],
    subject: str,
    topic: str,
    learner_level: str,
    learner_goal: str,
    preferred_formats: List[str],
    available_time_minutes: int,
    difficulty_feedback: str = "Appropriate",
    not_useful_urls: List[str] = None
) -> Tuple[float, Dict[str, float]]:
    """
    Computes transparent multi-criteria composite score.
    Returns: (total_score_100, breakdown_dict)
    """
    not_useful_urls = not_useful_urls or []
    
    # 1. Topic Relevance (35%)
    r_topic = calculate_topic_relevance(
        resource.get("topic", ""),
        resource.get("title", ""),
        resource.get("description", ""),
        subject,
        topic
    )
    
    # 2. Level Match (20%)
    r_level = calculate_level_match(
        resource.get("difficulty_level", "Beginner"),
        learner_level,
        difficulty_feedback
    )
    
    # 3. Goal Match (20%)
    r_goal = calculate_goal_match(
        resource.get("learning_goal", "Concept Understanding"),
        learner_goal,
        resource.get("resource_type", "Article")
    )
    
    # 4. Preferred Format (15%)
    r_format = calculate_format_match(
        resource.get("resource_type", "Article"),
        preferred_formats
    )
    
    # 5. Time Compatibility (10%)
    r_time = calculate_time_compatibility(
        int(resource.get("duration_minutes", 30)),
        available_time_minutes
    )
    
    weighted_score = (
        (r_topic * WEIGHT_TOPIC) +
        (r_level * WEIGHT_LEVEL) +
        (r_goal * WEIGHT_GOAL) +
        (r_format * WEIGHT_FORMAT) +
        (r_time * WEIGHT_TIME)
    ) * 100.0
    
    # Apply negative penalty if user previously flagged URL as Not Useful
    if resource.get("url") in not_useful_urls:
        weighted_score = max(5.0, weighted_score - 40.0)
        
    breakdown = {
        "topic_score": round(r_topic * 100, 1),
        "level_score": round(r_level * 100, 1),
        "goal_score": round(r_goal * 100, 1),
        "format_score": round(r_format * 100, 1),
        "time_score": round(r_time * 100, 1),
        "total_score": round(weighted_score, 1)
    }
    
    return round(weighted_score, 1), breakdown
