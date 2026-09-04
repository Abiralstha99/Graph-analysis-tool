from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime
import json

from .config import Settings
from .schemas.chat import ChatMessage, ChatRequest, ChatResponse

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

router = APIRouter(prefix="/chat", tags=["Chatbox"])

# In-memory storage for conversation sessions (in production, use a database)
conversation_sessions: dict = {}

_GEMINI_MODELS = [
    'models/gemini-2.5-flash',
    'models/gemini-pro',
    'gemini-pro',
    'models/gemini-1.0-pro',
    'gemini-1.0-pro-latest',
]


def generate_conversation_id() -> str:
    """Generate a unique conversation ID"""
    return f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def parse_graph_context(context_str: str) -> str:
    """Parse and enhance the graph context from the frontend"""
    try:
        if context_str.strip().startswith('{'):
            context_data = json.loads(context_str)

            enhanced_context = "\nCurrent Graph Analysis Context:\n"

            if isinstance(context_data, dict):
                if 'baseline' in context_data:
                    baseline_info = context_data['baseline']
                    enhanced_context += f"• Baseline Dataset: {baseline_info.get('name', 'Unknown')}\n"
                    if 'stats' in baseline_info:
                        stats = baseline_info['stats']
                        enhanced_context += f"  - Rows: {stats.get('rows', 'N/A')}, Columns: {stats.get('columns', 'N/A')}\n"
                        if 'numerical_summary' in stats:
                            enhanced_context += f"  - Numerical columns: {len(stats['numerical_summary'])}\n"

                if 'selectedSample' in context_data and context_data['selectedSample']:
                    sample_info = context_data['selectedSample']
                    enhanced_context += f"• Selected Sample: {sample_info.get('name', 'Unknown')}\n"
                    if 'stats' in sample_info:
                        stats = sample_info['stats']
                        enhanced_context += f"  - Rows: {stats.get('rows', 'N/A')}, Columns: {stats.get('columns', 'N/A')}\n"

                if 'allSamples' in context_data:
                    samples = context_data['allSamples']
                    if samples:
                        enhanced_context += f"• Total Samples Available: {len(samples)}\n"
                        sample_names = [s.get('name', 'Unknown') for s in samples]
                        enhanced_context += f"  - Sample Names: {', '.join(sample_names)}\n"

                if 'graphType' in context_data:
                    enhanced_context += f"• Current Graph Type: {context_data['graphType']}\n"

                if 'selectedColumns' in context_data and context_data['selectedColumns']:
                    enhanced_context += f"• Analyzed Columns: {', '.join(context_data['selectedColumns'])}\n"

            enhanced_context += "\nThe user can ask questions about these datasets, their statistical properties, patterns, or comparisons between baseline and sample data.\n"
            return enhanced_context

    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    if context_str.strip():
        return f"\nCurrent session context:\n{context_str}\n"

    return ""


def format_conversation_history(messages: List[ChatMessage]) -> str:
    """Format conversation history for context"""
    if not messages:
        return ""

    formatted = "Previous conversation:\n"
    for msg in messages[-5:]:
        role = "User" if msg.role == "user" else "Assistant"
        formatted += f"{role}: {msg.content}\n"
    return formatted


def _get_model():
    """Return the first working Gemini model, or None if none available."""
    for model_name in _GEMINI_MODELS:
        try:
            return genai.GenerativeModel(model_name)
        except Exception:
            continue
    return None


def _build_fallback_from_context(message: str, context: Optional[str]) -> str:
    """Build an informative fallback message when AI is unavailable."""
    if not context:
        return (
            "I'm sorry, the AI assistant is currently unavailable. "
            "This is a data analysis and graphing application where you can upload CSV files "
            "to compare baseline and sample data. Please try again later."
        )

    try:
        context_data = json.loads(context) if context.strip().startswith('{') else {}
        parts = ["I'm sorry, the AI assistant is currently unavailable. However, I can see you have datasets loaded: "]

        if 'baseline' in context_data:
            parts.append(f"Your baseline is '{context_data['baseline'].get('name', 'baseline dataset')}'. ")

        if context_data.get('selectedSample'):
            parts.append(f"Currently analyzing '{context_data['selectedSample'].get('name', 'sample dataset')}'. ")

        samples = context_data.get('allSamples', [])
        if samples:
            parts.append(f"You have {len(samples)} sample dataset(s) for comparison. ")

        parts.append("Please try again later for AI-powered analysis insights.")
        return "".join(parts)

    except (json.JSONDecodeError, KeyError):
        return (
            "I'm sorry, the AI assistant is currently unavailable. "
            "I can see you have graph data loaded. Please try again later for detailed analysis."
        )


