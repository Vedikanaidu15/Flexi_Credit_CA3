import os
import csv
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from agents.learner_profile import LearnerProfile
from utils.api_client import search_tavily_safe

def infer_resource_type(title: str, url: str, snippet: str) -> str:
    """Infer the format/type of the web resource."""
    combined = (f"{title} {url} {snippet}").lower()
    if "youtube.com" in url or "youtu.be" in url or "video" in combined or "lecture" in combined:
        return "Video"
    elif "quiz" in combined or "practice" in combined or "mcq" in combined or "leetcode.com" in url or "problems" in combined or "lab" in combined:
        return "Practice"
    elif "geeksforgeeks.org" in url or "tutorialspoint.com" in url or "w3schools.com" in url or "notes" in combined or "cheat sheet" in combined:
        return "Notes"
    elif "medium.com" in url or "wikipedia.org" in url or "article" in combined:
        return "Articles"
    return "Articles"

def infer_difficulty_and_duration(title: str, snippet: str, res_type: str, profile_level: str) -> (str, int):
    """Infer difficulty and estimated study duration."""
    combined = (f"{title} {snippet}").lower()
    
    # Difficulty
    if "advanced" in combined or "vlsm" in combined or "complex" in combined or "deep dive" in combined:
        level = "Advanced"
    elif "beginner" in combined or "intro" in combined or "explained" in combined or "basics" in combined:
        level = "Beginner"
    elif "intermediate" in combined or "practice" in combined:
        level = "Intermediate"
    else:
        level = profile_level  # Default to learner's targeted level
        
    # Duration (minutes)
    if res_type == "Video":
        duration = 25
    elif res_type == "Notes":
        duration = 20
    elif res_type == "Practice":
        duration = 35
    else:
        duration = 20
        
    return level, duration

def extract_source_name(url: str) -> str:
    """Extract human-readable source from URL."""
    try:
        domain = urlparse(url).netloc.replace("www.", "")
        if "youtube.com" in domain or "youtu.be" in domain:
            return "YouTube"
        elif "geeksforgeeks.org" in domain:
            return "GeeksforGeeks"
        elif "sanfoundry.com" in domain:
            return "Sanfoundry"
        elif "leetcode.com" in domain:
            return "LeetCode"
        elif "wikipedia.org" in domain:
            return "Wikipedia"
        elif "cisco.com" in domain:
            return "Cisco Networking"
        elif "tutorialspoint.com" in domain:
            return "TutorialsPoint"
        return domain.capitalize()
    except Exception:
        return "Web Resource"

