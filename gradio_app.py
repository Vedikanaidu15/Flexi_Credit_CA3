import os
import gradio as gr
from dotenv import load_dotenv
from agents.learner_profile import LearnerProfileAgent
from agents.resource_retrieval import ResourceRetrievalAgent
from agents.recommendation import RecommendationAgent
from agents.learning_plan import LearningPlanAgent
from utils.api_client import get_tavily_api_key, get_groq_api_key

load_dotenv()

def generate_learning_recommendations(
    subject: str,
    topic: str,
    level: str,
    goal: str,
    preferred_formats: list,
    available_time: float,
    custom_tavily_key: str = "",
    custom_groq_key: str = "",
    difficulty_feedback: str = "Appropriate"
):
    if not subject or not subject.strip():
        return "⚠️ Please enter a Subject to proceed.", "", ""
    if not topic or not topic.strip():
        return "⚠️ Please enter a Topic to proceed.", "", ""
    if not preferred_formats:
        preferred_formats = ["Video", "Notes"]

    # Resolve API keys: custom input overrides environment variable
    effective_tavily = custom_tavily_key.strip() if custom_tavily_key and custom_tavily_key.strip() else get_tavily_api_key()
    effective_groq = custom_groq_key.strip() if custom_groq_key and custom_groq_key.strip() else get_groq_api_key()

    # 1. Learner Profile Agent
    profile = LearnerProfileAgent.build_profile(
        subject=subject,
        topic=topic,
        level=level,
        goal=goal,
        preferred_formats=preferred_formats,
        available_time_val=float(available_time),
        time_unit="Hours",
        difficulty_feedback=difficulty_feedback
    )

    # 2. Resource Retrieval Agent
    retrieval_agent = ResourceRetrievalAgent()
    raw_resources = retrieval_agent.retrieve_resources(profile, tavily_api_key=effective_tavily)

    # 3. Recommendation Agent
    rec_agent = RecommendationAgent(top_k=5)
    recommended = rec_agent.recommend(raw_resources, profile, groq_api_key=effective_groq)

    # 4. Learning Plan Agent
    plan_agent = LearningPlanAgent()
    plan = plan_agent.build_study_plan(recommended, profile, groq_api_key=effective_groq)

    # Build Profile HTML
    profile_html = f"""
    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
        <h3 style="margin-top:0; color: #1e293b;">👤 Synthesized Learner Profile</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px;">
            <div><strong>Subject:</strong> {profile.subject}</div>
            <div><strong>Topic:</strong> {profile.topic}</div>
            <div><strong>Target Level:</strong> <span style="background:#e0f2fe; color:#0369a1; padding:2px 8px; border-radius:12px; font-weight:600;">{profile.target_level}</span></div>
            <div><strong>Learning Goal:</strong> {profile.learning_goal}</div>
            <div><strong>Preferred Formats:</strong> {', '.join(profile.preferred_resources)}</div>
            <div><strong>Time Budget:</strong> {profile.available_time_minutes} mins ({profile.available_time_minutes / 60:.1f} hrs)</div>
        </div>
    </div>
    """

    # Build Recommendations HTML
    rec_html = """
    <div style="margin-bottom: 20px;">
        <h3 style="color: #1e293b;">📚 Top Recommended Learning Resources</h3>
        <p style="color: #64748b; font-size: 0.9rem;">Ranked by multi-criteria scoring (Topic 35%, Level 20%, Goal 20%, Format 15%, Time 10%) + Groq AI reasoning.</p>
    """
    for i, r in enumerate(recommended):
        score = r.get("score", 0)
        bd = r.get("scoring_breakdown", {})
        breakdown_text = f"Topic: {bd.get('topic_score')}% | Level: {bd.get('level_score')}% | Goal: {bd.get('goal_score')}% | Format: {bd.get('format_score')}% | Time: {bd.get('time_score')}%"
        
        rec_html += f"""
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; padding: 16px; margin-bottom: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.03);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
                <h4 style="margin: 0; color: #0f172a;">{i+1}. {r.get('title')}</h4>
                <span style="background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white; padding: 4px 10px; border-radius: 8px; font-weight: 700; font-size: 0.85rem;">Match: {score}%</span>
            </div>
            <div style="margin: 8px 0; font-size: 0.82rem;">
                <span style="background:#f1f5f9; color:#334155; padding:2px 8px; border-radius:12px; margin-right:4px;">🌐 {r.get('source')}</span>
                <span style="background:#eff6ff; color:#1d4ed8; padding:2px 8px; border-radius:12px; margin-right:4px;">📖 {r.get('resource_type')}</span>
                <span style="background:#f0fdf4; color:#15803d; padding:2px 8px; border-radius:12px; margin-right:4px;">📊 {r.get('difficulty_level')}</span>
                <span style="background:#fff7ed; color:#c2410c; padding:2px 8px; border-radius:12px; margin-right:4px;">⏱️ {r.get('duration_minutes')} mins</span>
            </div>
            <p style="margin: 6px 0; font-size: 0.9rem; color: #475569;">{r.get('description')}</p>
            <div style="background: #eef2ff; border-left: 3px solid #6366f1; padding: 6px 10px; border-radius: 4px; margin: 8px 0; font-size: 0.85rem; color: #3730a3;">
                <strong>💡 Why Recommended:</strong> {r.get('why_recommended')}
            </div>
            <div style="font-size: 0.78rem; color: #64748b; margin-bottom: 8px;">
                🔍 <em>Breakdown: {breakdown_text}</em>
            </div>
            <a href="{r.get('url')}" target="_blank" style="display: inline-block; background: #2563eb; color: white; text-decoration: none; padding: 6px 12px; border-radius: 6px; font-size: 0.82rem; font-weight: 600;">🔗 Open Resource</a>
        </div>
        """
    rec_html += "</div>"

    # Build Study Plan HTML
    plan_steps = plan.get("steps", [])
    total_time = plan.get("total_scheduled_minutes", 0)
    avail_time = plan.get("available_minutes", 0)
    strategy = plan.get("strategy_tip", "")

    plan_html = f"""
    <div style="margin-top: 10px;">
        <h3 style="color: #1e293b;">⏱️ Personalised Time-Limited Study Schedule</h3>
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 0.9rem; color: #166534;">
            <strong>📅 Allocated Time:</strong> {total_time} mins / {avail_time} mins available | <strong>Status:</strong> {'✅ Within Budget' if plan.get('is_within_budget') else '⚠️ Exceeded'}
        </div>
        <div style="background: #faf5ff; border-left: 4px solid #a855f7; border-radius: 4px; padding: 8px 12px; margin-bottom: 14px; font-size: 0.88rem; color: #581c87;">
            <strong>🎯 AI Study Strategy:</strong> {strategy}
        </div>
        <table style="width: 100%; border-collapse: collapse; font-size: 0.88rem; text-align: left;">
            <thead>
                <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1;">
                    <th style="padding: 8px;">Step</th>
                    <th style="padding: 8px;">Phase</th>
                    <th style="padding: 8px;">Activity / Title</th>
                    <th style="padding: 8px;">Duration</th>
                    <th style="padding: 8px;">Type</th>
                    <th style="padding: 8px;">Action</th>
                </tr>
            </thead>
            <tbody>
    """
    for s in plan_steps:
        link_elem = f'<a href="{s.get("url")}" target="_blank" style="color:#2563eb; font-weight:600;">Open Link</a>' if s.get("url") else 'Self Study'
        plan_html += f"""
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 8px; font-weight:600;">{s.get('step_number')}</td>
                    <td style="padding: 8px; color:#4f46e5; font-weight:500;">{s.get('phase')}</td>
                    <td style="padding: 8px;">{s.get('title')}</td>
                    <td style="padding: 8px;">{s.get('duration_minutes')} mins</td>
                    <td style="padding: 8px;">{s.get('resource_type')}</td>
                    <td style="padding: 8px;">{link_elem}</td>
                </tr>
        """
    plan_html += """
            </tbody>
        </table>
    </div>
    """

    return profile_html, rec_html, plan_html