@router.post("/send_message", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest):
    """Send a message to the AI chatbot and get a response."""
    if not GENAI_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Generative AI library not available.",
        )

    settings = Settings.from_environment()
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini AI API key not configured.",
        )

    genai.configure(api_key=settings.gemini_api_key)

    conversation_id = generate_conversation_id()
    model = _get_model()

    if model is None:
        return ChatResponse(
            response=_build_fallback_from_context(request.message, request.context),
            conversation_id=conversation_id,
            timestamp=datetime.now().isoformat(),
            status="fallback",
        )

    graph_available = bool(request.context and request.context.strip())

    if graph_available:
        system_context = (
            "You are an AI assistant specialized in data analysis and graph interpretation. "
            "You're currently helping a user analyze their datasets in a graphing application.\n\n"
            "CURRENT SESSION: The user has loaded datasets and you have access to their current graph "
            "analysis context. Use this information to provide specific, relevant answers about their data.\n\n"
            "Your capabilities include:\n"
            "- Analyzing the current datasets (baseline vs samples)\n"
            "- Interpreting statistical patterns and trends\n"
            "- Providing insights on data comparisons\n"
            "- Suggesting analysis approaches based on the data structure\n"
            "- Answering specific questions about the loaded datasets\n"
            "- Helping with data interpretation and scientific conclusions\n\n"
            "When the user asks questions, refer to their specific datasets by name and provide "
            "concrete insights based on the actual data context provided. "
            "Be technical and specific when discussing their data patterns, statistics, and comparisons."
        )
    else:
        system_context = (
            "You are an AI assistant specialized in helping users with data analysis, graph "
            "interpretation, and scientific research. You're part of a graphing application that "
            "allows users to compare baseline data with sample data.\n\n"
            "Your capabilities include:\n"
            "- Helping interpret graphs and data visualizations\n"
            "- Providing insights on data trends and patterns\n"
            "- Answering questions about statistical analysis\n"
            "- Offering suggestions for data analysis workflows\n"
            "- Explaining scientific concepts related to the data\n\n"
            "Be helpful, accurate, and concise in your responses. When discussing data or graphs, "
            "be specific and technical when appropriate.\n"
            "Note: The user hasn't loaded any datasets yet, so provide general guidance about data "
            "analysis and graphing."
        )

    history_context = format_conversation_history(request.conversation_history)
    graph_context = parse_graph_context(request.context) if request.context else ""
    full_prompt = f"{system_context}\n\n{history_context}{graph_context}\nUser: {request.message}"

    try:
        response = model.generate_content(full_prompt)
        if not response or not response.text:
            raise ValueError("Empty response from Gemini AI")
        ai_text = response.text
    except Exception:
        # AI call failed — return a graceful fallback instead of leaking the error
        return ChatResponse(
            response=_build_fallback_from_context(request.message, request.context),
            conversation_id=conversation_id,
            timestamp=datetime.now().isoformat(),
            status="fallback_error",
        )

    # Persist conversation in memory
    conversation_sessions.setdefault(conversation_id, []).extend([
        {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()},
        {"role": "assistant", "content": ai_text, "timestamp": datetime.now().isoformat()},
    ])

    return ChatResponse(
        response=ai_text,
        conversation_id=conversation_id,
        timestamp=datetime.now().isoformat(),
        status="success",
    )


@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Retrieve a conversation history by ID."""
    if conversation_id not in conversation_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    return {
        "conversation_id": conversation_id,
        "messages": conversation_sessions[conversation_id],
        "status": "success",
    }


@router.delete("/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear a conversation history."""
    if conversation_id in conversation_sessions:
        del conversation_sessions[conversation_id]

    return {
        "message": "Conversation cleared successfully",
        "conversation_id": conversation_id,
        "status": "success",
    }


@router.post("/quick_question")
async def ask_quick_question(request: dict):
    """Ask a quick question without maintaining conversation history."""
    if not GENAI_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Generative AI library not available.",
        )

    settings = Settings.from_environment()
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini AI API key not configured.",
        )

    question = request.get("question", "")
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A non-empty 'question' field is required.",
        )

    genai.configure(api_key=settings.gemini_api_key)

    # Use a slightly smaller model list for quick questions (vision not needed)
    model = None
    for model_name in ['models/gemini-pro', 'gemini-pro', 'models/gemini-1.0-pro', 'gemini-1.0-pro-latest']:
        try:
            model = genai.GenerativeModel(model_name)
            break
        except Exception:
            continue

    if model is None:
        return JSONResponse(content={
            "question": question,
            "answer": (
                "I'm sorry, the AI assistant is currently unavailable. "
                "This application helps you analyze and compare data from CSV files. "
                "Please try again later when the AI service is restored."
            ),
            "timestamp": datetime.now().isoformat(),
            "status": "fallback",
        })

    system_context = (
        "You are a helpful AI assistant for a data analysis and graphing application. "
        "Provide concise, accurate answers to user questions about data analysis, statistics, "
        "and graph interpretation."
    )
    full_prompt = f"{system_context}\n\nUser question: {question}"

    try:
        response = model.generate_content(full_prompt)
        if not response or not response.text:
            raise ValueError("Empty response from AI")

        return JSONResponse(content={
            "question": question,
            "answer": response.text,
            "timestamp": datetime.now().isoformat(),
            "status": "success",
        })

    except Exception:
        return JSONResponse(content={
            "question": question,
            "answer": (
                "I'm sorry, the AI assistant is currently experiencing technical difficulties. "
                "This application helps you analyze and compare data from CSV files. "
                "Please try again later when the AI service is restored."
            ),
            "timestamp": datetime.now().isoformat(),
            "status": "fallback",
        })


@router.get("/health")
async def chat_health():
    """Health check for chat service"""
    gemini_status = "configured" if Settings.from_environment().gemini_api_key else "not_configured"
    return {
        "status": "ok",
        "gemini_api": gemini_status,
        "service": "chatbox",
        "active_conversations": len(conversation_sessions),
    }
