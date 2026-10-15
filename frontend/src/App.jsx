import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { PropertyProvider } from './context/PropertyContext.jsx';
import PropertyList from './pages/PropertyList.jsx';
import PropertyDetail from './pages/PropertyDetail.jsx';

function App() {
  return (
    <Router>
      <PropertyProvider>
        <Routes>
          <Route path="/" element={<PropertyList />} />
          <Route path="/property/:id" element={<PropertyDetail />} />
        </Routes>
      </PropertyProvider>
    </Router>
  );
}

export default App;
