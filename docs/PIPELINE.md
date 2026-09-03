# MRG Labs Graphing App - Project Pipeline

## 🔄 Data Flow Architecture

This document outlines the complete pipeline of how data flows through the MRG Labs FTIR Graphing Application, from user interaction to final visualization and AI analysis.

---

## 📊 High-Level Pipeline Overview

```
┌─────────────────┐
│  User Browser   │
│  (React App)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         Frontend Layer                  │
│  ┌──────────────────────────────────┐  │
│  │  1. Authentication & Routing     │  │
│  │  2. File Upload & Validation     │  │
│  │  3. Data Visualization           │  │
│  │  4. AI Chat Interface            │  │
│  └──────────────────────────────────┘  │
└────────┬────────────────────────────────┘
         │ HTTP/REST API
         ▼
┌─────────────────────────────────────────┐
│         Backend Layer (FastAPI)         │
│  ┌──────────────────────────────────┐  │
│  │  1. Session Management           │  │
│  │  2. File Processing              │  │
│  │  3. Graph Generation             │  │
│  │  4. AI Analysis Services         │  │
│  └──────────────────────────────────┘  │
└────────┬────────────────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌──────────────┐
│  MySQL  │ │ Google Gemini│
│Database │ │   AI API     │
└─────────┘ └──────────────┘
```

---

## 🔐 Stage 1: User Authentication Pipeline

### 1.1 Signup Flow

```
User fills signup form
    ↓
Frontend validates input (email format, password strength)
    ↓
POST /register → Backend
    ↓
Backend validates data
    ↓
Check if email exists in MySQL
    ↓
If new: Hash password with bcrypt
    ↓
Insert user into `users` table
    ↓
Create session, set cookie
    ↓
Return success + user data
    ↓
Frontend stores auth state in AuthContext
    ↓
Redirect to Dashboard
```

**Technologies:**
- Frontend: React + Chakra UI forms, React Context API
- Backend: FastAPI, bcrypt, MySQL
- Security: bcrypt (12 rounds), SQL parameterization

---

### 1.2 Login Flow

```
User enters credentials
    ↓
POST /login → Backend
    ↓
Query user by email from MySQL
    ↓
Verify password with bcrypt.checkpw()
    ↓
If valid: Create session with UUID
    ↓
Store session in `sessions` table (user_id, expires_at)
    ↓
Set httpOnly cookie with session_id
    ↓
Return user data (no password)
    ↓
Frontend updates AuthContext
    ↓
Redirect to Dashboard
```

**Session Management:**
- Session expires after 7 days
- httpOnly cookies prevent XSS attacks
- Sessions stored in MySQL with expiration timestamps

---

### 1.3 Protected Routes

```
User navigates to protected page
    ↓
React Router checks AuthContext
    ↓
If not authenticated:
    ↓
    Redirect to /login
    ↓
If authenticated:
    ↓
    Every API request includes session cookie
    ↓
    Backend validates session via @require_auth decorator
    ↓
    Check session exists in DB and not expired
    ↓
    If valid: Proceed with request
    ↓
    If invalid: Return 401 Unauthorized
```

---

## 📁 Stage 2: File Upload & Processing Pipeline

### 2.1 Baseline Upload

```
User clicks "Upload Baseline"
    ↓
Browser file picker opens
    ↓
User selects CSV file
    ↓
Frontend reads file with FileReader API
    ↓
Papa Parse parses CSV to JSON
    ↓
Validate structure:
  - Check for X and Y columns
  - Verify numeric data
  - Minimum data points (e.g., 100)
    ↓
Store in React state as ParsedCSV object:
  {
    filename: string,
    x: number[],
    y: number[]
  }
    ↓
Display filename in UI
    ↓
Enable "Upload Samples" button
```

**Key Libraries:**
- `Papa Parse`: CSV parsing
- React state hooks: Data management

---

### 2.2 Sample Files Upload

```
User clicks "Upload Samples"
    ↓
Browser file picker (multiple=true)
    ↓
User selects multiple CSV files
    ↓
For each file:
    ↓
    Read with FileReader
    ↓
    Parse with Papa Parse
    ↓
    Validate structure (same as baseline)
    ↓
    Store in samples array with ParsedCSV format
    ↓
Display all samples in sidebar:
  - Filename
  - Data point count
  - Interactive selection
```

