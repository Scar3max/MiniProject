import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import streamlit as st
import streamlit.components.v1 as components
import time
import json
from interview import InterviewOrchestrator

# Page configuration
st.set_page_config(
    page_title="Adaptive Performance-Based Interview Bot",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern, interactive UI
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #6366f1;
        --secondary-color: #8b5cf6;
        --background-color: #0f172a;
        --card-background: #1e293b;
        --text-color: #e2e8f0;
        --border-color: #334155;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        animation: fadeIn 0.8s ease-in;
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        margin-top: 0.5rem;
    }
    
    /* Chat message styling - Glassmorphism */
    .chat-container {
        display: flex;
        margin-bottom: 1.5rem;
        animation: slideIn 0.5s ease-out;
    }
    
    .chat-container.bot {
        justify-content: flex-start;
    }
    
    .chat-container.user {
        justify-content: flex-end;
    }
    
    .chat-message {
        max-width: 70%;
        padding: 1.2rem 1.8rem;
        border-radius: 20px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .chat-message.bot {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-bottom-left-radius: 4px;
    }
    
    .chat-message.user {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border-bottom-right-radius: 4px;
    }
    
    .chat-message .role {
        font-weight: 600;
        font-size: 0.7rem;
        margin-bottom: 0.5rem;
        opacity: 0.8;
        letter-spacing: 0.5px;
    }
    
    .chat-message .content {
        font-size: 1rem;
        line-height: 1.6;
    }
    
    /* Typing indicator */
    .typing-indicator {
        display: flex;
        align-items: center;
        padding: 1rem;
        background: rgba(102, 126, 234, 0.1);
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .typing-indicator span {
        height: 10px;
        width: 10px;
        background: #667eea;
        border-radius: 50%;
        display: inline-block;
        margin: 0 3px;
        animation: bounce 1.4s infinite ease-in-out both;
    }
    
    .typing-indicator span:nth-child(1) {
        animation-delay: -0.32s;
    }
    
    .typing-indicator span:nth-child(2) {
        animation-delay: -0.16s;
    }
    
    @keyframes bounce {
        0%, 80%, 100% { 
            transform: scale(0);
        } 40% { 
            transform: scale(1.0);
        }
    }
    
    /* Analysis dropdown styling */
    .analysis-container {
        background: rgba(102, 126, 234, 0.05);
        border: 2px solid rgba(102, 126, 234, 0.3);
        border-radius: 10px;
        padding: 1rem;
        margin-top: 0.5rem;
    }
    
    .analysis-label {
        color: #667eea;
        font-weight: 600;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    
    .analysis-content {
        color: #94a3b8;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Input styling */
    .stTextInput>div>div>input {
        border-radius: 10px;
        border: 2px solid rgba(102, 126, 234, 0.3);
        padding: 0.75rem;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    }
    
    /* Stats card */
    .stats-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
        border: 2px solid rgba(102, 126, 234, 0.3);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        text-align: center;
    }
    
    .stats-card h3 {
        color: #667eea;
        font-size: 2rem;
        margin: 0;
        font-weight: 700;
    }
    
    .stats-card p {
        color: #94a3b8;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    
    /* Animations */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* Progress bar */
    .progress-container {
        background: rgba(102, 126, 234, 0.1);
        border-radius: 10px;
        height: 8px;
        margin: 1rem 0;
        overflow: hidden;
    }
    
    .progress-bar {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    
    /* Real-time feedback badge */
    .badge-container {
        display: flex;
        margin-top: 0.75rem;
    }
    
    .feedback-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        animation: slideInBounce 0.6s ease-out;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border: 2px solid rgba(255,255,255,0.3);
        width: fit-content;
    }
    
    .feedback-badge.normal {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
    }
    
    .feedback-badge.vague {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
    }
    
    .feedback-badge.incorrect {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
    }
    
    .feedback-badge.hesitation {
        background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
        color: white;
    }
    
    .feedback-badge.knowledge-gap {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
    }
    
    .feedback-badge.evasive {
        background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
        color: white;
    }
    
    @keyframes slideInBounce {
        0% {
            opacity: 0;
            transform: translateY(-20px) scale(0.8);
        }
        60% {
            opacity: 1;
            transform: translateY(5px) scale(1.05);
        }
        100% {
            transform: translateY(0) scale(1);
        }
    }
    
    /* Analytics specific styles */
    .metric-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%);
        border: 2px solid rgba(102, 126, 234, 0.4);
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem 0;
        text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
    }
    
    .metric-card h2 {
        color: #667eea;
        font-size: 3rem;
        margin: 0;
        font-weight: 800;
    }
    
    .metric-card p {
        color: #94a3b8;
        font-size: 1rem;
        margin-top: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Feedback section */
    .feedback-section {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%);
        border-left: 5px solid #10b981;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .feedback-section h4 {
        color: #10b981;
        margin-top: 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.chatbot = None
    st.session_state.messages = []
    st.session_state.interview_started = False
    st.session_state.interview_ended = False
    st.session_state.domain = ""
    st.session_state.question_count = 0
    st.session_state.show_analysis = {}
    st.session_state.theme_color = "#667eea"
    st.session_state.page = "interview"  # interview or analytics
    st.session_state.interview_history = []  # Store completed interviews
    st.session_state.performance_data = []  # Track answer quality over time

def typewriter_effect(text, speed=0.03):
    """Display text with typewriter effect"""
    placeholder = st.empty()
    displayed_text = ""
    for char in text:
        displayed_text += char
        placeholder.markdown(f'<div class="chat-message bot"><div class="role">🤖 Interviewer</div><div class="content">{displayed_text}▌</div></div>', unsafe_allow_html=True)
        time.sleep(speed)
    placeholder.markdown(f'<div class="chat-message bot"><div class="role">🤖 Interviewer</div><div class="content">{displayed_text}</div></div>', unsafe_allow_html=True)
    return placeholder

def get_feedback_badge(answer_type):
    """Generate a feedback badge based on answer type"""
    badge_map = {
        "Normal": ("✅ Good Answer", "normal"),
        "NORMAL": ("✅ Good Answer", "normal"),
        "Vague": ("⚠️ Vague", "vague"),
        "VAGUE": ("⚠️ Vague", "vague"),
        "Factually_Incorrect": ("❌ Incorrect", "incorrect"),
        "FACTUALLY_INCORRECT": ("❌ Incorrect", "incorrect"),
        "HESITATION_SIGNAL": ("🤔 Hesitation", "hesitation"),
        "KNOWLEDGE_GAP": ("💭 Knowledge Gap", "knowledge-gap"),
        "EVASIVE_NON_ANSWER": ("🔄 Evasive", "evasive"),
        "EVASIVE_CHALLENGE": ("⚠️ Violation", "evasive"),
    }
    
    label, css_class = badge_map.get(answer_type, ("📝 Analyzed", "normal"))
    return f'<div class="badge-container"><div class="feedback-badge {css_class}">{label}</div></div>'

def display_message(role, content, analysis=None, msg_id=None):
    """Display a chat message with optional analysis - WhatsApp style"""
    if role == "bot":
        st.markdown(f'''
            <div class="chat-container bot">
                <div class="chat-message bot">
                    <div class="role">🤖 INTERVIEWER</div>
                    <div class="content">{content}</div>
                </div>
            </div>
        ''', unsafe_allow_html=True)
    else:
        # User message with badge
        badge_html = ""
        if analysis and 'answer_type' in analysis:
            badge_html = get_feedback_badge(analysis['answer_type'])
        
        st.markdown(f'''
            <div class="chat-container user">
                <div class="chat-message user">
                    <div class="role">👤 YOU</div>
                    <div class="content">{content}</div>
                    {badge_html}
                </div>
            </div>
        ''', unsafe_allow_html=True)

def show_typing_indicator():
    """Show typing indicator animation"""
    return st.markdown("""
        <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
        </div>
    """, unsafe_allow_html=True)

def calculate_interview_stats():
    """Calculate statistics from current interview"""
    if not st.session_state.messages:
        return None
    
    stats = {
        "total_questions": 0,
        "total_answers": 0,
        "answer_types": {
            "Normal": 0,
            "Vague": 0,
            "Incorrect": 0,
            "Hesitation": 0,
            "Knowledge_Gap": 0,
            "Evasive": 0,
            "Violation": 0
        },
        "scores": [],
        "topics_covered": set()
    }
    
    for msg in st.session_state.messages:
        if msg["role"] == "bot":
            stats["total_questions"] += 1
        elif msg["role"] == "user" and msg.get("analysis"):
            stats["total_answers"] += 1
            analysis = msg["analysis"]
            
            # Count answer types
            answer_type = analysis.get("answer_type", "Normal")
            if answer_type in ["NORMAL", "Normal"]:
                stats["answer_types"]["Normal"] += 1
            elif answer_type in ["VAGUE", "Vague"]:
                stats["answer_types"]["Vague"] += 1
            elif answer_type in ["FACTUALLY_INCORRECT", "Factually_Incorrect"]:
                stats["answer_types"]["Incorrect"] += 1
            elif answer_type == "HESITATION_SIGNAL":
                stats["answer_types"]["Hesitation"] += 1
            elif answer_type == "KNOWLEDGE_GAP":
                stats["answer_types"]["Knowledge_Gap"] += 1
            elif answer_type == "EVASIVE_NON_ANSWER":
                stats["answer_types"]["Evasive"] += 1
            elif answer_type == "EVASIVE_CHALLENGE":
                stats["answer_types"]["Violation"] += 1
            
            # Collect scores
            if "answer_quality_score" in analysis:
                stats["scores"].append(analysis["answer_quality_score"])
    
    # Add current topic
    if st.session_state.chatbot:
        stats["topics_covered"].add(st.session_state.chatbot.current_topic)
        if hasattr(st.session_state.chatbot, 'topic_syllabus'):
            for topic in st.session_state.chatbot.topic_syllabus:
                stats["topics_covered"].add(topic)
    
    return stats

def generate_ai_feedback():
    """Generate overall AI feedback based on performance"""
    stats = calculate_interview_stats()
    if not stats or stats["total_answers"] == 0:
        return "Not enough data to generate feedback."
    
    feedback = []
    
    # Overall performance
    avg_score = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
    if avg_score >= 7.0:
        feedback.append("🌟 **Excellent Performance**: You demonstrated strong knowledge and clear communication throughout the interview.")
    elif avg_score >= 5.0:
        feedback.append("👍 **Good Effort**: You showed decent understanding, but there's room for improvement in depth and clarity.")
    elif avg_score >= 3.0:
        feedback.append("📚 **Needs Improvement**: Consider reviewing the fundamentals and practicing more detailed explanations.")
    else:
        feedback.append("💪 **Keep Learning**: Focus on building stronger foundational knowledge in this domain.")
    
    # Answer quality breakdown
    normal_pct = (stats["answer_types"]["Normal"] / stats["total_answers"]) * 100
    vague_pct = (stats["answer_types"]["Vague"] / stats["total_answers"]) * 100
    incorrect_pct = (stats["answer_types"]["Incorrect"] / stats["total_answers"]) * 100
    
    if normal_pct >= 60:
        feedback.append(f"✅ **Strong Answers**: {normal_pct:.0f}% of your responses were clear and accurate.")
    
    if vague_pct > 30:
        feedback.append(f"⚠️ **Be More Specific**: {vague_pct:.0f}% of answers lacked detail. Try providing concrete examples and explanations.")
    
    if incorrect_pct > 20:
        feedback.append(f"❌ **Accuracy Concerns**: {incorrect_pct:.0f}% of answers contained factual errors. Review core concepts carefully.")
    
    # Behavioral feedback
    if stats["answer_types"]["Hesitation"] > 3:
        feedback.append("🤔 **Confidence**: Multiple hesitations detected. Practice articulating your thoughts more confidently.")
    
    if stats["answer_types"]["Knowledge_Gap"] > 2:
        feedback.append("💭 **Knowledge Gaps**: Several topics where you admitted not knowing. Identify and study these areas.")
    
    if stats["answer_types"]["Violation"] > 0:
        feedback.append("⚠️ **Professional Conduct**: Maintain professional demeanor even when questions are challenging.")
    
    return "\n\n".join(feedback)

def show_analytics_page():
    """Display comprehensive analytics page"""
    st.markdown("""
        <div class="main-header">
            <h1>📊 Interview Analytics</h1>
            <p>Detailed performance insights and feedback</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back to Interview", use_container_width=True):
            st.session_state.page = "interview"
            st.rerun()
    
    stats = calculate_interview_stats()
    
    if not stats or stats["total_answers"] == 0:
        st.warning("⚠️ No interview data available yet. Complete an interview to see analytics.")
        return
    
    # Key metrics row
    st.markdown("### 📈 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="stats-card">
                <h3>{stats['total_questions']}</h3>
                <p>Questions Asked</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="stats-card">
                <h3>{stats['total_answers']}</h3>
                <p>Answers Given</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        avg_score = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
        st.markdown(f"""
            <div class="stats-card">
                <h3>{avg_score:.1f}/10</h3>
                <p>Avg Score</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="stats-card">
                <h3>{len(stats['topics_covered'])}</h3>
                <p>Topics Covered</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Performance over time
    st.markdown("### 📉 Performance Trend")
    if stats["scores"]:
        import plotly.graph_objects as go
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(1, len(stats["scores"]) + 1)),
            y=stats["scores"],
            mode='lines+markers',
            name='Score',
            line=dict(color='#667eea', width=3),
            marker=dict(size=10, color='#764ba2'),
            fill='tozeroy',
            fillcolor='rgba(102, 126, 234, 0.2)'
        ))
        
        # Add average line
        fig.add_hline(y=avg_score, line_dash="dash", line_color="orange", 
                      annotation_text=f"Average: {avg_score:.1f}")
        
        fig.update_layout(
            title="Answer Quality Over Time",
            xaxis_title="Question Number",
            yaxis_title="Quality Score (0-10)",
            template="plotly_dark",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No score data available yet.")
    
    st.markdown("---")
    
    # Answer type distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 Answer Quality Distribution")
        import plotly.graph_objects as go
        
        # Filter out zero values
        labels = []
        values = []
        colors = []
        color_map = {
            "Normal": "#10b981",
            "Vague": "#f59e0b",
            "Incorrect": "#ef4444",
            "Hesitation": "#8b5cf6",
            "Knowledge_Gap": "#6366f1",
            "Evasive": "#ec4899",
            "Violation": "#dc2626"
        }
        
        for answer_type, count in stats["answer_types"].items():
            if count > 0:
                labels.append(answer_type.replace("_", " "))
                values.append(count)
                colors.append(color_map.get(answer_type, "#667eea"))
        
        if values:
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=colors),
                hole=0.4,
                textinfo='label+percent',
                textfont_size=14
            )])
            
            fig.update_layout(
                template="plotly_dark",
                height=400,
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No answer type data available.")
    
    with col2:
        st.markdown("### 🎓 Topics Covered")
        if stats["topics_covered"]:
            for idx, topic in enumerate(stats["topics_covered"], 1):
                st.markdown(f"""
                    <div class="stats-card">
                        <h3>{idx}</h3>
                        <p>{topic}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No topics data available.")
    
    st.markdown("---")
    
    # AI Feedback
    st.markdown("### 🤖 AI Interviewer Feedback")
    feedback = generate_ai_feedback()
    st.markdown(f"""
        <div class="analysis-container">
            {feedback}
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Conversation history
    st.markdown("### 💬 Full Conversation History")
    with st.expander("📜 View Complete Conversation", expanded=False):
        for idx, msg in enumerate(st.session_state.messages):
            if msg["role"] == "bot":
                st.markdown(f"**🤖 Interviewer:** {msg['content']}")
            else:
                st.markdown(f"**👤 You:** {msg['content']}")
                if msg.get("analysis"):
                    analysis = msg["analysis"]
                    st.markdown(f"*Analysis: {analysis.get('answer_type', 'N/A')} - {analysis.get('analysis_notes', 'N/A')}*")
            st.markdown("---")

# Check which page to show
if st.session_state.page == "analytics":
    show_analytics_page()
    st.stop()

# Main header
st.markdown("""
    <div class="main-header">
        <h1>Adaptive Performance-Based Interview Bot</h1>
        <p>Your AI-powered technical interview companion</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # Logo/Branding
    st.markdown("""
        <div style="text-align: center; padding: 1rem 0 2rem 0;">
            <div style="font-size: 4rem; margin-bottom: 0.5rem;">🎯</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: #667eea;">Interview Assistant</div>
            <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.3rem;">AI-Powered Practice</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Quick Tips with graphics
    st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%); 
                    border-left: 4px solid #667eea; 
                    border-radius: 8px; 
                    padding: 1rem; 
                    margin: 1rem 0;">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">💡</div>
            <div style="font-weight: 600; color: #667eea; margin-bottom: 0.5rem;">Quick Tips</div>
            <div style="font-size: 0.85rem; color: #94a3b8; line-height: 1.6;">
                • Be specific and detailed<br>
                • Use examples when possible<br>
                • Think before answering<br>
                • Type 'quit' to end anytime
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Feature highlights
    st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%); 
                    border-left: 4px solid #10b981; 
                    border-radius: 8px; 
                    padding: 1rem; 
                    margin: 1rem 0;">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">✨</div>
            <div style="font-weight: 600; color: #10b981; margin-bottom: 0.5rem;">Features</div>
            <div style="font-size: 0.85rem; color: #94a3b8; line-height: 1.6;">
                • Real-time feedback badges<br>
                • Adaptive difficulty<br>
                • Performance analytics<br>
                • AI-powered insights
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Analytics button
    if st.session_state.interview_ended or st.session_state.messages:
        st.markdown("---")
        if st.button("📊 View Analytics", use_container_width=True):
            st.session_state.page = "analytics"
            st.rerun()
    
    # Stats with icons
    if st.session_state.interview_started:
        st.markdown("---")
        st.markdown(f"""
            <div class="stats-card">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">💬</div>
                <h3>{st.session_state.question_count}</h3>
                <p>Questions Asked</p>
            </div>
        """, unsafe_allow_html=True)
    
    # Interview history
    if st.session_state.interview_history:
        st.markdown(f"""
            <div class="stats-card">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">📚</div>
                <h3>{len(st.session_state.interview_history)}</h3>
                <p>Interviews Completed</p>
            </div>
        """, unsafe_allow_html=True)
    
    # Answer Analysis Panel
    if st.session_state.interview_started and st.session_state.messages:
        st.markdown("---")
        st.markdown("### 📋 Answer Analysis")
        
        # Get user messages with analysis
        user_messages = [(idx, msg) for idx, msg in enumerate(st.session_state.messages) if msg["role"] == "user" and msg.get("analysis")]
        
        if user_messages:
            # Show last 3 analyses
            for idx, msg in reversed(user_messages[-3:]):
                analysis = msg.get("analysis", {})
                answer_type = analysis.get("answer_type", "Unknown")
                analysis_notes = analysis.get("analysis_notes", "No analysis available")
                
                # Color based on answer type
                if answer_type in ["NORMAL", "Normal"]:
                    color = "#10b981"
                    icon = "✅"
                elif answer_type in ["VAGUE", "Vague"]:
                    color = "#f59e0b"
                    icon = "⚠️"
                elif answer_type in ["FACTUALLY_INCORRECT", "Factually_Incorrect"]:
                    color = "#ef4444"
                    icon = "❌"
                elif answer_type == "HESITATION_SIGNAL":
                    color = "#8b5cf6"
                    icon = "🤔"
                elif answer_type == "KNOWLEDGE_GAP":
                    color = "#6366f1"
                    icon = "💭"
                elif answer_type == "EVASIVE_NON_ANSWER":
                    color = "#ec4899"
                    icon = "🔄"
                elif answer_type == "EVASIVE_CHALLENGE":
                    color = "#dc2626"
                    icon = "⚠️"
                else:
                    color = "#667eea"
                    icon = "📝"
                
                with st.expander(f"{icon} Q{idx//2 + 1}: {answer_type.replace('_', ' ').title()}", expanded=False):
                    st.markdown(f"**Your Answer:** {msg['content'][:100]}...")
                    st.markdown(f"**Analysis:** {analysis_notes}")
        else:
            st.info("Answer questions to see analysis here")
    
    st.markdown("---")
    
    # Creator Information
    st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
                    border: 2px solid rgba(102, 126, 234, 0.3);
                    border-radius: 12px;
                    padding: 1.2rem;
                    margin: 0.5rem 0 1rem 0;
                    text-align: center;">
            <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">👨‍💻</div>
            <div style="font-weight: 700; color: #667eea; font-size: 0.95rem; margin-bottom: 0.3rem;">Created by</div>
            <div style="font-weight: 600; color: #e2e8f0; font-size: 1.05rem; margin-bottom: 0.2rem;">Aayush Tripathi</div>
            <div style="color: #94a3b8; font-size: 0.85rem; line-height: 1.4;">
                ECE Department<br>
                LNMIIT
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Supervision Information
    st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%);
                    border: 2px solid rgba(16, 185, 129, 0.3);
                    border-radius: 12px;
                    padding: 1.2rem;
                    margin: 0.5rem 0 1rem 0;
                    text-align: center;">
            <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">👨‍🏫</div>
            <div style="font-weight: 700; color: #10b981; font-size: 0.95rem; margin-bottom: 0.3rem;">Supervised by</div>
            <div style="font-weight: 600; color: #e2e8f0; font-size: 1.05rem; margin-bottom: 0.2rem;">Dr. Nishant Gupta</div>
            <div style="color: #94a3b8; font-size: 0.85rem; line-height: 1.4;">
                Assistant Professor<br>
                LNMIIT
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # About with better graphics
    with st.expander("ℹ️ About This Tool"):
        st.markdown("""
            <div style="text-align: center; padding: 0.5rem 0;">
                <div style="font-size: 2.5rem; margin-bottom: 1rem;">🤖</div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        **Powered by:**
        
        🧠 **Gemini AI** - Question generation
        
        ⚡ **Local SLM** - Smart triage
        
        📊 **Analytics Engine** - Performance tracking
        
        🎯 **Adaptive System** - Difficulty adjustment
        """)
    
    # Footer
    st.markdown("""
        <div style="text-align: center; padding: 2rem 0 1rem 0; color: #64748b; font-size: 0.75rem;">
            <div style="margin-bottom: 0.5rem;">Made with ❤️ for interview prep</div>
            <div>v1.0.0</div>
        </div>
    """, unsafe_allow_html=True)

