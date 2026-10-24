"""
analytics_service.py - Pure Python analytics and feedback service.
No Streamlit dependencies. Used by both Streamlit app and FastAPI backend.
"""

from typing import Dict, Any, Optional, List
import database


def calculate_interview_stats(
    candidate_id: Optional[int] = None,
    session_id: Optional[int] = None,
    messages: Optional[List[Dict[str, Any]]] = None,
    chatbot: Any = None,
    db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Calculate statistics from SQLite DB for candidate/session, with optional in-memory fallback.
    """
    if candidate_id is not None or session_id is not None:
        db_stats = database.calculate_db_stats(
            candidate_id=candidate_id,
            session_id=session_id,
            db_path=db_path
        )
        if db_stats and db_stats.get("total_answers", 0) > 0:
            return db_stats

    if not messages:
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

    for msg in messages:
        if msg.get("role") == "bot":
            stats["total_questions"] += 1
        elif msg.get("role") == "user" and msg.get("analysis"):
            stats["total_answers"] += 1
            analysis = msg["analysis"]

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
            else:
                stats["answer_types"]["Normal"] += 1

            if "score_used" in analysis and analysis["score_used"] is not None:
                stats["scores"].append(float(analysis["score_used"]))
            elif "answer_quality_score" in analysis and analysis["answer_quality_score"] is not None:
                stats["scores"].append(float(analysis["answer_quality_score"]))

    if chatbot:
        if hasattr(chatbot, "current_topic") and chatbot.current_topic:
            stats["topics_covered"].add(chatbot.current_topic)
        if hasattr(chatbot, "topic_syllabus"):
            for topic in chatbot.topic_syllabus:
                stats["topics_covered"].add(topic)

    return stats


def generate_ai_feedback(stats: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate overall AI feedback based on performance metrics.
    """
    if not stats or stats.get("total_answers", 0) == 0:
        return "Not enough data to generate feedback."

    feedback = []

    scores = stats.get("scores", [])
    avg_score = sum(scores) / len(scores) if scores else 0.0

    # Overall performance
    if avg_score >= 7.0:
        feedback.append("🌟 **Excellent Performance**: You demonstrated strong knowledge and clear communication throughout the interview.")
    elif avg_score >= 5.0:
        feedback.append("👍 **Good Effort**: You showed decent understanding, but there's room for improvement in depth and clarity.")
    elif avg_score >= 3.0:
        feedback.append("📚 **Needs Improvement**: Consider reviewing the fundamentals and practicing more detailed explanations.")
    else:
        feedback.append("💪 **Keep Learning**: Focus on building stronger foundational knowledge in this domain.")

    total_answers = stats["total_answers"]
    answer_types = stats.get("answer_types", {})

    normal_pct = (answer_types.get("Normal", 0) / total_answers) * 100
    vague_pct = (answer_types.get("Vague", 0) / total_answers) * 100
    incorrect_pct = (answer_types.get("Incorrect", 0) / total_answers) * 100

    if normal_pct >= 60:
        feedback.append(f"✅ **Strong Answers**: {normal_pct:.0f}% of your responses were clear and accurate.")

    if vague_pct > 30:
        feedback.append(f"⚠️ **Be More Specific**: {vague_pct:.0f}% of answers lacked detail. Try providing concrete examples and explanations.")

    if incorrect_pct > 20:
        feedback.append(f"❌ **Accuracy Concerns**: {incorrect_pct:.0f}% of answers contained factual errors. Review core concepts carefully.")

    # Behavioral feedback
    if answer_types.get("Hesitation", 0) > 3:
        feedback.append("🤔 **Confidence**: Multiple hesitations detected. Practice articulating your thoughts more confidently.")

    if answer_types.get("Knowledge_Gap", 0) > 2:
        feedback.append("💭 **Knowledge Gaps**: Several topics where you admitted not knowing. Identify and study these areas.")

    if answer_types.get("Violation", 0) > 0:
        feedback.append("⚠️ **Professional Conduct**: Maintain professional demeanor even when questions are challenging.")

    return "\n\n".join(feedback)


def generate_ai_feedback_items(stats: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Generates structured final summary items without emojis.
    Each item has {category: 'strength'|'gap'|'info', title: str, text: str}.
    Derived from the EXACT SAME logic and thresholds as generate_ai_feedback.
    """
    if not stats or not stats.get("scores"):
        return [{
            "category": "info",
            "title": "Interview Incomplete",
            "text": "Interview completed with limited responses. Review the domain fundamentals."
        }]

    items = []
    avg_score = sum(stats["scores"]) / len(stats["scores"])

    # Overall performance
    if avg_score >= 7.0:
        items.append({
            "category": "strength",
            "title": "Excellent Performance",
            "text": "You demonstrated strong knowledge and clear communication throughout the interview."
        })
    elif avg_score >= 5.0:
        items.append({
            "category": "info",
            "title": "Good Effort",
            "text": "You showed decent understanding, but there's room for improvement in depth and clarity."
        })
    elif avg_score >= 3.0:
        items.append({
            "category": "gap",
            "title": "Needs Improvement",
            "text": "Consider reviewing the fundamentals and practicing more detailed explanations."
        })
    else:
        items.append({
            "category": "gap",
            "title": "Keep Learning",
            "text": "Focus on building stronger foundational knowledge in this domain."
        })

    total_answers = stats.get("total_answers", 0)
    answer_types = stats.get("answer_types", {})

    if total_answers > 0:
        normal_pct = (answer_types.get("Normal", 0) / total_answers) * 100
        vague_pct = (answer_types.get("Vague", 0) / total_answers) * 100
        incorrect_pct = (answer_types.get("Incorrect", 0) / total_answers) * 100

        if normal_pct >= 60:
            items.append({
                "category": "strength",
                "title": "Strong Answers",
                "text": f"{normal_pct:.0f}% of your responses were clear and accurate."
            })

        if vague_pct > 30:
            items.append({
                "category": "gap",
                "title": "Be More Specific",
                "text": f"{vague_pct:.0f}% of answers lacked detail. Try providing concrete examples and explanations."
            })

        if incorrect_pct > 20:
            items.append({
                "category": "gap",
                "title": "Accuracy Concerns",
                "text": f"{incorrect_pct:.0f}% of answers contained factual errors. Review core concepts carefully."
            })

    # Behavioral feedback
    if answer_types.get("Hesitation", 0) > 3:
        items.append({
            "category": "gap",
            "title": "Confidence",
            "text": "Multiple hesitations detected. Practice articulating your thoughts more confidently."
        })

    if answer_types.get("Knowledge_Gap", 0) > 2:
        items.append({
            "category": "gap",
            "title": "Knowledge Gaps",
            "text": "Several topics where you admitted not knowing. Identify and study these areas."
        })

    if answer_types.get("Violation", 0) > 0:
        items.append({
            "category": "gap",
            "title": "Professional Conduct",
            "text": "Maintain professional demeanor even when questions are challenging."
        })

    return items