---

## 📊 Stage 3: Graph Visualization Pipeline

### 3.1 Interactive Chart Generation

```
User selects a sample from sidebar
    ↓
Frontend triggers useEffect with [baseline, selectedSample]
    ↓
Prepare Chart.js data structure:
  {
    datasets: [
      {
        label: baseline.filename,
        data: baseline.x.map((x, i) => ({x, y: baseline.y[i]})),
        borderColor: 'blue',
        borderWidth: 2
      },
      {
        label: sample.filename,
        data: sample.x.map((x, i) => ({x, y: sample.y[i]})),
        borderColor: 'red',
        borderWidth: 2
      }
    ]
  }
    ↓
Configure Chart.js options:
  - Responsive: true
  - Scales: linear X and Y axes
  - Plugins: zoom, pan, legend
  - Tooltips: show (x, y) coordinates
    ↓
Render with react-chartjs-2
    ↓
User can:
  - Zoom with mouse wheel
  - Pan by dragging
  - Reset view with button
  - Toggle gridlines
```

**Visualization Stack:**
- Chart.js: Core charting library
- react-chartjs-2: React wrapper
- chartjs-plugin-zoom: Interactive zoom/pan

---

### 3.2 FTIR Analysis & Scoring

```
User uploads samples
    ↓
For each sample, calculate difference from baseline:
    ↓
    Interpolate baseline and sample to common X points
    ↓
    Calculate delta: δ = baseline_y - sample_y
    ↓
    Apply scoring method (user-selectable):
    ↓
    ┌─────────────────────────────────────┐
    │ Method 1: RMSE Deviation            │
    │   RMSE = √(Σ(w_i × δ_i²) / Σ(w_i)) │
    │   Score based on thresholds         │
    └─────────────────────────────────────┘
    ↓
    ┌─────────────────────────────────────┐
    │ Method 2: Hybrid (RMSE + Shape)     │
    │   Base Score = f(RMSE)              │
    │   Pearson Penalty = g(correlation)  │
    │   Final = Base - Penalty            │
    └─────────────────────────────────────┘
    ↓
    ┌─────────────────────────────────────┐
    │ Method 3: Area Difference           │
    │   Area = Σ(w × dx × |δy|)           │
    │   Trapezoidal integration           │
    │   Score based on total area         │
    └─────────────────────────────────────┘
    ↓
Assign anomaly score (0-100, higher = better)
    ↓
Display score badge next to filename:
  - 90-100: Green (Excellent)
  - 70-89: Yellow (Good)
  - <70: Red (Critical)
    ↓
Update sidebar with color-coded scores
```

**Scoring Features:**
- Wavelength-based weights (oxidation zone: 200%, fingerprint: 100%)
- Real-time score updates
- Visual heatmap of deviations
- Method comparison tooltips

---

### 3.3 Deviation Heatmap

```
Calculate deviations for selected sample
    ↓
For each X point:
    ↓
    deviation = weight × |baseline_y - sample_y|
    ↓
    (method-specific: RMSE uses δ², others use |δ|)
    ↓
Normalize to 0-1 range for color mapping
    ↓
Map to color gradient:
  - Green (0.0-0.3): Low deviation
  - Yellow (0.3-0.7): Medium deviation
  - Red (0.7-1.0): High deviation
    ↓
Render horizontal color bar below graph
    ↓
User hovers to see exact deviation value
```

---

## 🤖 Stage 4: AI Analysis Pipeline

### 4.1 Automated Graph Insights

```
User clicks "Analyze with AI" button
    ↓
Frontend gathers context:
  - Baseline filename
  - Sample filename
  - Score from current method
  - Graph data statistics (min, max, mean, std)
    ↓
POST /analysis/generate_insights
    ↓
Backend prepares prompt for Gemini AI:
  """
  Analyze this FTIR spectroscopy comparison:
  - Baseline: {baseline_name}
  - Sample: {sample_name}
  - Anomaly Score: {score}/100
  - Statistical data: {stats}
  
  Provide:
  1. Key findings
  2. Trend analysis
  3. Anomaly detection
  4. Recommendations
  """
    ↓
Send to Google Gemini API (gemini-1.5-flash)
    ↓
Gemini processes request (temperature=0.7)
    ↓
Return structured JSON:
  {
    "summary": "Overall assessment...",
    "key_findings": ["Finding 1", "Finding 2"],
    "trends": "Identified patterns...",
    "anomalies": "Detected issues...",
    "recommendations": ["Action 1", "Action 2"]
  }
    ↓
Backend returns to frontend
    ↓
Display in expandable card with sections:
  - Summary badge
  - Key findings list
  - Detailed analysis
  - Action recommendations
```