# Function to start interview with selected domain
def start_interview_with_domain(selected_domain):
    """Start interview with the given domain"""
    # Create centered loading screen
    st.markdown("""
        <style>
            .loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            }
            .loading-spinner {
                width: 80px;
                height: 80px;
                border: 8px solid rgba(255,255,255,0.3);
                border-top: 8px solid white;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-bottom: 2rem;
            }
            .loading-title {
                color: white;
                font-size: 3rem;
                font-weight: 800;
                text-align: center;
                margin: 0;
                text-shadow: 3px 3px 10px rgba(0,0,0,0.3);
                animation: pulse 2s ease-in-out infinite;
            }
            .loading-subtitle {
                color: rgba(255,255,255,0.9);
                font-size: 1.2rem;
                margin-top: 1rem;
                text-shadow: 2px 2px 5px rgba(0,0,0,0.2);
            }
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.8; transform: scale(1.02); }
            }
        </style>
    """, unsafe_allow_html=True)
    
    loading_container = st.empty()
    loading_container.markdown(f"""
        <div class="loading-overlay">
            <div class="loading-spinner"></div>
            <h1 class="loading-title">Preparing Your Interview</h1>
            <p class="loading-subtitle">Setting up questions for <strong>{selected_domain}</strong></p>
        </div>
    """, unsafe_allow_html=True)
    
    try:
        st.session_state.chatbot = InterviewOrchestrator(selected_domain)
        
        # Check for rate limit during initialization
        if st.session_state.chatbot.rate_limit_hit:
            loading_container.empty()
            st.error("🚨 Rate limit reached. Please try again later.")
            st.stop()
        
        if not st.session_state.chatbot.current_topic:
            loading_container.empty()
            st.error("❌ Failed to create interview syllabus. Please try again.")
            st.stop()
        
        # Start interview
        question = st.session_state.chatbot.start_interview()
        
        # Check if start_interview hit rate limit
        if isinstance(question, dict) and question.get("status") == "TERMINATED":
            loading_container.empty()
            st.error("🚨 Rate limit reached. Please try again later.")
            st.stop()
        
        st.session_state.messages.append({
            "role": "bot",
            "content": question,
            "analysis": None
        })
        st.session_state.interview_started = True
        st.session_state.domain = selected_domain
        st.session_state.question_count = 1
        
        loading_container.empty()
        st.rerun()
    except Exception as e:
        loading_container.empty()
        st.error(f"❌ Error starting interview: {str(e)}")

