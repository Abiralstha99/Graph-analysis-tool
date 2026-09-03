# Backend API Documentation

## New AI-Powered Features

This backend now includes two new AI-powered services using Google's Gemini AI:

### 1. Graph Analysis API (`/analysis`)

**Purpose**: Provides AI-powered insights and analysis for graph comparisons between baseline and sample data.

#### Endpoints:

##### `POST /analysis/generate_insights`
- **Description**: Generates comprehensive AI analysis of a graph comparison
- **Parameters**:
  - `baseline`: UploadFile - The baseline CSV data file
  - `sample`: UploadFile - The sample CSV data file to compare
  - `sample_name`: Optional[str] - Custom name for the sample (defaults to filename)
- **Response**: JSON object containing:
  - `sample_name`: Name of the analyzed sample
  - `statistics`: Statistical comparison data
  - `ai_insights`: AI-generated analysis text with key observations, trends, implications
  - `metadata`: Analysis timestamp and file information

##### `GET /analysis/health`
- **Description**: Health check for the analysis service
- **Response**: Service status and Gemini API configuration status

### 2. Chatbox API (`/chat`)

**Purpose**: Interactive AI assistant for data analysis questions and general help.

#### Endpoints:

##### `POST /chat/send_message`
- **Description**: Send a message to the AI chatbot and maintain conversation history
- **Request Body**:
  ```json
  {
    "message": "Your question or message",
    "conversation_history": [...], // Optional previous messages
    "context": "Additional context about current graphs" // Optional
  }
  ```
- **Response**: Chat response with conversation ID and timestamp

##### `POST /chat/quick_question`
- **Description**: Ask a one-off question without maintaining conversation history
- **Request Body**:
  ```json
  {
    "question": "Your question here"
  }
  ```
- **Response**: Direct answer to the question

##### `GET /chat/conversation/{conversation_id}`
- **Description**: Retrieve conversation history by ID
- **Response**: Full conversation history

##### `DELETE /chat/conversation/{conversation_id}`
- **Description**: Clear a conversation history
- **Response**: Confirmation of deletion

##### `GET /chat/health`
- **Description**: Health check for the chat service
- **Response**: Service status, API configuration, and active conversation count

## Setup Requirements

### Environment Variables
Create a `.env` file in the backend directory with:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

### API Key Setup
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file

### Dependencies
The following new packages have been added to `requirements.txt`:
- `google-generativeai==0.3.2` - Gemini AI integration
- `pydantic==2.5.0` - Enhanced data validation

### Installation
```bash
cd backend
pip install -r requirements.txt
```

## Usage Examples

### Graph Analysis
```python
import requests

# Analyze a graph comparison
with open('baseline.csv', 'rb') as baseline, open('sample.csv', 'rb') as sample:
    response = requests.post(
        'http://localhost:8080/analysis/generate_insights',
        files={
            'baseline': baseline,
            'sample': sample
        },
        data={'sample_name': 'Test Sample 1'}
    )
    analysis = response.json()
    print(analysis['ai_insights'])
```

### Chatbox Interaction
```python
import requests

# Send a chat message
response = requests.post(
    'http://localhost:8080/chat/send_message',
    json={
        'message': 'Can you explain what might cause a shift in spectroscopy peaks?',
        'context': 'Currently analyzing FTIR spectroscopy data'
    }
)
chat_response = response.json()
print(chat_response['response'])
```

## Features

### Graph Analysis AI Features:
- Statistical comparison analysis
- Visual pattern recognition
- Trend identification
- Anomaly detection
- Scientific interpretation
- Data quality assessment

### Chatbot Features:
- Conversation memory
- Context-aware responses
- Scientific knowledge base
- Data analysis guidance
- Research workflow suggestions

## Error Handling
Both services include comprehensive error handling and will return appropriate HTTP status codes with detailed error messages when issues occur.

## Security Notes
- API keys should be kept secure and not committed to version control
- Consider implementing rate limiting for production use
- The conversation storage is currently in-memory (use a database for production)