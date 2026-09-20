from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class LearnerProfile:
    subject: str
    topic: str
    current_level: str              # Beginner, Intermediate, Advanced
    learning_goal: str              # Exam Preparation, Concept Understanding, Practice
    preferred_resources: List[str]  # ['Video', 'Notes', 'Articles', 'Practice']
    available_time_minutes: int     # e.g. 120 minutes
    difficulty_feedback: str = "Appropriate" # 'Too Difficult', 'Appropriate', 'Too Easy'
    not_useful_urls: List[str] = field(default_factory=list)
    useful_urls: List[str] = field(default_factory=list)
    
    @property
    def target_level(self) -> str:
        """Effective target level considering feedback adjustment."""
        if self.difficulty_feedback == "Too Difficult":
            if self.current_level.lower() == "advanced":
                return "Intermediate"
            elif self.current_level.lower() == "intermediate":
                return "Beginner"
            return "Beginner"
        elif self.difficulty_feedback == "Too Easy":
            if self.current_level.lower() == "beginner":
                return "Intermediate"
            elif self.current_level.lower() == "intermediate":
                return "Advanced"
            return "Advanced"
        return self.current_level

    def get_search_queries(self) -> List[str]:
        """Generate targeted search queries for Resource Retrieval Agent."""
        queries = []
        fmt_str = " ".join(self.preferred_resources)
        
        # Primary targeted educational query
        queries.append(f"{self.subject} {self.topic} {self.target_level} tutorial {self.learning_goal} {fmt_str}")
        
        # Secondary specific query
        if "exam" in self.learning_goal.lower():
            queries.append(f"{self.subject} {self.topic} notes formula cheat sheet previous questions")
        elif "practice" in self.learning_goal.lower():
            queries.append(f"{self.subject} {self.topic} practice problems mcqs exercises with solutions")
        else:
            queries.append(f"{self.subject} {self.topic} concept explained step by step visual {fmt_str}")
            
        return queries

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "topic": self.topic,
            "current_level": self.current_level,
            "target_level": self.target_level,
            "learning_goal": self.learning_goal,
            "preferred_resources": self.preferred_resources,
            "available_time_minutes": self.available_time_minutes,
            "available_time_formatted": f"{self.available_time_minutes // 60}h {self.available_time_minutes % 60}m" if self.available_time_minutes >= 60 else f"{self.available_time_minutes}m",
            "difficulty_feedback": self.difficulty_feedback
        }


class LearnerProfileAgent:
    """Agent 1: Converts student input and feedback into a structured learner profile."""
    
    @staticmethod
    def build_profile(
        subject: str,
        topic: str,
        level: str,
        goal: str,
        preferred_formats: List[str],
        available_time_val: float,
        time_unit: str = "Hours",
        difficulty_feedback: str = "Appropriate",
        not_useful_urls: Optional[List[str]] = None,
        useful_urls: Optional[List[str]] = None
    ) -> LearnerProfile:
        # Convert time to minutes
        if time_unit.lower().startswith("hour"):
            time_minutes = int(available_time_val * 60)
        else:
            time_minutes = int(available_time_val)
            
        time_minutes = max(15, min(time_minutes, 600)) # 15 min to 10 hours
        
        clean_formats = [f.strip() for f in preferred_formats if f.strip()]
        if not clean_formats:
            clean_formats = ["Video", "Notes"]
            
        return LearnerProfile(
            subject=subject.strip(),
            topic=topic.strip(),
            current_level=level.strip(),
            learning_goal=goal.strip(),
            preferred_resources=clean_formats,
            available_time_minutes=time_minutes,
            difficulty_feedback=difficulty_feedback,
            not_useful_urls=not_useful_urls or [],
            useful_urls=useful_urls or []
        )