**AI Configuration:**
- Model: gemini-1.5-flash
- Temperature: 0.7 (balanced creativity)
- Max tokens: 1024
- Timeout: 30 seconds

---

### 4.2 Chatbot Interaction

```
User types question in chatbot
    ↓
Frontend captures message + conversation history
    ↓
POST /chat/send_message
  {
    "message": "What does this peak mean?",
    "conversation_history": [
      {"role": "user", "content": "Previous question"},
      {"role": "assistant", "content": "Previous answer"}
    ],
    "graph_context": {
      "baseline": "...",
      "sample": "...",
      "score": 85
    }
  }
    ↓
Backend constructs conversation with context:
    ↓
    System prompt: "You are an FTIR spectroscopy expert..."
    ↓
    Include graph context in first message
    ↓
    Append conversation history
    ↓
    Add user's new question
    ↓
Send to Gemini API with chat session
    ↓
Gemini generates contextual response
    ↓
Return response to frontend
    ↓
Display in chat bubble with:
  - User message (right-aligned, blue)
  - AI response (left-aligned, gray)
  - Timestamp
  - Markdown rendering
    ↓
Update conversation history
    ↓
Ready for next question
```

**Chat Features:**
- Context-aware responses
- Conversation memory
- Scientific terminology
- Code/formula rendering with Markdown
- Copy response button

---

## 📤 Stage 5: Export Pipeline

### 5.1 Graph Generation (Backend)

```
User clicks "Export Graphs"
    ↓
Frontend collects all samples
    ↓
POST /generate_graphs
  {
    "baseline": {x: [...], y: [...]},
    "samples": [{x: [...], y: [...]}, ...],
    "user_id": 123
  }
    ↓
Backend receives request (requires auth)
    ↓
For each sample:
    ↓
    Create matplotlib figure (10×6 inches, 300 DPI)
    ↓
    Plot baseline: plt.plot(baseline.x, baseline.y, 'b-', linewidth=2)
    ↓
    Plot sample: plt.plot(sample.x, sample.y, 'r-', linewidth=2)
    ↓
    Add labels:
      - X-axis: "Wavenumber (cm⁻¹)"
      - Y-axis: "Absorbance (A)"
      - Title: "Baseline vs {sample_name}"
    ↓
    Add legend with filenames
    ↓
    Add grid with alpha=0.3
    ↓
    Save to PNG:
      backend/static/generated_graphs/{run_id}/{sample_name}.png
    ↓
Collect all PNG paths
    ↓
Create ZIP archive:
  FTIR_export.zip
    ├── sample1_vs_baseline.png
    ├── sample2_vs_baseline.png
    └── ...
    ↓
Store metadata in MySQL `files` table:
  - user_id
  - original_filenames
  - generated_paths
  - timestamp
    ↓
Return ZIP file to frontend
```

**Export Technologies:**
- Matplotlib: Graph rendering
- Pillow: Image processing
- zipfile: Archive creation
- Python pathlib: File management

---

### 5.2 Frontend Export Handling

#### Option A: Standard Download

```
User clicks "Export" button
    ↓
Browser receives ZIP blob
    ↓
Create download link:
  <a href={blob_url} download="FTIR_export.zip">
    ↓
    Programmatic click triggers download
    ↓
    ZIP saved to Downloads folder
    ↓
    Show success notification
```

#### Option B: Folder Selection (Chromium Only)

```
User clicks "Export to Folder" button
    ↓
Check if window.showDirectoryPicker exists
    ↓
If yes (Chrome/Edge):
    ↓
    Prompt user to select folder
    ↓
    await window.showDirectoryPicker()
    ↓
    User grants write permission
    ↓
    Get file handle:
      handle = await directoryHandle.getFileHandle('FTIR_export.zip', {create: true})
    ↓
    Create writable stream
    ↓
    Write ZIP blob to stream
    ↓
    Close stream
    ↓
    Success: File written to chosen folder
    ↓
If no (Firefox/Safari):
    ↓
    Button disabled
    ↓
    Fallback to standard download
```

