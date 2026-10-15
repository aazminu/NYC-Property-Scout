import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProperty } from '../context/PropertyContext.jsx';

const PropertyList = () => {
  const navigate = useNavigate();
  const {
    properties,
    loading,
    error,
    filters,
    updateFilters,
    nextPage,
    prevPage,
    resetFilters,
    currentPage,
    hasNextPage,
    hasPrevPage,
  } = useProperty();

  const [localFilters, setLocalFilters] = useState({
    minPrice: '',
    maxPrice: '',
    beds: '',
    borough: '',
  });

  const [searchQuery, setSearchQuery] = useState('');

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setLocalFilters({ ...localFilters, [name]: value });
  };

  const handleSearch = (e) => {
    if (e.key === 'Enter' || e.type === 'click') {
      // Filter properties by search query
      const filtered = properties.filter(property => {
        const query = searchQuery.toLowerCase();
        return (
          property.address?.toLowerCase().includes(query) ||
          property.borough_name?.toLowerCase().includes(query) ||
          property.building_name?.toLowerCase().includes(query) ||
          property.BBL?.includes(searchQuery)
        );
      });
      // You could update context or local state here
      console.log('Search results:', filtered);
    }
  };

  const applyFilters = () => {
    updateFilters({
      minPrice: localFilters.minPrice ? parseInt(localFilters.minPrice) : null,
      maxPrice: localFilters.maxPrice ? parseInt(localFilters.maxPrice) : null,
      beds: localFilters.beds ? parseInt(localFilters.beds) : null,
      borough: localFilters.borough || null,
    });
  };

  const handleReset = () => {
    setLocalFilters({ minPrice: '', maxPrice: '', beds: '', borough: '' });
    resetFilters();
  };

  const formatPrice = (price) => {
    if (!price || price === 'N/A') return 'Contact for price';
    return `$${parseInt(price).toLocaleString()}/mo`;
  };

  const getBorough = (address) => {
    if (!address) return 'Unknown';
    const lower = address.toLowerCase();
    if (lower.includes('brooklyn')) return 'Brooklyn';
    if (lower.includes('manhattan')) return 'Manhattan';
    if (lower.includes('queens')) return 'Queens';
    if (lower.includes('bronx')) return 'Bronx';
    if (lower.includes('staten island')) return 'Staten Island';
    return 'NYC';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header with Search */}
      <header className="bg-gradient-to-r from-blue-600 to-indigo-700 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold text-white">NYC Property Scout</h1>
              <p className="mt-1 text-blue-100">AI-powered transparency for NYC rentals</p>
            </div>
            <div className="flex items-center gap-2 text-blue-100 text-sm">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-medium">Watson AI Verified</span>
            </div>
          </div>
          
          {/* Search Bar */}
          <div className="relative max-w-2xl">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleSearch}
              placeholder="Search by address, neighborhood, or zip code..."
              className="w-full px-5 py-4 pr-12 rounded-lg text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-300 shadow-lg"
            />
            <button 
              onClick={handleSearch}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Filter & Sort</h2>
            {(localFilters.minPrice || localFilters.maxPrice || localFilters.beds || localFilters.borough) && (
              <button
                onClick={handleReset}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                Clear all
              </button>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <input
              type="number"
              name="minPrice"
              placeholder="Min Price"
              value={localFilters.minPrice}
              onChange={handleFilterChange}
              className="px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
            <input
              type="number"
              name="maxPrice"
              placeholder="Max Price"
              value={localFilters.maxPrice}
              onChange={handleFilterChange}
              className="px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
            <select
              name="beds"
              value={localFilters.beds}
              onChange={handleFilterChange}
              className="px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            >
              <option value="">Any Beds</option>
              <option value="0">Studio</option>
              <option value="1">1 Bed</option>
              <option value="2">2 Beds</option>
              <option value="3">3 Beds</option>
              <option value="4">4+ Beds</option>
            </select>
            <select
              name="borough"
              value={localFilters.borough}
              onChange={handleFilterChange}
              className="px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            >
              <option value="">All Boroughs</option>
              <option value="Brooklyn">Brooklyn</option>
              <option value="Manhattan">Manhattan</option>
              <option value="Queens">Queens</option>
              <option value="Bronx">Bronx</option>
              <option value="Staten Island">Staten Island</option>
            </select>
            <button
              onClick={applyFilters}
              className="bg-blue-600 text-white px-6 py-2.5 rounded-lg hover:bg-blue-700 transition font-medium text-sm"
            >
              Apply Filters
            </button>
          </div>
        </div>

        {/* Results Count & Sort */}
        {!loading && !error && Array.isArray(properties) && properties.length > 0 && (
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-gray-600">
              <span className="font-semibold text-gray-900">{properties.length}</span> homes available
            </p>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Sort:</span>
              <select className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                <option>Newest</option>
                <option>Price (Low to High)</option>
                <option>Price (High to Low)</option>
                <option>Beds</option>
              </select>
            </div>
          </div>
        )}

        {/* Loading State with Skeletons */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <div key={n} className="bg-white rounded-lg shadow-sm overflow-hidden animate-pulse">
                <div className="h-48 bg-gray-200"></div>
                <div className="p-4 space-y-3">
                  <div className="h-6 bg-gray-200 rounded w-1/2"></div>
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800">Error: {error}</p>
          </div>
        )}

        {/* Properties Grid */}
        {!loading && !error && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
              {Array.isArray(properties) && properties.map((property) => (
                <div
                  key={property.zpid}
                  className="group bg-white rounded-lg shadow-sm hover:shadow-xl transition-all duration-300 cursor-pointer overflow-hidden border border-gray-100 hover:border-blue-200"
                >
                  {/* Image with Overlay */}
                  <div className="relative h-48 bg-gray-200 overflow-hidden">
                    {property.image_url ? (
                      <img 
                        src={property.image_url} 
                        alt={property.address}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        onError={(e) => {
                          e.target.style.display = 'none';
                          e.target.nextSibling.style.display = 'flex';
                        }}
                      />
                    ) : null}
                    <div 
                      className="absolute inset-0 flex items-center justify-center text-white group-hover:scale-105 transition-transform duration-300 bg-gradient-to-br from-blue-400 to-blue-600"
                      style={{ display: property.image_url ? 'none' : 'flex' }}
                    >
                      <div className="text-center p-4">
                        <svg className="w-16 h-16 mx-auto mb-2 opacity-75" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                        <p className="text-sm font-medium">{property.property_type}</p>
                      </div>
                    </div>
                    
                    {/* Favorite Button */}
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        // Add favorite logic here
                      }}
                      className="absolute top-3 right-3 w-9 h-9 bg-white/90 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-white transition-all shadow-lg"
                    >
                      <svg className="w-5 h-5 text-gray-600 hover:text-red-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                      </svg>
                    </button>
                    
                    {/* AI Badge */}
                    <div className="absolute bottom-3 left-3 bg-blue-600 text-white text-xs font-semibold px-2.5 py-1 rounded-full flex items-center gap-1 shadow-lg">
                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                        <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                      </svg>
                      AI Scout
                    </div>
                  </div>

                  {/* Property Info */}
                  <div 
                    className="p-4"
                    onClick={() => navigate(`/property/${property.zpid}`)}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="text-xl font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                        {formatPrice(property.price)}
                      </h3>
                      <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded">
                        {getBorough(property.address)}
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                      {property.address}
                    </p>

                    <div className="flex items-center gap-4 text-sm text-gray-700">
                      {property.beds !== 'N/A' && property.beds !== null && (
                        <span className="flex items-center gap-1">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                          </svg>
                          {property.beds} bd
                        </span>
                      )}
                      {property.baths !== 'N/A' && property.baths !== null && (
                        <span className="flex items-center gap-1">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z" />
                          </svg>
                          {property.baths} ba
                        </span>
                      )}
                      {property.sqft !== 'N/A' && property.sqft !== null && (
                        <span className="flex items-center gap-1">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                          </svg>
                          {property.sqft} sqft
                        </span>
                      )}
                    </div>

                    <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                        </svg>
                        Updated recently
                      </span>
                      <span className="text-blue-600 font-medium group-hover:underline">
                        See transparency →
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {Array.isArray(properties) && properties.length > 0 && (
              <div className="flex justify-center items-center gap-2 py-8">
                <button
                  onClick={prevPage}
                  disabled={!hasPrevPage}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all ${
                    hasPrevPage
                      ? 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400 shadow-sm'
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200'
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Previous
                </button>
                
                <div className="flex items-center gap-1">
                  <div className="px-4 py-2.5 bg-blue-600 text-white rounded-lg font-semibold shadow-sm">
                    {currentPage}
                  </div>
                </div>
                
                <button
                  onClick={nextPage}
                  disabled={!hasNextPage}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all ${
                    hasNextPage
                      ? 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400 shadow-sm'
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200'
                  }`}
                >
                  Next
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            )}

            {/* No Results */}
            {Array.isArray(properties) && properties.length === 0 && !loading && (
              <div className="text-center py-12">
                <svg className="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                </svg>
                <p className="text-gray-600 text-lg">No properties found</p>
                <p className="text-gray-500 text-sm mt-2">Try adjusting your filters</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default PropertyList;
