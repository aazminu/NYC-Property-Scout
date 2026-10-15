# NYC Property Scout

An AI-powered property transparency tool for NYC renters, built for the WatsonX Hackathon.

📄 **[NYC Property Scout.pdf](NYC%20Property%20Scout.pdf)** - Our presentation for the WatsonX Hackathon

## Features

- 🤖 **AI Transparency Reports**: Watson-powered analysis of property quality and financial data
- 🏢 **NYC Open Data Integration**: 311 complaints, DOB violations, DOF tax records
- 💬 **Interactive Chat**: Ask follow-up questions about any property
- ⚡ **Smart Caching**: 24-hour local cache for instant report loading
- 🎨 **Modern UI**: Zillow-inspired design with real property images

## Tech Stack

- **Frontend**: React 18, Vite, Tailwind CSS, React Router
- **Backend**: FastAPI, Python 3.11+
- **AI**: IBM WatsonX Orchestrate
- **Data**: NYC Open Data APIs, Zillow listings

## Quick Start

### Prerequisites

- Node.js 18+ and pnpm
- Python 3.11+
- IBM WatsonX API credentials

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export WATSONX_API_KEY="your-api-key"
export WATSONX_PROJECT_ID="your-project-id"

# Start the server
uvicorn main:app --reload
```

The backend runs at http://localhost:8000

### Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Start dev server
pnpm run dev
```

The frontend runs at http://localhost:5173

## Project Structure

```
NYC-Rent-Web-Scrapper/
├── backend/
│   ├── main.py              # FastAPI application
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   │   ├── ScoreCard.jsx    # AI Transparency Report display
│   │   │   └── WatsonChat.jsx   # Chat interface
│   │   ├── pages/
│   │   │   ├── PropertyList.jsx # Home page with listings
│   │   │   └── PropertyDetail.jsx # Property details + AI analysis
│   │   ├── context/         # React Context for state
│   │   └── services/        # API integration
│   └── package.json
├── data/                    # Property listings data
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/properties` | GET | List properties with pagination/filters |
| `/api/properties/{id}` | GET | Get single property by ID |
| `/api/chat/stream` | POST | Stream Watson AI analysis (SSE) |

## Environment Variables

### Backend
| Variable | Description |
|----------|-------------|
| `WATSONX_API_KEY` | IBM WatsonX API key |
| `WATSONX_PROJECT_ID` | WatsonX project ID |
| `WATSONX_AGENT_ID` | WatsonX Orchestrate agent ID |

## License

MIT