**Browser Support:**
- ✅ Chrome 86+
- ✅ Edge 86+
- ✅ Opera 72+
- ❌ Firefox
- ❌ Safari

---

## 🗄️ Stage 6: Database Pipeline

### 6.1 User Data Flow

```sql
-- On Signup
INSERT INTO users (email, password_hash, created_at)
VALUES (?, ?, NOW());

-- On Login
SELECT id, email, password_hash
FROM users
WHERE email = ?;

-- Session Creation
INSERT INTO sessions (session_id, user_id, expires_at)
VALUES (UUID(), ?, DATE_ADD(NOW(), INTERVAL 7 DAY));

-- Session Validation
SELECT s.user_id, u.email
FROM sessions s
JOIN users u ON s.user_id = u.id
WHERE s.session_id = ? AND s.expires_at > NOW();

-- File Tracking
INSERT INTO files (user_id, original_filenames, generated_paths, created_at)
VALUES (?, ?, ?, NOW());
```

### 6.2 Database Schema

```
┌──────────────────────────────────────┐
│            users                     │
├──────────────────────────────────────┤
│ id (PK)          INT AUTO_INCREMENT  │
│ email            VARCHAR(255) UNIQUE │
│ password_hash    VARCHAR(255)        │
│ created_at       DATETIME            │
└──────────────────────────────────────┘
                │
                │ 1:N
                ▼
┌──────────────────────────────────────┐
│          sessions                    │
├──────────────────────────────────────┤
│ id (PK)          INT AUTO_INCREMENT  │
│ session_id       VARCHAR(255) UNIQUE │
│ user_id (FK)     INT                 │
│ expires_at       DATETIME            │
│ created_at       DATETIME            │
└──────────────────────────────────────┘

                │
                │ 1:N
                ▼
┌──────────────────────────────────────┐
│            files                     │
├──────────────────────────────────────┤
│ id (PK)              INT             │
│ user_id (FK)         INT             │
│ original_filenames   TEXT            │
│ generated_paths      TEXT            │
│ created_at           DATETIME        │
└──────────────────────────────────────┘
```

---

## 🚀 Deployment Pipeline (Docker)

### Build Process

```bash
# 1. Build Docker images
docker compose build
    ↓
    ┌─────────────────────────────────┐
    │  Frontend (Node Alpine)         │
    │  - npm install dependencies     │
    │  - npm run build (Vite)         │
    │  - Serve with nginx:1.25-alpine │
    └─────────────────────────────────┘
    ↓
    ┌─────────────────────────────────┐
    │  Backend (Python 3.11 Slim)     │
    │  - pip install requirements     │
    │  - uvicorn FastAPI server       │
    └─────────────────────────────────┘

# 2. Start containers
docker compose up
    ↓
    Frontend container: Port 5173
    Backend container: Port 8080
    MySQL container: Port 3306 (internal)
    ↓
    Network bridge connects all services
    ↓
    Volume mounts:
      - ./backend/static → /app/static (persistent graphs)
      - mysql-data → /var/lib/mysql (persistent DB)
```

### Container Communication

```
┌─────────────────────────────────────────┐
│  Docker Network: mrg-labs-network       │
│                                         │
│  ┌───────────────┐                     │
│  │  Frontend     │                     │
│  │  nginx:5173   │                     │
│  └───────┬───────┘                     │
│          │ HTTP proxy                  │
│          ▼                              │
│  ┌───────────────┐     ┌────────────┐  │
│  │  Backend      │────▶│   MySQL    │  │
│  │  uvicorn:8080 │     │   :3306    │  │
│  └───────┬───────┘     └────────────┘  │
│          │                              │
│          ▼                              │
│  ┌───────────────┐                     │
│  │ Google Gemini │ (external API)      │
│  │     AI        │                     │
│  └───────────────┘                     │
└─────────────────────────────────────────┘
```

---

## 🔄 Complete End-to-End Example

### Scenario: New User Analyzes FTIR Data

