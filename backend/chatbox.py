from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime
import json
import traceback

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
conversation_sessions = {}

def generate_conversation_id() -> str:
    """Generate a unique conversation ID"""
    return f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def parse_graph_context(context_str: str) -> str:
    """Parse and enhance the graph context from the frontend"""
    try:
        # Try to parse as JSON first to handle structured data
        if context_str.strip().startswith('{'):
            context_data = json.loads(context_str)
            
            # Build a more intelligent context description
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
        # Fallback to treating as plain text
        pass
    
    # If not JSON or parsing failed, return as formatted text context
    if context_str.strip():
        return f"\nCurrent session context:\n{context_str}\n"
    
    return ""

def format_conversation_history(messages: List[ChatMessage]) -> str:
    """Format conversation history for context"""
    if not messages:
        return ""
    
    formatted = "Previous conversation:\n"
    for msg in messages[-5:]:  # Only include last 5 messages for context
        role = "User" if msg.role == "user" else "Assistant"
        formatted += f"{role}: {msg.content}\n"
    return formatted

@router.post("/send_message", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest):
    """
    Send a message to the AI chatbot and get a response
    """
    try:
        # Check if required modules are available
        if not GENAI_AVAILABLE:
            return JSONResponse(
                status_code=500, 
                content={"error": "Google Generative AI library not available"}
            )
        
        settings = Settings.from_environment()
        if not settings.gemini_api_key:
            return JSONResponse(
                status_code=500, 
                content={"error": "Gemini AI API key not configured"}
            )

        genai.configure(api_key=settings.gemini_api_key)
        
        # Generate conversation ID if this is a new conversation
        conversation_id = generate_conversation_id()
        
        # Configure Gemini model with fallback
        model = None
        model_names = ['models/gemini-2.5-flash', 'models/gemini-pro', 'gemini-pro', 'models/gemini-1.0-pro', 'gemini-1.0-pro-latest']
        
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                break
            except Exception as e:
                continue
        
        if model is None:
            # Provide intelligent fallback response when AI is unavailable
            graph_available = bool(request.context and request.context.strip())
            
            if graph_available and request.context:
                try:
                    context_data = json.loads(request.context) if request.context.strip().startswith('{') else {}
                    fallback_msg = "I'm sorry, the AI assistant is currently unavailable. However, I can see you have datasets loaded: "
                    
                    if 'baseline' in context_data:
                        baseline_name = context_data['baseline'].get('name', 'baseline dataset')
                        fallback_msg += f"Your baseline is '{baseline_name}'. "
                    
                    if 'selectedSample' in context_data and context_data['selectedSample']:
                        sample_name = context_data['selectedSample'].get('name', 'sample dataset')
                        fallback_msg += f"Currently analyzing '{sample_name}'. "
                    
                    if 'allSamples' in context_data and context_data['allSamples']:
                        sample_count = len(context_data['allSamples'])
                        fallback_msg += f"You have {sample_count} sample dataset(s) for comparison. "
                    
                    fallback_msg += "Please try again later for AI-powered analysis insights."
                    
                except (json.JSONDecodeError, KeyError):
                    fallback_msg = "I'm sorry, the AI assistant is currently unavailable. I can see you have graph data loaded. Please try again later for detailed analysis."
            else:
                fallback_msg = "I'm sorry, the AI assistant is currently unavailable. This is a data analysis and graphing application where you can upload CSV files to compare baseline and sample data. Please try again later when the AI service is restored."
            
            fallback_response = ChatResponse(
                response=fallback_msg,
                conversation_id=conversation_id,
                timestamp=datetime.now().isoformat(),
                status="fallback"
            )
            return fallback_response
        
        # Build context for the AI
        graph_available = bool(request.context and request.context.strip())
        
        if graph_available:
            system_context = """
            You are an AI assistant specialized in data analysis and graph interpretation. You're currently helping a user analyze their datasets in a graphing application.
            
            CURRENT SESSION: The user has loaded datasets and you have access to their current graph analysis context. Use this information to provide specific, relevant answers about their data.
            
            Your capabilities include:
            - Analyzing the current datasets (baseline vs samples)
            - Interpreting statistical patterns and trends
            - Providing insights on data comparisons
            - Suggesting analysis approaches based on the data structure
            - Answering specific questions about the loaded datasets
            - Helping with data interpretation and scientific conclusions
            
            When the user asks questions, refer to their specific datasets by name and provide concrete insights based on the actual data context provided.
            Be technical and specific when discussing their data patterns, statistics, and comparisons.
            """
        else:
            system_context = """
            You are an AI assistant specialized in helping users with data analysis, graph interpretation, and scientific research. 
            You're part of a graphing application that allows users to compare baseline data with sample data.
            
            Your capabilities include:
            - Helping interpret graphs and data visualizations
            - Providing insights on data trends and patterns
            - Answering questions about statistical analysis
            - Offering suggestions for data analysis workflows
            - Explaining scientific concepts related to the data
            
            Be helpful, accurate, and concise in your responses. When discussing data or graphs, be specific and technical when appropriate.
            Note: The user hasn't loaded any datasets yet, so provide general guidance about data analysis and graphing.
            """
        
        # Add conversation history if available
        history_context = format_conversation_history(request.conversation_history)
        
        # Parse and enhance graph context
        graph_context = ""
        if request.context:
            graph_context = parse_graph_context(request.context)
        
        # Build the full prompt
        full_prompt = f"{system_context}\n\n{history_context}{graph_context}\nUser: {request.message}"
        
        # Generate response with better error handling
        try:
            response = model.generate_content(full_prompt)
            
            if not response or not response.text:
                raise Exception("Empty response from Gemini AI")
                
        except Exception as e:
            # Provide intelligent fallback response based on available context
            if graph_available and request.context:
                try:
                    # Try to provide basic insights from the context
                    context_data = json.loads(request.context) if request.context.strip().startswith('{') else {}
                    fallback_msg = "I'm experiencing technical difficulties with the AI service, but I can see you have datasets loaded. "
                    
                    if 'baseline' in context_data:
                        baseline_name = context_data['baseline'].get('name', 'baseline dataset')
                        fallback_msg += f"Your baseline is '{baseline_name}'. "
                    
                    if 'selectedSample' in context_data and context_data['selectedSample']:
                        sample_name = context_data['selectedSample'].get('name', 'sample dataset')
                        fallback_msg += f"You're currently analyzing '{sample_name}'. "
                    
                    if 'allSamples' in context_data and context_data['allSamples']:
                        sample_count = len(context_data['allSamples'])
                        fallback_msg += f"You have {sample_count} sample dataset(s) available for comparison. "
                    
                    fallback_msg += f"Your question was: '{request.message}'. Please try again when the AI service is restored for more detailed analysis."
                    
                except (json.JSONDecodeError, KeyError):
                    fallback_msg = f"I'm sorry, the AI assistant is currently experiencing technical difficulties. I can see you have graph data loaded. Your question was: '{request.message}'. Please try again later when the AI service is restored."
            else:
                fallback_msg = f"I'm sorry, the AI assistant is currently experiencing technical difficulties. This is a data analysis and graphing application where you can upload CSV files to compare baseline and sample data. Your question was: '{request.message}'. Please try again later when the AI service is restored."
            
            fallback_response = ChatResponse(
                response=fallback_msg,
                conversation_id=conversation_id,
                timestamp=datetime.now().isoformat(),
                status="fallback_error"
            )
            return fallback_response
        
        # Create response object
        chat_response = ChatResponse(
            response=response.text,
            conversation_id=conversation_id,
            timestamp=datetime.now().isoformat(),
            status="success"
        )
        
        # Store conversation in memory (in production, use a database)
        if conversation_id not in conversation_sessions:
            conversation_sessions[conversation_id] = []
        
        conversation_sessions[conversation_id].extend([
            {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()},
            {"role": "assistant", "content": response.text, "timestamp": datetime.now().isoformat()}
        ])
        
        return chat_response
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to process chat message: {str(e)}"}
        )