class ResourceRetrievalAgent:
    """Agent 2: Uses Tavily API to retrieve educational resources, with CSV fallback."""
    
    def __init__(self, csv_fallback_path: str = "data/learning_resources.csv"):
        self.csv_fallback_path = csv_fallback_path

    def load_csv_resources(self, profile: LearnerProfile) -> List[Dict[str, Any]]:
        """Load and filter matching resources from local CSV fallback dataset."""
        resources = []
        if not os.path.exists(self.csv_fallback_path):
            return resources
            
        with open(self.csv_fallback_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Basic matching on subject or topic or general relevance
                subj_match = profile.subject.lower() in row.get("subject", "").lower() or row.get("subject", "").lower() in profile.subject.lower()
                topic_match = profile.topic.lower() in row.get("topic", "").lower() or row.get("topic", "").lower() in profile.topic.lower()
                
                # Check keyword overlap if not exact match
                if not (subj_match or topic_match):
                    query_words = set((profile.subject + " " + profile.topic).lower().split())
                    row_words = set((row.get("subject", "") + " " + row.get("topic", "") + " " + row.get("title", "")).lower().split())
                    if not (query_words & row_words):
                        continue
                        
                resources.append({
                    "id": row.get("id", ""),
                    "title": row.get("title", ""),
                    "subject": row.get("subject", profile.subject),
                    "topic": row.get("topic", profile.topic),
                    "resource_type": row.get("resource_type", "Article"),
                    "difficulty_level": row.get("difficulty_level", "Beginner"),
                    "learning_goal": row.get("learning_goal", "Concept Understanding"),
                    "duration_minutes": int(row.get("duration_minutes", 25)),
                    "url": row.get("url", "https://example.com"),
                    "source": row.get("source", "Curated Repository"),
                    "description": row.get("description", ""),
                    "retrieval_source": "Local Curated Dataset (Fallback)"
                })
        return resources

    def retrieve_resources(self, profile: LearnerProfile, tavily_api_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves resources via Tavily API search.
        Gracefully integrates local CSV resources if Tavily returns few or no results.
        """
        retrieved: List[Dict[str, Any]] = []
        seen_urls = set()
        
        # 1. Try Live Tavily Search
        search_queries = profile.get_search_queries()
        for q in search_queries[:2]:  # Run top 2 queries
            tavily_results = search_tavily_safe(q, api_key=tavily_api_key, max_results=5)
            for item in tavily_results:
                url = item.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                title = item.get("title", "Educational Resource")
                snippet = item.get("content", "")
                res_type = infer_resource_type(title, url, snippet)
                diff_lvl, duration = infer_difficulty_and_duration(title, snippet, res_type, profile.target_level)
                
                retrieved.append({
                    "id": f"tavily_{len(retrieved)+1}",
                    "title": title,
                    "subject": profile.subject,
                    "topic": profile.topic,
                    "resource_type": res_type,
                    "difficulty_level": diff_lvl,
                    "learning_goal": profile.learning_goal,
                    "duration_minutes": duration,
                    "url": url,
                    "source": extract_source_name(url),
                    "description": snippet[:200] + "..." if len(snippet) > 200 else snippet,
                    "retrieval_source": "Live Tavily Web Search"
                })
                
        # 2. Check if we need local CSV dataset (if Tavily returned 0 or few items, or for benchmark richness)
        csv_items = self.load_csv_resources(profile)
        for item in csv_items:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                retrieved.append(item)
                
        # If still empty (e.g. exotic query with no API key and no exact CSV match), synthesize curated resources based on topic
        if not retrieved:
            retrieved = self._generate_fallback_defaults(profile)
            
        return retrieved

    def _generate_fallback_defaults(self, profile: LearnerProfile) -> List[Dict[str, Any]]:
        """Synthesizes structured topic resources as a guaranteed safety net."""
        return [
            {
                "id": "syn_1",
                "title": f"{profile.topic} - Comprehensive Guide & Concept Breakdown",
                "subject": profile.subject,
                "topic": profile.topic,
                "resource_type": "Video" if "Video" in profile.preferred_resources else "Articles",
                "difficulty_level": profile.target_level,
                "learning_goal": profile.learning_goal,
                "duration_minutes": 25,
                "url": f"https://www.youtube.com/results?search_query={profile.subject}+{profile.topic}",
                "source": "Educational Platform",
                "description": f"In-depth core tutorial covering foundational and practical concepts of {profile.topic}.",
                "retrieval_source": "Synthesized Fallback Repository"
            },
            {
                "id": "syn_2",
                "title": f"{profile.topic} Quick Revision Notes & Formulas",
                "subject": profile.subject,
                "topic": profile.topic,
                "resource_type": "Notes",
                "difficulty_level": "Beginner",
                "learning_goal": "Exam Preparation",
                "duration_minutes": 20,
                "url": f"https://www.geeksforgeeks.org/search/?q={profile.topic}",
                "source": "GeeksforGeeks",
                "description": f"Curated cheat sheet, standard definitions, and important exam questions for {profile.topic}.",
                "retrieval_source": "Synthesized Fallback Repository"
            },
            {
                "id": "syn_3",
                "title": f"{profile.topic} Practice Problems & MCQ Solutions",
                "subject": profile.subject,
                "topic": profile.topic,
                "resource_type": "Practice",
                "difficulty_level": "Intermediate",
                "learning_goal": "Practice",
                "duration_minutes": 35,
                "url": f"https://www.sanfoundry.com/?s={profile.topic}",
                "source": "Sanfoundry",
                "description": f"Hands-on exercises and step-by-step problem sets to test understanding of {profile.topic}.",
                "retrieval_source": "Synthesized Fallback Repository"
            }
        ]