```
1. USER REGISTRATION
   ├─ Navigate to /signup
   ├─ Enter: email@example.com, password123
   ├─ Frontend: POST /register
   ├─ Backend: Hash password, insert to MySQL
   ├─ Backend: Create session, set cookie
   └─ Frontend: Redirect to /dashboard

2. FILE UPLOAD
   ├─ Click "Upload Baseline"
   ├─ Select baseline.csv (3451 data points)
   ├─ Papa Parse: Convert to {x: [...], y: [...]}
   ├─ Validate: All numeric, sufficient points ✓
   ├─ Display: "baseline.csv uploaded"
   ├─ Click "Upload Samples"
   ├─ Select sample1.csv, sample2.csv, sample3.csv
   ├─ Parse and validate all samples ✓
   └─ Display: 3 samples in sidebar

3. INTERACTIVE VISUALIZATION
   ├─ Click sample1.csv in sidebar
   ├─ React: useEffect triggers chart update
   ├─ Chart.js: Render baseline (blue) + sample1 (red)
   ├─ Calculate FTIR scores:
   │   ├─ Hybrid method selected
   │   ├─ RMSE = 0.15 → Base Score = 78
   │   ├─ Pearson r = 0.97 → No penalty
   │   └─ Final Score = 78 (Yellow badge)
   ├─ Render deviation heatmap (mostly green, some yellow)
   ├─ User: Zoom into 1700-1750 cm⁻¹ (oxidation zone)
   └─ User: Toggle grid, adjust view

4. AI ANALYSIS
   ├─ Click "Analyze with AI"
   ├─ Frontend: POST /analysis/generate_insights
   ├─ Backend: Construct prompt with graph context
   ├─ Gemini API: Process analysis (3 seconds)
   ├─ Return: {
   │     summary: "Moderate oxidation detected",
   │     key_findings: ["Peak at 1720 cm⁻¹", "Score: 78/100"],
   │     recommendations: ["Monitor sample", "Consider relubrication"]
   │   }
   └─ Display: Expandable insight card with findings

5. CHATBOT INTERACTION
   ├─ Open chatbot sidebar
   ├─ User types: "What does the peak at 1720 mean?"
   ├─ Frontend: POST /chat/send_message + graph context
   ├─ Backend: Send to Gemini with conversation history
   ├─ Gemini: Generate contextual response
   ├─ Response: "The peak at 1720 cm⁻¹ indicates carbonyl..."
   ├─ Display: Chat bubble with markdown
   ├─ User asks follow-up: "Is this critical?"
   └─ AI responds with context-aware answer

6. EXPORT GRAPHS
   ├─ Click "Export Graphs"
   ├─ Frontend: POST /generate_graphs with all samples
   ├─ Backend: Generate 3 PNG graphs with matplotlib
   │   ├─ sample1_vs_baseline.png
   │   ├─ sample2_vs_baseline.png
   │   └─ sample3_vs_baseline.png
   ├─ Backend: Create FTIR_export.zip
   ├─ Backend: Store metadata in MySQL files table
   ├─ User clicks "Export to Folder" (Chrome)
   ├─ Browser: showDirectoryPicker() → User selects Desktop
   ├─ Write ZIP to Desktop/FTIR_export.zip
   └─ Success notification: "Exported 3 graphs to Desktop"

7. LOGOUT
   ├─ Click profile menu → Logout
   ├─ Frontend: POST /logout
   ├─ Backend: Delete session from database
   ├─ Backend: Clear session cookie
   ├─ Frontend: Clear AuthContext
   └─ Redirect to /login
```

---

## 🛠️ Technology Stack Summary

### Frontend Pipeline

| Stage | Technology | Purpose |
|-------|------------|---------|
| UI Framework | React 18 + TypeScript | Component-based architecture |
| Routing | React Router v6 | SPA navigation |
| State Management | React Context API | Global auth state |
| UI Components | Chakra UI | Accessible, themed components |
| Charting | Chart.js + react-chartjs-2 | Interactive graphs |
| CSV Parsing | Papa Parse | Fast CSV processing |
| File System | File System Access API | Custom folder exports |
| Build Tool | Vite | Fast HMR, optimized builds |
| HTTP Client | Fetch API | REST communication |

### Backend Pipeline

| Stage | Technology | Purpose |
|-------|------------|---------|
| API Framework | FastAPI | High-performance Python API |
| Auth | bcrypt | Password hashing |
| Session Management | MySQL + UUID | Secure session storage |
| Database | MySQL 8.0 | User & file data |
| Graph Generation | Matplotlib + Pandas | Scientific visualization |
| Image Processing | Pillow | PNG optimization |
| AI Integration | Google Gemini API | Analysis & chat |
| ASGI Server | uvicorn | Production server |
| CORS | FastAPI middleware | Cross-origin requests |