# Main content area
if not st.session_state.interview_started:
    # Welcome screen
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🚀 Ready to begin?")
        st.markdown("Enter the technical domain you'd like to be interviewed on:")
        
        domain = st.text_input(
            "Interview Domain",
            placeholder="e.g., Machine Learning, Python, Data Structures...",
            label_visibility="collapsed"
        )
        
        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            if st.button("🎯 Start Interview", use_container_width=True):
                if domain:
                    start_interview_with_domain(domain)
                else:
                    st.warning("⚠️ Please enter an interview domain")
    
    # Popular domains section
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🔥 Popular Domains")
    st.markdown("Click any card to start instantly:")
    
    # Domain cards with icons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 15px;
                        padding: 2rem 1rem;
                        text-align: center;
                        cursor: pointer;
                        transition: transform 0.3s ease;
                        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                        margin-bottom: 1rem;
                        min-height: 180px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;">
                <div style="font-size: 3rem; margin-bottom: 0.5rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">💻</div>
                <div style="color: white; font-weight: 700; font-size: 1.1rem; text-shadow: 2px 2px 8px rgba(0,0,0,0.4);">Software Engineering</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Start", key="se", use_container_width=True):
            start_interview_with_domain("Software Engineering")
    
    with col2:
        st.markdown("""
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        border-radius: 15px;
                        padding: 2rem 1rem;
                        text-align: center;
                        cursor: pointer;
                        transition: transform 0.3s ease;
                        box-shadow: 0 4px 15px rgba(240, 147, 251, 0.3);
                        margin-bottom: 1rem;
                        min-height: 180px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;">
                <div style="font-size: 3rem; margin-bottom: 0.5rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">🤖</div>
                <div style="color: white; font-weight: 700; font-size: 1.1rem; text-shadow: 2px 2px 8px rgba(0,0,0,0.4);">Machine Learning</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Start", key="ml", use_container_width=True):
            start_interview_with_domain("Machine Learning")
    
    with col3:
        st.markdown("""
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                        border-radius: 15px;
                        padding: 2rem 1rem;
                        text-align: center;
                        cursor: pointer;
                        transition: transform 0.3s ease;
                        box-shadow: 0 4px 15px rgba(79, 172, 254, 0.3);
                        margin-bottom: 1rem;">
                <div style="font-size: 3rem; margin-bottom: 0.5rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">⚡</div>
                <div style="color: white; font-weight: 700; font-size: 1.1rem; text-shadow: 2px 2px 8px rgba(0,0,0,0.4);">ECE</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Start", key="ec", use_container_width=True):
            start_interview_with_domain("ECE")
    
    with col4:
        st.markdown("""
            <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
                        border-radius: 15px;
                        padding: 2rem 1rem;
                        text-align: center;
                        cursor: pointer;
                        transition: transform 0.3s ease;
                        box-shadow: 0 4px 15px rgba(250, 112, 154, 0.3);
                        margin-bottom: 1rem;">
                <div style="font-size: 3rem; margin-bottom: 0.5rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">🔐</div>
                <div style="color: white; font-weight: 700; font-size: 1.1rem; text-shadow: 2px 2px 8px rgba(0,0,0,0.4);">Cryptography</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Start", key="crypto", use_container_width=True):
            start_interview_with_domain("Cryptography")
    
    # Second row of popular domains
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.markdown("""
            <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
                        border-radius: 15px;
                        padding: 2rem 1rem;
                        text-align: center;
                        cursor: pointer;
                        transition: transform 0.3s ease;
                        box-shadow: 0 4px 15px rgba(67, 233, 123, 0.3);
                        margin-bottom: 1rem;">
                <div style="font-size: 3rem; margin-bottom: 0.5rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">🐍</div>
                <div style="color: white; font-weight: 700; font-size: 1.1rem; text-shadow: 2px 2px 8px rgba(0,0,0,0.4);">Python Programming</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Start", key="python", use_container_width=True):
            start_interview_with_domain("Python Programming")
    
    with col6:
        st.markdown("""
            <div style="background: linear-gradient(135deg, #fa8bff 0%, #2bd2ff 100%);
                        border-radius: 15px;
                        padding: 2rem 1rem;
                        text-align: center;
                        cursor: pointer;
                        transition: transform 0.3s ease;
                        box-shadow: 0 4px 15px rgba(250, 139, 255, 0.3);
                        margin-bottom: 1rem;">
                <div style="font-size: 3rem; margin-bottom: 0.5rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">📊</div>
                <div style="color: white; font-weight: 700; font-size: 1.1rem; text-shadow: 2px 2px 8px rgba(0,0,0,0.4);">Data Structures</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Start", key="ds", use_container_width=True):
            start_interview_with_domain("Data Structures and Algorithms")
    
    with col7:
        st.markdown("""
            <div style="background: linear-gradient(135deg, #ff9a56 0%, #ff6a88 100%);
                        border-radius: 15px;
                        padding: 2rem 1rem;
                        text-align: center;
                        cursor: pointer;
                        transition: transform 0.3s ease;
                        box-shadow: 0 4px 15px rgba(255, 154, 86, 0.3);
                        margin-bottom: 1rem;">
                <div style="font-size: 3rem; margin-bottom: 0.5rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">🌐</div>
                <div style="color: white; font-weight: 700; font-size: 1.1rem; text-shadow: 2px 2px 8px rgba(0,0,0,0.4);">Web Development</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Start", key="web", use_container_width=True):
            start_interview_with_domain("Web Development")
    
    with col8:
        st.markdown("""
            <div style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
                        border-radius: 15px;
                        padding: 2rem 1rem;
                        text-align: center;
                        cursor: pointer;
                        transition: transform 0.3s ease;
                        box-shadow: 0 4px 15px rgba(168, 237, 234, 0.3);
                        margin-bottom: 1rem;">
                <div style="font-size: 3rem; margin-bottom: 0.5rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">☁️</div>
                <div style="color: white; font-weight: 700; font-size: 1.1rem; text-shadow: 2px 2px 8px rgba(0,0,0,0.4);">Cloud Computing</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Start", key="cloud", use_container_width=True):
            start_interview_with_domain("Cloud Computing")

else:
    # Interview in progress
    st.markdown(f"### 📚 Domain: {st.session_state.domain}")
    
    # Display chat history
    for idx, message in enumerate(st.session_state.messages):
        display_message(
            message["role"],
            message["content"],
            message.get("analysis"),
            idx
        )
    
    # Input area
    if not st.session_state.interview_ended:
        user_input = st.chat_input("Type your answer here... (or 'quit' to end)")
        
        if user_input:
            # Add user message
            st.session_state.messages.append({
                "role": "user",
                "content": user_input,
                "analysis": None
            })
            
            # Check for quit
            if user_input.lower() in ['quit', 'exit']:
                st.session_state.interview_ended = True
                st.session_state.messages.append({
                    "role": "bot",
                    "content": "Thank you for participating! The interview has ended. 🎉",
                    "analysis": None
                })
                st.rerun()
            
            # Process answer
            with st.spinner(""):
                typing_placeholder = st.empty()
                typing_placeholder.markdown("""
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                """, unsafe_allow_html=True)
                
                try:
                    response = st.session_state.chatbot.process_user_answer(user_input)
                    typing_placeholder.empty()
                    
                    # Update the user message with analysis
                    if response.get('analysis'):
                        st.session_state.messages[-1]['analysis'] = response['analysis']
                        # Track performance data
                        score = response['analysis'].get('answer_quality_score', 0)
                        st.session_state.performance_data.append({
                            'question_num': st.session_state.question_count,
                            'score': score,
                            'answer_type': response['analysis'].get('answer_type', 'Unknown')
                        })
                    
                    if response['status'] == "TERMINATED":
                        st.session_state.interview_ended = True
                        if response.get("reason") == "RateLimit":
                            end_message = "🚨 Rate limit reached. Thank you for your time!"
                        elif response.get("reason") == "SyllabusFinished":
                            end_message = "🎉 That covers all topics! Thank you for your time!"
                        else:
                            end_message = "Thank you for your time. The interview has concluded."
                        
                        st.session_state.messages.append({
                            "role": "bot",
                            "content": end_message,
                            "analysis": None
                        })
                    else:
                        st.session_state.question_count += 1
                        st.session_state.messages.append({
                            "role": "bot",
                            "content": response['next_question'],
                            "analysis": None
                        })
                    
                    st.rerun()
                    
                except Exception as e:
                    typing_placeholder.empty()
                    st.error(f"❌ An error occurred: {str(e)}")
    else:
        # Interview ended
        st.markdown("---")
        st.markdown("### 🎊 Interview Complete!")
        st.markdown("Thank you for using the Adaptive Performance-Based Interview Bot.")
        
        # Save to history
        if st.session_state.messages and st.session_state.domain:
            interview_record = {
                "domain": st.session_state.domain,
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "questions": st.session_state.question_count,
                "messages": st.session_state.messages.copy(),
                "performance": st.session_state.performance_data.copy()
            }
            # Only add if not already in history
            if not st.session_state.interview_history or \
               st.session_state.interview_history[-1]["date"] != interview_record["date"]:
                st.session_state.interview_history.append(interview_record)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 View Analytics", use_container_width=True):
                st.session_state.page = "analytics"
                st.rerun()
        
        with col2:
            if st.button("🔄 Start New Interview", use_container_width=True):
                # Reset session state
                st.session_state.initialized = False
                st.session_state.chatbot = None
                st.session_state.messages = []
                st.session_state.interview_started = False
                st.session_state.interview_ended = False
                st.session_state.domain = ""
                st.session_state.question_count = 0
                st.session_state.performance_data = []
                st.rerun()
