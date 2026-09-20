import json
from typing import List, Dict, Any, Optional
from agents.learner_profile import LearnerProfile
from utils.api_client import query_groq_safe

class LearningPlanAgent:
    """Agent 4: Generates a sequential, time-limited study schedule that fits within available time."""

    def build_study_plan(
        self,
        recommended_resources: List[Dict[str, Any]],
        profile: LearnerProfile,
        groq_api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Builds an ordered, time-boxed study timeline.
        Guarantees total scheduled time <= available_time_minutes.
        """
        if not recommended_resources:
            return {
                "steps": [],
                "total_scheduled_minutes": 0,
                "available_minutes": profile.available_time_minutes,
                "strategy_tip": "No resources available to build a study plan."
            }

        available_mins = profile.available_time_minutes
        
        # Sort recommendations into a natural learning pedagogy:
        # 1. Foundation/Theory (Videos / Articles)
        # 2. In-depth Reference / Formulas (Notes)
        # 3. Hands-on (Practice / Labs)
        type_priority = {"Video": 1, "Articles": 2, "Notes": 3, "Practice": 4}
        sorted_resources = sorted(
            recommended_resources,
            key=lambda x: type_priority.get(x.get("resource_type", "Articles"), 5)
        )

        steps = []
        allocated_time = 0
        
        # Determine how many resources we can fit
        for idx, res in enumerate(sorted_resources):
            duration = int(res.get("duration_minutes", 20))
            
            # Check remaining budget
            remaining_time = available_mins - allocated_time
            if remaining_time < 10:
                break
                
            # If resource takes more than remaining time, scale it to fit remaining budget
            actual_step_duration = min(duration, remaining_time)
            
            # Determine stage name
            res_type = res.get("resource_type", "Concept")
            if res_type == "Video":
                phase = "Visual Foundation"
            elif res_type == "Notes":
                phase = "Core Theory & Key Formulas"
            elif res_type == "Practice":
                phase = "Hands-on Problem Solving"
            else:
                phase = "In-depth Study"

            steps.append({
                "step_number": len(steps) + 1,
                "phase": phase,
                "title": res.get("title"),
                "duration_minutes": actual_step_duration,
                "resource_type": res_type,
                "source": res.get("source"),
                "url": res.get("url"),
                "action_item": f"Complete {res_type.lower()} on {res.get('title')} ({actual_step_duration} mins)"
            })
            allocated_time += actual_step_duration

        # If there is leftover time (e.g. >= 10 mins), add a final Review & Self-Assessment step
        leftover = available_mins - allocated_time
        if leftover >= 10:
            steps.append({
                "step_number": len(steps) + 1,
                "phase": "Review & Self-Assessment",
                "title": f"Quick Summary & Self-Quiz on {profile.topic}",
                "duration_minutes": leftover,
                "resource_type": "Review",
                "source": "Self Study",
                "url": "",
                "action_item": f"Spend {leftover} mins summarizing key points and testing active recall."
            })
            allocated_time += leftover

        # Query Groq for AI Study Strategy Tips
        strategy_tip = self._generate_strategy_with_groq(profile, steps, allocated_time, groq_api_key)

        return {
            "steps": steps,
            "total_scheduled_minutes": allocated_time,
            "available_minutes": available_mins,
            "strategy_tip": strategy_tip,
            "is_within_budget": allocated_time <= available_mins
        }

    def _generate_strategy_with_groq(
        self,
        profile: LearnerProfile,
        steps: List[Dict[str, Any]],
        total_time: int,
        groq_api_key: Optional[str]
    ) -> str:
        """Generates AI study guidance via Groq, with fallback."""
        prompt = f"""
Student Profile:
- Topic: {profile.topic} ({profile.subject})
- Level: {profile.target_level}
- Goal: {profile.learning_goal}
- Study Session Duration: {total_time} minutes ({len(steps)} planned steps)

Provide a 2-3 sentence actionable study strategy and milestone tip for this session. Focus on high efficiency and retention.
"""
        groq_tip = query_groq_safe(prompt, api_key=groq_api_key)
        if groq_tip:
            return groq_tip.strip()
            
        # Fallback heuristic tip
        if "exam" in profile.learning_goal.lower():
            return f"[Study Strategy] Focus on memorizing subnet formulas and powers of 2 first, then practice active recall with timed problems during the final {steps[-1]['duration_minutes']} minutes."
        elif "practice" in profile.learning_goal.lower():
            return f"[Study Strategy] Spend the initial portion reviewing solved examples, then solve at least 5 numerical problems independently without looking at answers."
        else:
            return f"[Study Strategy] Watch the video actively at 1.25x speed with pen and paper, pause to sketch network diagrams, and review your notes immediately after."