### DevOps Pipeline

| Stage | Technology | Purpose |
|-------|------------|---------|
| Containerization | Docker | Isolated environments |
| Orchestration | docker-compose | Multi-container management |
| Frontend Server | nginx | Static file serving |
| Reverse Proxy | nginx | API routing |
| Volume Management | Docker volumes | Persistent storage |

---

## 📈 Performance Metrics

### Pipeline Benchmarks

| Operation | Time | Notes |
|-----------|------|-------|
| CSV Parse (3451 points) | ~50ms | Papa Parse |
| Chart Render | ~100ms | Chart.js initial |
| Chart Update | ~16ms | 60 FPS target |
| AI Analysis | 2-5s | Gemini API latency |
| Chat Response | 1-3s | Depends on context |
| Graph Export (PNG) | ~200ms/graph | Matplotlib |
| ZIP Creation (10 graphs) | ~1s | Python zipfile |
| Database Query | <10ms | Indexed lookups |
| Login/Signup | ~150ms | bcrypt hashing |

---

## 🔒 Security Pipeline

### Authentication Flow

```
1. Password Input
   ↓
2. Frontend validation (length, complexity)
   ↓
3. HTTPS transmission
   ↓
4. Backend receives plaintext password
   ↓
5. bcrypt.hashpw(password, bcrypt.gensalt(12))
   ↓
6. Store hash (never plaintext)
   ↓
7. Generate UUID session_id
   ↓
8. Store in sessions table with expiration
   ↓
9. Set httpOnly, secure cookie
   ↓
10. Frontend receives auth state (no password)
```

### Request Authorization

```
Every protected API call:
    ↓
    Include session cookie
    ↓
    @require_auth decorator validates:
      ├─ Cookie exists?
      ├─ Session in database?
      ├─ Session expired?
      └─ User still exists?
    ↓
    If all checks pass: Proceed
    ↓
    If any fails: 401 Unauthorized
```

---

## 📦 Deliverables Pipeline

### Development → Production

```
1. LOCAL DEVELOPMENT
   ├─ npm run dev (Frontend: Vite dev server)
   ├─ uvicorn --reload (Backend: Hot reload)
   └─ MySQL local instance

2. TESTING
   ├─ Frontend: Vitest unit tests
   ├─ Backend: pytest integration tests
   └─ Manual QA testing

3. BUILD
   ├─ npm run build (Frontend: Optimized bundle)
   ├─ Docker build (Multi-stage builds)
   └─ Image optimization

4. DEPLOYMENT
   ├─ docker-compose up -d (Production mode)
   ├─ nginx serves static files
   ├─ uvicorn workers: 4 processes
   └─ MySQL persistent volumes

5. MONITORING
   ├─ Application logs
   ├─ Error tracking
   └─ Performance metrics
```

---

## 🎯 Future Pipeline Enhancements

### Planned Features

1. **Real-time Collaboration**
   ```
   User A uploads graphs
       ↓
   WebSocket broadcast to team
       ↓
   User B sees live updates
       ↓
   Collaborative annotations
   ```

2. **Batch Processing**
   ```
   Upload 100 samples
       ↓
   Queue processing jobs
       ↓
   Background worker pool
       ↓
   Progress notifications
       ↓
   Email when complete
   ```

3. **Advanced Analytics**
   ```
   Historical data trends
       ↓
   Predictive modeling with ML
       ↓
   Anomaly detection alerts
       ↓
   Automated reporting
   ```

4. **Cloud Storage**
   ```
   Export to cloud providers
       ↓
   AWS S3 / Google Cloud Storage
       ↓
   Shareable links
       ↓
   Long-term archival
   ```

---

## 📚 Related Documentation

- **[README.md](README.md)** - Project overview
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - API endpoints
- **[AUTH_DOCUMENTATION.md](AUTH_DOCUMENTATION.md)** - Authentication details
- **[FTIR_SCORING_METHODOLOGY.md](FTIR_SCORING_METHODOLOGY.md)** - Scoring algorithms
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Installation instructions

---

**Last Updated:** December 1, 2025  
**Version:** 1.0  
**Maintained by:** MRG Labs Development Team
