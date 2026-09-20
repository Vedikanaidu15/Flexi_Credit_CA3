import os
import unittest
from agents.learner_profile import LearnerProfileAgent, LearnerProfile
from agents.resource_retrieval import ResourceRetrievalAgent
from agents.recommendation import RecommendationAgent
from agents.learning_plan import LearningPlanAgent
from utils.scoring import score_resource, calculate_level_match, calculate_goal_match, calculate_format_match

class TestPersonalisedLearningAgent(unittest.TestCase):

    # 1. Test Learner Profile Agent
    def test_learner_profile_creation(self):
        profile = LearnerProfileAgent.build_profile(
            subject="Computer Networks",
            topic="IPv4 and Subnetting",
            level="Beginner",
            goal="Exam Preparation",
            preferred_formats=["Video", "Notes"],
            available_time_val=2.0,
            time_unit="Hours"
        )
        self.assertEqual(profile.subject, "Computer Networks")
        self.assertEqual(profile.topic, "IPv4 and Subnetting")
        self.assertEqual(profile.available_time_minutes, 120)
        self.assertEqual(profile.target_level, "Beginner")
        
        queries = profile.get_search_queries()
        self.assertGreaterEqual(len(queries), 2)
        self.assertIn("IPv4 and Subnetting", queries[0])

    # 2. Test Scoring changes for Different Learning Levels
    def test_scoring_different_levels(self):
        beginner_res = {
            "title": "IPv4 Basics for Beginners",
            "topic": "IPv4 and Subnetting",
            "resource_type": "Video",
            "difficulty_level": "Beginner",
            "learning_goal": "Concept Understanding",
            "duration_minutes": 25,
            "description": "Introductory guide"
        }
        
        adv_res = {
            "title": "Advanced VLSM Routing",
            "topic": "IPv4 and Subnetting",
            "resource_type": "Video",
            "difficulty_level": "Advanced",
            "learning_goal": "Concept Understanding",
            "duration_minutes": 25,
            "description": "Complex prefix aggregation"
        }
        
        # When user is Beginner
        score_b_user_b_res, _ = score_resource(beginner_res, "Computer Networks", "IPv4 and Subnetting", "Beginner", "Concept Understanding", ["Video"], 120)
        score_b_user_a_res, _ = score_resource(adv_res, "Computer Networks", "IPv4 and Subnetting", "Beginner", "Concept Understanding", ["Video"], 120)
        self.assertGreater(score_b_user_b_res, score_b_user_a_res, "Beginner resource should score higher for a beginner student")
        
        # When user is Advanced
        score_a_user_b_res, _ = score_resource(beginner_res, "Computer Networks", "IPv4 and Subnetting", "Advanced", "Concept Understanding", ["Video"], 120)
        score_a_user_a_res, _ = score_resource(adv_res, "Computer Networks", "IPv4 and Subnetting", "Advanced", "Concept Understanding", ["Video"], 120)
        self.assertGreater(score_a_user_a_res, score_a_user_b_res, "Advanced resource should score higher for an advanced student")

    # 3. Test Scoring changes for Different Goals
    def test_scoring_different_goals(self):
        notes_res = {
            "title": "Subnetting Cheat Sheet",
            "topic": "IPv4 and Subnetting",
            "resource_type": "Notes",
            "difficulty_level": "Beginner",
            "learning_goal": "Exam Preparation",
            "duration_minutes": 20,
            "description": "Fast revision notes"
        }
        
        practice_res = {
            "title": "Subnetting Practice MCQs",
            "topic": "IPv4 and Subnetting",
            "resource_type": "Practice",
            "difficulty_level": "Beginner",
            "learning_goal": "Practice",
            "duration_minutes": 35,
            "description": "Practice set"
        }
        
        score_exam_goal, _ = score_resource(notes_res, "Computer Networks", "IPv4 and Subnetting", "Beginner", "Exam Preparation", ["Notes"], 120)
        score_practice_goal, _ = score_resource(practice_res, "Computer Networks", "IPv4 and Subnetting", "Beginner", "Practice", ["Practice"], 120)
        
        self.assertGreaterEqual(score_exam_goal, 80.0)
        self.assertGreaterEqual(score_practice_goal, 80.0)

    # 4. Test Scoring changes for Different Formats
    def test_scoring_different_formats(self):
        video_match = calculate_format_match("Video", ["Video"])
        video_mismatch = calculate_format_match("Video", ["Notes", "Practice"])
        self.assertGreater(video_match, video_mismatch)
        self.assertEqual(video_match, 1.0)

    # 5. Test Study Plan Duration Compliance for Different Available Times
    def test_learning_plan_time_constraint(self):
        profile_short = LearnerProfileAgent.build_profile(
            subject="Computer Networks",
            topic="IPv4 and Subnetting",
            level="Beginner",
            goal="Exam Preparation",
            preferred_formats=["Video", "Notes"],
            available_time_val=45,
            time_unit="Minutes"
        )
        
        sample_resources = [
            {"id": "1", "title": "Subnetting Intro Video", "resource_type": "Video", "duration_minutes": 25, "source": "YouTube", "url": "https://youtube.com/1"},
            {"id": "2", "title": "Formula Notes", "resource_type": "Notes", "duration_minutes": 20, "source": "GFG", "url": "https://gfg.org/2"},
            {"id": "3", "title": "Big Practice Lab", "resource_type": "Practice", "duration_minutes": 60, "source": "LeetCode", "url": "https://leetcode.com/3"}
        ]
        
        plan_agent = LearningPlanAgent()
        plan = plan_agent.build_study_plan(sample_resources, profile_short)
        
        self.assertLessEqual(plan["total_scheduled_minutes"], 45)
        self.assertTrue(plan["is_within_budget"])

    # 6. Test Feedback Mechanism (Too Difficult & Negative URL feedback)
    def test_feedback_adaptation(self):
        # Difficulty feedback shifts target level
        profile_adv = LearnerProfileAgent.build_profile(
            subject="DBMS",
            topic="Normalization",
            level="Advanced",
            goal="Exam Preparation",
            preferred_formats=["Notes"],
            available_time_val=1.0,
            time_unit="Hours",
            difficulty_feedback="Too Difficult"
        )
        self.assertEqual(profile_adv.target_level, "Intermediate")
        
        # Negative URL feedback penalizes resource
        dummy_res = {
            "title": "Unhelpful Resource",
            "topic": "Normalization",
            "resource_type": "Notes",
            "difficulty_level": "Intermediate",
            "learning_goal": "Exam Preparation",
            "duration_minutes": 20,
            "url": "https://example.com/unhelpful",
            "description": "Some description"
        }
        
        normal_score, _ = score_resource(dummy_res, "DBMS", "Normalization", "Intermediate", "Exam Preparation", ["Notes"], 60)
        penalized_score, _ = score_resource(dummy_res, "DBMS", "Normalization", "Intermediate", "Exam Preparation", ["Notes"], 60, not_useful_urls=["https://example.com/unhelpful"])
        
        self.assertLess(penalized_score, normal_score)
        self.assertGreaterEqual(normal_score - penalized_score, 30)

    # 7. Test Offline Retrieval Fallback
    def test_retrieval_offline_fallback(self):
        profile = LearnerProfileAgent.build_profile(
            subject="Computer Networks",
            topic="IPv4 and Subnetting",
            level="Beginner",
            goal="Exam Preparation",
            preferred_formats=["Video", "Notes"],
            available_time_val=2.0,
            time_unit="Hours"
        )
        
        # Passing None for API key forces local CSV fallback
        agent = ResourceRetrievalAgent(csv_fallback_path="data/learning_resources.csv")
        resources = agent.retrieve_resources(profile, tavily_api_key=None)
        
        self.assertGreaterEqual(len(resources), 3)
        self.assertTrue(any("subnet" in r["title"].lower() or "ipv4" in r["title"].lower() for r in resources))

if __name__ == "__main__":
    unittest.main()
