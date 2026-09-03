# MRG Labs Graphing App

Full-stack web application for the 2025 Schneider Prize challenge. Upload a single baseline CSV and multiple sample CSVs, preview overlay graphs in the browser, and batch-export all sample-vs-baseline plots as PNG images.

## ✨ New Features

🔐 **User Authentication** - Secure signup/login with session management  
🤖 **AI-Powered Analysis** - Get intelligent insights about your graph data using Google Gemini AI  
💬 **AI Chat Assistant** - Ask questions and get help analyzing your data in real-time  
📊 **Advanced Graph Visualization** - Interactive charts with zoom, pan, and custom scaling  
👤 **User Profiles** - Personal workspaces with saved graphs and analysis history

## Tech Stack

### Frontend

- **React** + **Vite** + **TypeScript** - Modern, fast development
- **Chakra UI** - Beautiful, accessible UI components
- **React Router** - Client-side routing and navigation
- **Chart.js** (react-chartjs-2) - Interactive graph visualization
- **Papa Parse** - CSV parsing and data processing

### Backend

- **FastAPI** - High-performance Python API framework
- **Google Gemini AI** - Advanced AI-powered analysis and chat
- **MySQL** - User data and session management
- **Pandas** + **Matplotlib** - Data processing and graph generation
- **bcrypt** - Secure password hashing

### Infrastructure

- **Docker** + **docker-compose** - Containerized deployment
- **Session-based auth** - Secure user authentication

## Features

### Core Functionality

- ✅ Baseline CSV (single) + multiple sample CSV uploads
- ✅ Real-time interactive preview of baseline vs selected sample
- ✅ Advanced zoom and pan controls with reset functionality
- ✅ Custom X-axis scaling for spectroscopy data
- ✅ Batch export: generates and saves PNG graphs
- ✅ **Folder Export (Chromium only)**: Choose custom export folder using File System Access API
- ✅ Dynamic legend with filename display
- ✅ Professional axes labeling (A for Y-axis, cm⁻¹ for X-axis)

### AI-Powered Features

- 🤖 **Automated Graph Analysis** - Statistical comparisons and pattern recognition
- 💡 **AI Insights** - Trend identification, anomaly detection, scientific interpretation
- 💬 **Interactive Chatbot** - Context-aware AI assistant for data analysis questions
- 📈 **Smart Recommendations** - Data quality assessment and suggestions

### User Management

- 🔐 **Secure Authentication** - User registration and login with bcrypt hashing
- 👤 **User Profiles** - Personalized dashboards and settings
- 📁 **File Management** - Track and manage your uploaded graphs
- 🔒 **Session Management** - Secure session-based authentication
- 🚪 **Easy Logout** - One-click logout from any page

## Project Structure

```
mrg-labs-graphing-app/
  frontend/
    src/
      components/
      pages/
  backend/
    utils/plotter.py
    static/generated_graphs/
```

## 🚀 Quick Start

### Prerequisites

- Node.js (v16+)
- Python (3.8+)
- MySQL (8.0+)

### 1. Database Setup

```bash
mysql -u root -p < backend/database_setup.sql
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DB_HOST=localhost
DB_USER=root
DB_PASS=your_password
DB_NAME=mrg_labs_db
SESSION_SECRET=$(openssl rand -hex 32)
GEMINI_API_KEY=your_gemini_key
EOF

# Start backend
python -m uvicorn app:app --reload --port 8080
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 4. Access Application

Open browser to **http://localhost:5173**

**First time?** Click "Sign Up" to create an account!

## 📖 Documentation

- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete setup instructions
- **[AUTH_DOCUMENTATION.md](AUTH_DOCUMENTATION.md)** - Authentication system details
- **[backend/API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md)** - API endpoints and AI features
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick command reference
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - What was implemented

## 🔑 API Endpoints

### Authentication

- `POST /register` - Create new user account
- `POST /login` - Login user (creates session)
- `POST /logout` - Logout user (clears session)
- `POST /change_password` - Change the authenticated user's password

### Graph Operations

- `POST /generate_graphs` - Generate and export graphs (requires auth)
- `GET /api/v1/files` - Get user's generated files (requires auth)
- `GET /health` - Check backend health

### AI Services

- `POST /analysis/generate_insights` - Get AI analysis of graph comparison
- `GET /analysis/health` - Check analysis service status
- `POST /chat/send_message` - Send message to AI chatbot
- `POST /chat/quick_question` - Ask quick question without conversation
- `GET /chat/conversation/{conversation_id}` - Retrieve a conversation
- `DELETE /chat/conversation/{conversation_id}` - Clear a conversation
- `GET /chat/health` - Check chat service status

## 🐳 Docker Deployment

```bash
docker compose build
docker compose up
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8080

## 📊 Usage Example

1. **Sign Up/Login** - Create account or sign in
2. **Upload Baseline** - Select your baseline CSV file
3. **Upload Samples** - Select one or more sample CSV files
4. **View Graph** - Interactive graph with zoom/pan controls
5. **Get AI Analysis** - Automatic analysis with insights
6. **Chat with AI** - Ask questions about your data
7. **Export Graphs** - Download generated PNG images
   - **Standard Export**: Downloads ZIP to default Downloads folder
   - **Folder Export** (Chromium only): Choose custom export location

## 📁 Folder Export Feature

The application now supports custom folder selection for exports using the **File System Access API**:

### Browser Compatibility

✅ **Supported Browsers:**
- Chrome 86+
- Edge 86+
- Opera 72+
- Brave (Chromium-based)

❌ **Not Supported:**
- Firefox
- Safari
- Internet Explorer

### How It Works

1. Click **"Export Graphs"** button in the export dialog
2. Browser will prompt you to select a destination folder
3. Grant write permissions when prompted
4. File `FTIR_export.zip` will be created/overwritten in your chosen folder
5. Success notification appears when complete

### Fallback Behavior

- If folder selection is not supported, the button will be disabled
- Standard "Export" button provides traditional download to Downloads folder
- If folder selection fails or is cancelled, app falls back to standard download

### Security Notes

- Browser will always prompt for user permission before writing files
- Each folder selection requires explicit user approval
- Files can only be written to user-selected folders, not arbitrary system locations
- Works in containerized Docker localhost environments

## 🔒 Security Features

- ✅ Password hashing with bcrypt
- ✅ Session-based authentication
- ✅ SQL injection prevention
- ✅ CORS configuration
- ✅ Protected API routes
- ✅ Input validation

## 🛠️ Development

### Project Structure

```
mrg-labs-graphing-app/
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── pages/         # Login, Signup, Dashboard
│   │   ├── components/    # Reusable UI components
│   │   ├── services/      # API calls (auth, etc.)
│   │   └── contexts/      # React contexts (AuthContext)
├── backend/               # FastAPI backend
│   ├── app.py            # Main API application
│   ├── chatbox.py        # AI chat service
│   ├── graph_analysis.py # AI analysis service
│   └── utils/            # Helper functions
└── docs/                 # Documentation
```

### Running Tests

```bash
# Backend tests (if implemented)
cd backend
pytest

# Frontend tests (if implemented)
cd frontend
npm test
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

Proprietary - MRG Labs (adjust as needed)

## 🙏 Acknowledgments

- Google Gemini AI for intelligent analysis
- Chakra UI for beautiful components
- FastAPI for excellent Python framework
- Chart.js for powerful visualizations

## 📬 Support

For issues and questions:

1. Check the documentation in `/docs` folder
2. Review the setup guide
3. Check existing issues on GitHub
4. Create a new issue with details

---

**Made with ❤️ for the 2025 Schneider Prize Challenge**