# Gradio UI Construction
with gr.Blocks(title="Personalised Learning Resource Recommendation Agent") as demo:
    gr.Markdown(
        """
        # 🎓 Personalised Learning Resource Recommendation Agent
        ### Multi-Agent AI System with Tavily Search, Multi-Criteria Scoring & Groq Reasoning
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🎯 Learner Requirements")
            subject_input = gr.Textbox(
                label="Subject",
                placeholder="e.g. Computer Networks, Operating Systems, DBMS, Python",
                value="Computer Networks"
            )
            topic_input = gr.Textbox(
                label="Topic",
                placeholder="e.g. IPv4 and Subnetting, CPU Scheduling, Binary Trees",
                value="IPv4 and Subnetting"
            )
            level_input = gr.Dropdown(
                label="Current Knowledge Level",
                choices=["Beginner", "Intermediate", "Advanced"],
                value="Beginner"
            )
            goal_input = gr.Dropdown(
                label="Primary Learning Goal",
                choices=["Exam Preparation", "Concept Understanding", "Practice"],
                value="Exam Preparation"
            )
            formats_input = gr.CheckboxGroup(
                label="Preferred Resource Formats",
                choices=["Video", "Notes", "Articles", "Practice"],
                value=["Video", "Notes"]
            )
            time_input = gr.Slider(
                label="Available Study Time (Hours)",
                minimum=0.25,
                maximum=8.0,
                step=0.25,
                value=2.0
            )

            with gr.Accordion("⚙️ Optional API Settings / Feedback", open=False):
                gr.Markdown("*(Leave blank to use environment variables or intelligent offline fallback)*")
                tavily_key_input = gr.Textbox(
                    label="Tavily API Key (Optional)",
                    type="password",
                    placeholder="tvly-..."
                )
                groq_key_input = gr.Textbox(
                    label="Groq API Key (Optional)",
                    type="password",
                    placeholder="gsk_..."
                )
                feedback_input = gr.Radio(
                    label="Difficulty Feedback Calibration",
                    choices=["Appropriate", "Too Easy", "Too Difficult"],
                    value="Appropriate"
                )

            submit_btn = gr.Button("✨ Generate Personalised Learning Plan", variant="primary")

        with gr.Column(scale=2):
            profile_output = gr.HTML(label="Learner Profile")
            rec_output = gr.HTML(label="Recommendations")
            plan_output = gr.HTML(label="Study Plan")

    # Connect button click
    submit_btn.click(
        fn=generate_learning_recommendations,
        inputs=[
            subject_input,
            topic_input,
            level_input,
            goal_input,
            formats_input,
            time_input,
            tavily_key_input,
            groq_key_input,
            feedback_input
        ],
        outputs=[profile_output, rec_output, plan_output]
    )

    with gr.Accordion("ℹ️ How the Agent Works (4-Agent System Architecture)", open=False):
        gr.Markdown(
            """
            1. **Agent 1: Learner Profile Agent (`learner_profile.py`)**: Ingests requirements, normalizes durations, and formulates search query representations.
            2. **Agent 2: Resource Retrieval Agent (`resource_retrieval.py`)**: Searches live web resources using Tavily API with safe local CSV fallback.
            3. **Agent 3: Recommendation Agent (`recommendation.py` & `scoring.py`)**: Ranks candidate resources using a 5-factor transparent formula (Topic 35%, Level 20%, Goal 20%, Format 15%, Time 10%) + Groq LLaMA-3.3 reasoning.
            4. **Agent 4: Learning Plan Agent (`learning_plan.py`)**: Constructs a pedagogical, time-bounded schedule strictly within the available hours.
            """
        )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 10000))
    )
