import json
from typing import List, Dict, Any, Optional
from agents.learner_profile import LearnerProfile
from utils.scoring import score_resource
from utils.api_client import query_groq_safe

class RecommendationAgent:
    """Agent 3: Ranks resources using a transparent multi-criteria formula & generates AI reasoning via Groq."""
    
    def __init__(self, top_k: int = 5):
        self.top_k = top_k

    def rank_resources(
        self,
        resources: List[Dict[str, Any]],
        profile: LearnerProfile
    ) -> List[Dict[str, Any]]:
        """Applies mathematical scoring formula to rank candidate resources."""
        scored_list = []
        
        for res in resources:
            score, breakdown = score_resource(
                resource=res,
                subject=profile.subject,
                topic=profile.topic,
                learner_level=profile.target_level,
                learner_goal=profile.learning_goal,
                preferred_formats=profile.preferred_resources,
                available_time_minutes=profile.available_time_minutes,
                difficulty_feedback=profile.difficulty_feedback,
                not_useful_urls=profile.not_useful_urls
            )
            
            res_copy = dict(res)
            res_copy["score"] = score
            res_copy["scoring_breakdown"] = breakdown
            scored_list.append(res_copy)
            
        # Sort descending by score
        scored_list.sort(key=lambda x: x["score"], reverse=True)
        return scored_list[:self.top_k]

    def generate_reasoning_with_groq(
        self,
        top_resources: List[Dict[str, Any]],
        profile: LearnerProfile,
        groq_api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Uses Groq LLM to generate concise, tailored 'Why Recommended' reasoning for each top resource.
        Falls back to rule-based explanation if Groq is unavailable.
        """
        if not top_resources:
            return []

        # Prepare prompt for Groq
        resources_summary = []
        for i, r in enumerate(top_resources):
            resources_summary.append({
                "index": i,
                "title": r.get("title"),
                "type": r.get("resource_type"),
                "level": r.get("difficulty_level"),
                "duration": f"{r.get('duration_minutes')} mins",
                "score": r.get("score")
            })

        prompt = f"""
You are an expert AI Academic Advisor.
Learner Profile:
- Subject: {profile.subject}
- Topic: {profile.topic}
- Current Level: {profile.target_level}
- Goal: {profile.learning_goal}
- Preferred Formats: {', '.join(profile.preferred_resources)}
- Available Study Time: {profile.available_time_minutes} minutes
- Recent Feedback Context: {profile.difficulty_feedback}

Selected Top Educational Resources:
{json.dumps(resources_summary, indent=2)}

Task:
For EACH resource index (0 to {len(top_resources)-1}), write a concise, punchy 1-2 sentence explanation of "Why Recommended" explaining specifically how it matches their level, format preference, and study goal.

Return ONLY a valid JSON array of strings in the exact order of resource index. Example:
[
  "Directly matches your Beginner level with visual walkthroughs optimal for exam review.",
  "Provides structured notes and formulas to solidify your conceptual understanding within 20 mins."
]
"""
        groq_response = query_groq_safe(prompt, api_key=groq_api_key)
        
        reasoning_list = None
        if groq_response:
            try:
                # Clean markdown blocks if LLM wrapped in ```json
                cleaned = groq_response.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1]
                    if cleaned.endswith("```"):
                        cleaned = cleaned.rsplit("```", 1)[0]
                reasoning_list = json.loads(cleaned.strip())
            except Exception as e:
                print(f"[Recommendation Agent] Could not parse Groq JSON: {e}")
                reasoning_list = None

        # Assign reasoning (or fallback if Groq failed/unavailable)
        for i, res in enumerate(top_resources):
            if reasoning_list and i < len(reasoning_list) and isinstance(reasoning_list[i], str):
                res["why_recommended"] = reasoning_list[i]
                res["reasoning_source"] = "Groq LLaMA-3.3 Reasoning Engine"
            else:
                res["why_recommended"] = self._generate_algorithmic_reasoning(res, profile)
                res["reasoning_source"] = "Algorithmic Rule Engine (Fallback)"
                
        return top_resources

    def _generate_algorithmic_reasoning(self, resource: Dict[str, Any], profile: LearnerProfile) -> str:
        """Rule-based reasoning generator as a reliable fallback."""
        r_type = resource.get("resource_type", "Resource")
        r_level = resource.get("difficulty_level", "Beginner")
        r_dur = resource.get("duration_minutes", 25)
        
        reasons = []
        if r_level.lower() == profile.target_level.lower():
            reasons.append(f"Calibrated for your {profile.target_level} level")
        else:
            reasons.append(f"Provides structured progression to {r_level} concepts")
            
        if r_type in profile.preferred_resources:
            reasons.append(f"matches preferred '{r_type}' format")
            
        if "exam" in profile.learning_goal.lower():
            reasons.append("high-yield focus for exam revision")
        elif "practice" in profile.learning_goal.lower():
            reasons.append("hands-on problem-solving application")
        else:
            reasons.append("solidifies fundamental conceptual clarity")
            
        return f"{', '.join(reasons)}. Fits easily into your study session ({r_dur}m)."

    def recommend(
        self,
        resources: List[Dict[str, Any]],
        profile: LearnerProfile,
        groq_api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Full pipeline: score, rank, and explain."""
        top_ranked = self.rank_resources(resources, profile)
        return self.generate_reasoning_with_groq(top_ranked, profile, groq_api_key)
