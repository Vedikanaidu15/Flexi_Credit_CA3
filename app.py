import streamlit as st
import os
from typing import List
from agents.learner_profile import LearnerProfileAgent, LearnerProfile
from agents.resource_retrieval import ResourceRetrievalAgent
from agents.recommendation import RecommendationAgent
from agents.learning_plan import LearningPlanAgent
from utils.api_client import get_tavily_api_key, get_groq_api_key

# Page Configuration
st.set_page_config(
    page_title="AI Learning Recommendation Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    
    .hero-container {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 2.2rem 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.4rem;
        background: linear-gradient(90deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        font-weight: 400;
        margin-bottom: 0;
    }
    .resource-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.3rem;
        margin-bottom: 1.2rem;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .resource-card:hover {
        border-color: #cbd5e1;
        box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .badge-type { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .badge-level { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
    .badge-time { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
    .badge-source { background: #f8fafc; color: #475569; border: 1px solid #e2e8f0; }
    
    .score-badge {
        float: right;
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white;
        padding: 6px 14px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.95rem;
    }
    .step-card {
        border-left: 4px solid #4f46e5;
        background: #f8fafc;
        padding: 1rem 1.2rem;
        border-radius: 0 12px 12px 0;
        margin-bottom: 0.8rem;
    }
    .workflow-box {
        background: #f1f5f9;
        border-radius: 12px;
        padding: 1rem;
        margin-top: 1rem;
        border: 1px dashed #cbd5e1;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "learner_profile" not in st.session_state:
    st.session_state.learner_profile = None
if "recommended_resources" not in st.session_state:
    st.session_state.recommended_resources = None
if "study_plan" not in st.session_state:
    st.session_state.study_plan = None
if "feedback_history" not in st.session_state:
    st.session_state.feedback_history = {"difficulty": "Appropriate", "not_useful_urls": [], "useful_urls": []}
if "demo_loaded" not in st.session_state:
    st.session_state.demo_loaded = False

# Sidebar: Configurations & API Keys
with st.sidebar:
    st.markdown("### ⚙️ System & API Settings")
    st.caption("Enter API keys for live web search and LLM reasoning, or use built-in offline intelligence.")
    
    env_tavily = get_tavily_api_key()
    env_groq = get_groq_api_key()
    
    custom_tavily = st.text_input("Tavily API Key", type="password", value=env_tavily or "", placeholder="tvly-...")
    custom_groq = st.text_input("Groq API Key", type="password", value=env_groq or "", placeholder="gsk_...")
    
    effective_tavily = custom_tavily.strip() if custom_tavily.strip() else None
    effective_groq = custom_groq.strip() if custom_groq.strip() else None
    
    # Status badges
    tavily_status = "🟢 Active" if effective_tavily else "⚪ Fallback Dataset"
    groq_status = "🟢 Active (LLaMA-3.3)" if effective_groq else "⚪ Fallback Reasoning Engine"
    
    st.markdown(f"**Tavily Search:** {tavily_status}")
    st.markdown(f"**Groq Reasoning:** {groq_status}")
    
    st.divider()
    st.markdown("### 🎓 Demo Scenarios")
    if st.button("🚀 Load College Demo Scenario", help="Loads 'Computer Networks -> IPv4 and Subnetting' with 2 hours study time"):
        st.session_state.demo_subject = "Computer Networks"
        st.session_state.demo_topic = "IPv4 and Subnetting"
        st.session_state.demo_level = "Beginner"
        st.session_state.demo_goal = "Exam Preparation"
        st.session_state.demo_formats = ["Video", "Notes"]
        st.session_state.demo_time = 2.0
        st.session_state.demo_loaded = True
        st.rerun()

    if st.button("🔄 Reset Agent State"):
        st.session_state.learner_profile = None
        st.session_state.recommended_resources = None
        st.session_state.study_plan = None
        st.session_state.feedback_history = {"difficulty": "Appropriate", "not_useful_urls": [], "useful_urls": []}
        st.session_state.demo_loaded = False
        st.rerun()

# Hero Header
st.markdown("""
<div class="hero-container">
    <div class="hero-title">Personalised Learning Resource Recommendation Agent</div>
    <div class="hero-subtitle">Multi-Agent AI learning assistant powered by Tavily Search, Multi-Criteria Scoring & Groq Reasoning</div>
</div>
""", unsafe_allow_html=True)

# Main Input Section
with st.container():
    st.markdown("### 🎯 Enter Your Learning Requirements")
    
    col1, col2 = st.columns(2)
    
    with col1:
        default_subj = "Computer Networks" if st.session_state.get("demo_loaded") else ""
        subject = st.text_input("Subject", value=default_subj, placeholder="e.g. Computer Networks, Operating Systems, DBMS, Python")
        
        default_topic = "IPv4 and Subnetting" if st.session_state.get("demo_loaded") else ""
        topic = st.text_input("Topic", value=default_topic, placeholder="e.g. IPv4 and Subnetting, CPU Scheduling, Binary Trees")
        
        level_opts = ["Beginner", "Intermediate", "Advanced"]
        default_lvl_idx = level_opts.index(st.session_state.get("demo_level", "Beginner")) if st.session_state.get("demo_loaded") else 0
        level = st.selectbox("Current Knowledge Level", level_opts, index=default_lvl_idx)

    with col2:
        goal_opts = ["Exam Preparation", "Concept Understanding", "Practice"]
        default_goal_idx = goal_opts.index(st.session_state.get("demo_goal", "Exam Preparation")) if st.session_state.get("demo_loaded") else 0
        goal = st.selectbox("Primary Learning Goal", goal_opts, index=default_goal_idx)
        
        format_opts = ["Video", "Notes", "Articles", "Practice"]
        default_formats = st.session_state.get("demo_formats", ["Video", "Notes"]) if st.session_state.get("demo_loaded") else ["Video", "Notes"]
        preferred_formats = st.multiselect("Preferred Resource Formats", format_opts, default=default_formats)
        
        default_time = st.session_state.get("demo_time", 2.0) if st.session_state.get("demo_loaded") else 2.0
        available_time = st.number_input("Available Study Time (Hours)", min_value=0.25, max_value=8.0, value=float(default_time), step=0.25)

    generate_btn = st.button("✨ Generate Personalised Learning Plan", type="primary", use_container_width=True)

# Workflow Execution
if generate_btn:
    if not subject.strip() or not topic.strip():
        st.warning("⚠️ Please provide both Subject and Topic to start.")
    else:
        with st.spinner("🤖 Agentic Pipeline in progress: Synthesizing profile, retrieving resources, scoring & reasoning..."):
            # Step 1: Learner Profile Agent
            profile = LearnerProfileAgent.build_profile(
                subject=subject,
                topic=topic,
                level=level,
                goal=goal,
                preferred_formats=preferred_formats,
                available_time_val=available_time,
                time_unit="Hours",
                difficulty_feedback=st.session_state.feedback_history["difficulty"],
                not_useful_urls=st.session_state.feedback_history["not_useful_urls"],
                useful_urls=st.session_state.feedback_history["useful_urls"]
            )
            st.session_state.learner_profile = profile

            # Step 2: Resource Retrieval Agent
            retrieval_agent = ResourceRetrievalAgent()
            raw_resources = retrieval_agent.retrieve_resources(profile, tavily_api_key=effective_tavily)

            # Step 3: Recommendation Agent (Scoring + Groq Reasoning)
            rec_agent = RecommendationAgent(top_k=5)
            recommended = rec_agent.recommend(raw_resources, profile, groq_api_key=effective_groq)
            st.session_state.recommended_resources = recommended

            # Step 4: Learning Plan Agent
            plan_agent = LearningPlanAgent()
            plan = plan_agent.build_study_plan(recommended, profile, groq_api_key=effective_groq)
            st.session_state.study_plan = plan

        st.success("✅ Personalised learning recommendations and study schedule generated successfully!")

# Results Display
if st.session_state.learner_profile and st.session_state.recommended_resources:
    profile: LearnerProfile = st.session_state.learner_profile
    resources = st.session_state.recommended_resources
    plan = st.session_state.study_plan

    st.markdown("---")
    
    # 1. Learner Profile Summary Card
    st.markdown("### 👤 Synthesized Learner Profile")
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)
    with p_col1:
        st.metric("Subject & Topic", f"{profile.subject}", profile.topic)
    with p_col2:
        st.metric("Target Level", profile.target_level, f"Base: {profile.current_level}")
    with p_col3:
        st.metric("Learning Goal", profile.learning_goal)
    with p_col4:
        st.metric("Time Budget", f"{profile.available_time_minutes} Mins", f"{profile.available_time_minutes / 60:.1f} Hours")

    # 2. Top Recommended Resources
    st.markdown("### 📚 Top Recommended Resources")
    st.caption("Ranked using transparent 5-factor scoring engine (Topic 35%, Level 20%, Goal 20%, Format 15%, Time 10%) + Groq AI Reasoning.")
    
    for idx, r in enumerate(resources):
        with st.container():
            score_val = r.get('score', 0)
            st.markdown(f"""
            <div class="resource-card">
                <div class="score-badge">Match Score: {score_val}%</div>
                <h4 style="margin-top:0; margin-bottom: 8px; color: #1e293b;">{idx+1}. {r.get('title')}</h4>
                <div>
                    <span class="badge badge-source">🌐 {r.get('source')}</span>
                    <span class="badge badge-type">📖 {r.get('resource_type')}</span>
                    <span class="badge badge-level">📊 {r.get('difficulty_level')}</span>
                    <span class="badge badge-time">⏱️ {r.get('duration_minutes')} mins</span>
                </div>
                <p style="margin-top: 10px; margin-bottom: 6px; font-size: 0.92rem; color: #334155;">{r.get('description')}</p>
                <div style="background: #f8fafc; border-left: 3px solid #6366f1; padding: 8px 12px; border-radius: 4px; margin-top: 8px; font-size: 0.88rem; color: #4338ca;">
                    <strong>💡 Why Recommended:</strong> {r.get('why_recommended')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            c_link, c_feed1, c_feed2 = st.columns([2, 1, 1])
            with c_link:
                if r.get("url"):
                    st.link_button(f"🔗 Open {r.get('source')} Resource", r.get("url"))
            with c_feed1:
                if st.button(f"👍 Useful", key=f"useful_{idx}_{r.get('id')}"):
                    if r.get("url") not in st.session_state.feedback_history["useful_urls"]:
                        st.session_state.feedback_history["useful_urls"].append(r.get("url"))
                    st.toast("Feedback recorded: Resource marked useful!")
            with c_feed2:
                if st.button(f"👎 Not Useful", key=f"not_useful_{idx}_{r.get('id')}"):
                    if r.get("url") not in st.session_state.feedback_history["not_useful_urls"]:
                        st.session_state.feedback_history["not_useful_urls"].append(r.get("url"))
                    st.toast("Feedback recorded: Resource marked not useful!")
            
            with st.expander(f"🔍 View Scoring Breakdown for Item #{idx+1}"):
                b = r.get("scoring_breakdown", {})
                sc1, sc2, sc3, sc4, sc5 = st.columns(5)
                sc1.metric("Topic (35%)", f"{b.get('topic_score')}%")
                sc2.metric("Level (20%)", f"{b.get('level_score')}%")
                sc3.metric("Goal (20%)", f"{b.get('goal_score')}%")
                sc4.metric("Format (15%)", f"{b.get('format_score')}%")
                sc5.metric("Time (10%)", f"{b.get('time_score')}%")

    # 3. Personalised Study Plan
    if plan:
        st.markdown("---")
        st.markdown("### ⏱️ Personalised Time-Limited Study Schedule")
        
        total_sched = plan.get("total_scheduled_minutes", 0)
        avail = plan.get("available_minutes", 0)
        
        st.info(f"📅 **Total Allocated Study Time:** {total_sched} mins / {avail} mins available • **Time Budget Compliance:** {'✅ Perfect' if plan.get('is_within_budget') else '⚠️ Exceeded'}")
        
        if plan.get("strategy_tip"):
            st.markdown(f"""
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 12px 16px; margin-bottom: 1.2rem; color: #166534; font-size: 0.95rem;">
                <strong>🎯 AI Study Strategy:</strong> {plan.get('strategy_tip')}
            </div>
            """, unsafe_allow_html=True)
            
        for step in plan.get("steps", []):
            st.markdown(f"""
            <div class="step-card">
                <strong>Step {step.get('step_number')}: {step.get('phase')}</strong> — <span style="color:#475569;">{step.get('title')}</span> ({step.get('duration_minutes')} mins)
                <div style="font-size: 0.88rem; color: #334155; margin-top: 4px;">📌 <em>{step.get('action_item')}</em></div>
            </div>
            """, unsafe_allow_html=True)

    # 4. Feedback & Continuous Improvement Loop
    st.markdown("---")
    st.markdown("### 💬 Adaptive Feedback Loop")
    st.caption("Tell the agent how this recommendation fits you. The next generation will automatically calibrate difficulty & ranking.")
    
    fb_col1, fb_col2 = st.columns([2, 1])
    with fb_col1:
        diff_feedback = st.radio(
            "How was the difficulty level of these recommendations?",
            ["Appropriate", "Too Easy", "Too Difficult"],
            index=["Appropriate", "Too Easy", "Too Difficult"].index(st.session_state.feedback_history["difficulty"]),
            horizontal=True
        )
    with fb_col2:
        st.write("")
        st.write("")
        if st.button("🔄 Apply Feedback & Re-rank", type="secondary", use_container_width=True):
            st.session_state.feedback_history["difficulty"] = diff_feedback
            # Trigger immediate re-run with updated feedback profile
            profile = LearnerProfileAgent.build_profile(
                subject=profile.subject,
                topic=profile.topic,
                level=profile.current_level,
                goal=profile.learning_goal,
                preferred_formats=profile.preferred_resources,
                available_time_val=profile.available_time_minutes,
                time_unit="Minutes",
                difficulty_feedback=diff_feedback,
                not_useful_urls=st.session_state.feedback_history["not_useful_urls"],
                useful_urls=st.session_state.feedback_history["useful_urls"]
            )
            st.session_state.learner_profile = profile
            
            # Re-retrieve & re-rank
            retrieval_agent = ResourceRetrievalAgent()
            raw_resources = retrieval_agent.retrieve_resources(profile, tavily_api_key=effective_tavily)
            rec_agent = RecommendationAgent(top_k=5)
            recommended = rec_agent.recommend(raw_resources, profile, groq_api_key=effective_groq)
            st.session_state.recommended_resources = recommended
            
            plan_agent = LearningPlanAgent()
            plan = plan_agent.build_study_plan(recommended, profile, groq_api_key=effective_groq)
            st.session_state.study_plan = plan
            
            st.toast("Profile adapted with feedback! Recommendations recalibrated.")
            st.rerun()

# 5. How the Agent Works (Collapsible explanation for viva presentation)
st.markdown("---")
with st.expander("ℹ️ How the Agent Works (Multi-Agent System Architecture)"):
    st.markdown("""
    #### 🤖 4-Agent Architecture Explained
    
    1. **Agent 1: Learner Profile Agent (`learner_profile.py`)**
       - Converts raw user inputs (Subject, Topic, Level, Goal, Preferred format, Available study time) and past feedback into a structured profile object.
       - Formulates optimized search queries for web discovery.
       
    2. **Agent 2: Resource Retrieval Agent (`resource_retrieval.py`)**
       - Queries Tavily API for educational resources (YouTube, GeeksforGeeks, Sanfoundry, Wikipedia, etc.).
       - Normalizes resource types, estimated study durations, and difficulty levels.
       - Features an offline curated CSV fallback repository (`learning_resources.csv`) ensuring 100% fault-tolerance.
       
    3. **Agent 3: Recommendation Agent (`recommendation.py` & `scoring.py`)**
       - Evaluates candidate resources against a transparent multi-criteria formula:
         $$\\text{Score} = 0.35\\times\\text{Topic} + 0.20\\times\\text{Level} + 0.20\\times\\text{Goal} + 0.15\\times\\text{Format} + 0.10\\times\\text{Time}$$
       - Uses Groq (LLaMA-3.3) to generate personalized "Why recommended" reasoning for each top resource.
       
    4. **Agent 4: Learning Plan Agent (`learning_plan.py`)**
       - Synthesizes the top resources into a sequential, pedagogically sound schedule (Foundation $\\rightarrow$ Theory $\\rightarrow$ Practice $\\rightarrow$ Review).
       - Enforces strict study time budget: $\\sum \\text{Duration} \\le \\text{Available Time}$.
       
    5. **Feedback Loop:**
       - Direct feedback ("Too Difficult", "Too Easy", "Not Useful") dynamically updates the learner profile and penalizes/boosts future recommendations in real-time.
    """)
