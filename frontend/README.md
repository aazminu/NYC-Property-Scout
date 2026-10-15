# NYC Rent Frontend

React frontend for NYC Property Scout with Watson AI transparency reports.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Make sure the backend is running on `http://localhost:8000`

3. Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Features

- **Property Listings**: Browse NYC rental properties with filters (price, bedrooms, borough)
- **Pagination**: Navigate through property results
- **Property Details**: View detailed information about each property
- **AI Transparency Reports**: Automatic Watson analysis with quality and financial scores
- **Responsive Design**: Built with Tailwind CSS for mobile and desktop

## Project Structure

```
src/
├── components/
│   └── ScoreCard.js          # Watson AI score display
├── context/
│   └── PropertyContext.js    # Global state management
├── pages/
│   ├── PropertyList.js       # Browse properties page
│   └── PropertyDetail.js     # Individual property page
├── services/
│   └── api.js               # API calls to backend
├── App.js                   # React Router setup
├── main.jsx                 # Entry point
└── index.css                # Tailwind CSS
```

## API Endpoints Used

- `GET /api/properties` - Fetch properties with filters
- `GET /api/properties/:id` - Get single property
- `GET /api/chat/stream` - Stream Watson analysis (SSE)
