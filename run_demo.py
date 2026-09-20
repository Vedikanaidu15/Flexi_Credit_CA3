import os
import json
from agents.learner_profile import LearnerProfileAgent
from agents.resource_retrieval import ResourceRetrievalAgent
from agents.recommendation import RecommendationAgent
from agents.learning_plan import LearningPlanAgent

def generate_output_report():
    print("Running Multi-Agent Pipeline to generate output results...")
    
    # 1. Learner Profile Agent
    profile = LearnerProfileAgent.build_profile(
        subject="Computer Networks",
        topic="IPv4 and Subnetting",
        level="Beginner",
        goal="Exam Preparation",
        preferred_formats=["Video", "Notes"],
        available_time_val=2.0,
        time_unit="Hours"
    )
    
    # 2. Resource Retrieval Agent
    retrieval_agent = ResourceRetrievalAgent(csv_fallback_path="data/learning_resources.csv")
    raw_resources = retrieval_agent.retrieve_resources(profile)
    
    # 3. Recommendation Agent
    rec_agent = RecommendationAgent(top_k=5)
    recommended = rec_agent.recommend(raw_resources, profile)
    
    # 4. Learning Plan Agent
    plan_agent = LearningPlanAgent()
    plan = plan_agent.build_study_plan(recommended, profile)
    
    # Prepare comprehensive result object
    results_data = {
        "learner_profile": profile.to_dict(),
        "candidate_resources_found": len(raw_resources),
        "top_recommendations": recommended,
        "study_plan": plan
    }
    
    # Save as JSON output file
    json_path = "output_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)
    print(f"[OK] Generated JSON output file: {json_path}")
    
    # Save as formatted Markdown output file
    md_path = "output_results.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 🎓 Generated Learning Recommendations & Study Plan\n\n")
        f.write("## 👤 1. Learner Profile\n")
        f.write(f"- **Subject:** {profile.subject}\n")
        f.write(f"- **Topic:** {profile.topic}\n")
        f.write(f"- **Level:** {profile.target_level}\n")
        f.write(f"- **Goal:** {profile.learning_goal}\n")
        f.write(f"- **Preferred Formats:** {', '.join(profile.preferred_resources)}\n")
        f.write(f"- **Available Time:** {profile.available_time_minutes} minutes (2.0 Hours)\n\n")
        
        f.write("## 📚 2. Top Recommended Resources (Ranked by 5-Factor Scoring)\n\n")
        for i, r in enumerate(recommended):
            f.write(f"### {i+1}. {r.get('title')}\n")
            f.write(f"- **Match Score:** **`{r.get('score')}%`**\n")
            f.write(f"- **Source:** {r.get('source')} | **Type:** {r.get('resource_type')} | **Level:** {r.get('difficulty_level')} | **Duration:** {r.get('duration_minutes')} mins\n")
            f.write(f"- **URL:** [{r.get('url')}]({r.get('url')})\n")
            f.write(f"- **Description:** {r.get('description')}\n")
            f.write(f"- **💡 Why Recommended:** {r.get('why_recommended')}\n")
            b = r.get('scoring_breakdown', {})
            f.write(f"- **Scoring Breakdown:** Topic: {b.get('topic_score')}% | Level: {b.get('level_score')}% | Goal: {b.get('goal_score')}% | Format: {b.get('format_score')}% | Time: {b.get('time_score')}%\n\n")
            
        f.write("## ⏱️ 3. Personalised Time-Limited Study Schedule\n\n")
        f.write(f"- **Total Allocated Time:** {plan.get('total_scheduled_minutes')} mins / {plan.get('available_minutes')} mins\n")
        f.write(f"- **AI Strategy Tip:** {plan.get('strategy_tip')}\n\n")
        
        f.write("| Step | Phase | Activity & Title | Duration | Resource Type | Action Link |\n")
        f.write("|---|---|---|---|---|---|\n")
        for s in plan.get("steps", []):
            url_link = f"[Open Link]({s.get('url')})" if s.get('url') else "Self Study"
            f.write(f"| {s.get('step_number')} | **{s.get('phase')}** | {s.get('title')} | {s.get('duration_minutes')} mins | {s.get('resource_type')} | {url_link} |\n")
            
    print(f"[OK] Generated Markdown output file: {md_path}")
    print("\nAll output files created successfully!")

if __name__ == "__main__":
    generate_output_report()