@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Retrieve a conversation history by ID
    """
    try:
        if conversation_id not in conversation_sessions:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return JSONResponse(content={
            "conversation_id": conversation_id,
            "messages": conversation_sessions[conversation_id],
            "status": "success"
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to retrieve conversation: {str(e)}"}
        )

@router.delete("/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """
    Clear a conversation history
    """
    try:
        if conversation_id in conversation_sessions:
            del conversation_sessions[conversation_id]
        
        return JSONResponse(content={
            "message": "Conversation cleared successfully",
            "conversation_id": conversation_id,
            "status": "success"
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to clear conversation: {str(e)}"}
        )

@router.post("/quick_question")
async def ask_quick_question(request: dict):
    """
    Ask a quick question without maintaining conversation history
    """
    try:
        # Check if required modules are available
        if not GENAI_AVAILABLE:
            return JSONResponse(
                status_code=500, 
                content={"error": "Google Generative AI library not available"}
            )
        
        settings = Settings.from_environment()
        if not settings.gemini_api_key:
            return JSONResponse(
                status_code=500, 
                content={"error": "Gemini AI API key not configured"}
            )

        genai.configure(api_key=settings.gemini_api_key)
        
        question = request.get("question", "")
        if not question:
            return JSONResponse(
                status_code=400, 
                content={"error": "Question is required"}
            )
        
        # Configure Gemini model with fallback
        model = None
        model_names = ['models/gemini-pro', 'gemini-pro', 'models/gemini-1.0-pro', 'gemini-1.0-pro-latest']
        
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                break
            except Exception as e:
                continue
        
        if model is None:
            # Provide fallback response for quick questions
            return JSONResponse(content={
                "question": question,
                "answer": "I'm sorry, the AI assistant is currently unavailable. This application helps you analyze and compare data from CSV files. You can upload baseline and sample data to generate statistical comparisons and visualizations. Please try again later when the AI service is restored, or contact support if the issue persists.",
                "timestamp": datetime.now().isoformat(),
                "status": "fallback"
            })
        
        # Simple system context for quick questions
        system_context = """
        You are a helpful AI assistant for a data analysis and graphing application. 
        Provide concise, accurate answers to user questions about data analysis, statistics, and graph interpretation.
        """
        
        full_prompt = f"{system_context}\n\nUser question: {question}"
        
        # Generate response with error handling
        try:
            response = model.generate_content(full_prompt)
            
            if not response or not response.text:
                raise Exception("Empty response from AI")
            
            return JSONResponse(content={
                "question": question,
                "answer": response.text,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            })
            
        except Exception as ai_error:
            # Provide fallback response when AI generation fails
            return JSONResponse(content={
                "question": question,
                "answer": f"I'm sorry, the AI assistant is currently unavailable due to technical difficulties. Your question was about '{question}'. This application helps you analyze and compare data from CSV files. You can upload baseline and sample data to generate statistical comparisons and visualizations. Please try again later when the AI service is restored.",
                "timestamp": datetime.now().isoformat(),
                "status": "fallback"
            })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to process quick question: {str(e)}"}
        )

@router.get("/health")
async def chat_health():
    """Health check for chat service"""
    gemini_status = "configured" if Settings.from_environment().gemini_api_key else "not_configured"
    return {
        "status": "ok",
        "gemini_api": gemini_status,
        "service": "chatbox",
        "active_conversations": len(conversation_sessions)
    }
