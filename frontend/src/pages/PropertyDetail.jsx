import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getPropertyById, streamWatsonAnalysis } from '../services/api';
import ScoreCard from '../components/ScoreCard.jsx';
import WatsonChat from '../components/WatsonChat.jsx';

// Cache duration: 24 hours in milliseconds
const CACHE_DURATION = 24 * 60 * 60 * 1000;

// Cache helper functions
const getCachedReport = (propertyId) => {
  try {
    const cached = localStorage.getItem(`watson_report_${propertyId}`);
    if (!cached) return null;
    
    const { data, threadId, timestamp } = JSON.parse(cached);
    const age = Date.now() - timestamp;
    
    // Check if cache is still valid
    if (age < CACHE_DURATION) {
      console.log(`Cache hit for property ${propertyId} (age: ${Math.round(age / 60000)} mins)`);
      return { data, threadId };
    }
    
    // Cache expired, remove it
    console.log(`Cache expired for property ${propertyId}`);
    localStorage.removeItem(`watson_report_${propertyId}`);
    return null;
  } catch (e) {
    console.error('Error reading cache:', e);
    return null;
  }
};

const setCachedReport = (propertyId, data, threadId) => {
  try {
    const cacheEntry = {
      data,
      threadId,
      timestamp: Date.now()
    };
    localStorage.setItem(`watson_report_${propertyId}`, JSON.stringify(cacheEntry));
    console.log(`Cached report for property ${propertyId} with threadId ${threadId}`);
  } catch (e) {
    console.error('Error writing cache:', e);
    // If localStorage is full, try to clear old entries
    if (e.name === 'QuotaExceededError') {
      clearOldCacheEntries();
    }
  }
};

const clearOldCacheEntries = () => {
  const keys = Object.keys(localStorage).filter(k => k.startsWith('watson_report_'));
  // Remove oldest half of entries
  keys.slice(0, Math.floor(keys.length / 2)).forEach(k => localStorage.removeItem(k));
};

const PropertyDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [property, setProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [watsonResponse, setWatsonResponse] = useState('');
  const [watsonLoading, setWatsonLoading] = useState(false);
  const [watsonError, setWatsonError] = useState(null);
  const [watsonStatus, setWatsonStatus] = useState('');
  const [threadId, setThreadId] = useState(null);
  const [fromCache, setFromCache] = useState(false);
  
  // Ref to store latest response for caching when onComplete fires
  const latestResponseRef = useRef('');

  useEffect(() => {
    fetchProperty();
  }, [id]);

  const fetchProperty = async () => {
    try {
      setLoading(true);
      const data = await getPropertyById(id);
      setProperty(data);
      setError(null);
      
      // Auto-trigger Watson analysis after property loads
      if (data && data.address) {
        triggerWatsonAnalysis(data.address, id);
      }
    } catch (err) {
      setError(err.message || 'Failed to load property');
      console.error('Error fetching property:', err);
    } finally {
      setLoading(false);
    }
  };

  const triggerWatsonAnalysis = (address, propertyId) => {
    // Check cache first
    const cached = getCachedReport(propertyId);
    if (cached) {
      setWatsonResponse(cached.data);
      setThreadId(cached.threadId); // Restore cached threadId for chat continuity
      setWatsonLoading(false);
      setWatsonStatus('Loaded from cache');
      setFromCache(true);
      return;
    }
    
    setFromCache(false);
    setWatsonLoading(true);
    setWatsonError(null);
    setWatsonResponse('');
    setWatsonStatus('Connecting to Watson...');

    const message = `${address}`;
    
    // Store propertyId in closure for caching
    const currentPropertyId = propertyId;
    
    const cleanup = streamWatsonAnalysis(
      message,
      null, // Don't pass thread_id for initial analysis - each property gets fresh analysis
      (message) => {
        // Check if message is a complete JSON object - if so, replace instead of append
        try {
          const parsed = JSON.parse(message);
          console.log('Received Watson message:', parsed);
          
          // Check if this is a complete report with scores
          if (parsed.scores) {
            const hasOverall = parsed.scores.overall_transparency_grade !== undefined || 
                               parsed.scores.overall_grade !== undefined ||
                               parsed.scores.overall !== undefined;
            const hasQuality = parsed.scores.quality_score !== undefined ||
                               parsed.scores.quality !== undefined;
            
            // If we have overall OR quality score, treat as complete report
            if (hasOverall || hasQuality) {
              console.log('Complete report received, updating state');
              latestResponseRef.current = message; // Store for caching
              setWatsonResponse(message);
              return;
            }
          }
          
          // If it's ONLY property data without any scores, ignore it
          if (parsed.property && !parsed.scores) {
            console.log('Received property data only, waiting for analysis...');
            return;
          }
          
          // For any other JSON structure, use it
          latestResponseRef.current = message;
          setWatsonResponse(message);
        } catch (e) {
          // Not JSON, treat as incremental text
          // Append text messages for markdown/incremental responses
          // Prevent duplicates by checking if message already exists
          setWatsonResponse((prev) => {
            const newVal = prev.includes(message) ? prev : prev + message;
            latestResponseRef.current = newVal;
            return newVal;
          });
        }
      },
      (status) => {
        setWatsonStatus(status);
      },
      (error) => {
        setWatsonError(error);
        setWatsonLoading(false);
      },
      (newThreadId) => {
        setWatsonLoading(false);
        setWatsonStatus('Analysis complete');
        setThreadId(newThreadId); // Save thread_id for future messages
        console.log('Watson analysis completed. Thread ID:', newThreadId);
        
        // Cache the report with threadId when complete
        if (latestResponseRef.current) {
          setCachedReport(currentPropertyId, latestResponseRef.current, newThreadId);
        }
      }
    );

    // Cleanup on unmount
    return cleanup;
  };

  const formatPrice = (price) => {
    if (!price || price === 'N/A') return 'Contact for price';
    return `$${parseInt(price).toLocaleString()}/month`;
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading property...</p>
        </div>
      </div>
    );
  }

  if (error || !property) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <svg className="w-16 h-16 mx-auto text-red-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p className="text-red-800 text-lg mb-4">{error || 'Property not found'}</p>
          <button
            onClick={() => navigate('/')}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition"
          >
            Back to Listings
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-blue-600 to-indigo-700 shadow-lg sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-2 text-white hover:text-blue-100 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="font-medium">Back to Search</span>
            </button>
            <div className="flex items-center gap-3">
              <button className="flex items-center gap-2 bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg transition-colors backdrop-blur-sm">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                </svg>
                <span className="text-sm font-medium">Share</span>
              </button>
              <button className="flex items-center gap-2 bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg transition-colors backdrop-blur-sm">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
                <span className="text-sm font-medium">Save</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Property Details */}
          <div className="lg:col-span-2 space-y-6">
            {/* Hero Image */}
            <div className="bg-white rounded-xl shadow-xl overflow-hidden">
              <div className="relative h-96 bg-gray-200">
                {property.image_url ? (
                  <img 
                    src={property.image_url} 
                    alt={property.address}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      e.target.style.display = 'none';
                      e.target.nextSibling.style.display = 'flex';
                    }}
                  />
                ) : null}
                <div 
                  className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-blue-500 to-indigo-600"
                  style={{ display: property.image_url ? 'none' : 'flex' }}
                >
                  <div className="text-white text-center p-6">
                    <svg className="w-32 h-32 mx-auto mb-4 opacity-75" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                    <p className="text-xl font-semibold">{property.property_type}</p>
                    <p className="text-sm opacity-90 mt-2">Professional photos coming soon</p>
                  </div>
                </div>
                {/* Image Navigation - only show if image exists */}
                {property.image_url && (
                  <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-2">
                    <div className="w-2 h-2 bg-white rounded-full shadow-lg"></div>
                    <div className="w-2 h-2 bg-white/50 rounded-full shadow-lg"></div>
                    <div className="w-2 h-2 bg-white/50 rounded-full shadow-lg"></div>
                  </div>
                )}
              </div>
            </div>

            {/* Property Information */}
            <div className="bg-white rounded-xl shadow-xl p-8">
              <div className="flex justify-between items-start mb-6">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h1 className="text-4xl font-bold text-gray-900">
                      {formatPrice(property.price)}
                    </h1>
                    <span className="bg-green-100 text-green-800 text-xs font-bold px-2.5 py-1 rounded-full">
                      FOR RENT
                    </span>
                  </div>
                  <p className="text-lg text-gray-700 mb-2">{property.address}</p>
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                      </svg>
                      {getBorough(property.address)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Property Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 py-6 border-t border-b border-gray-200">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Bedrooms</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {property.beds !== 'N/A' && property.beds !== null ? property.beds : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Bathrooms</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {property.baths !== 'N/A' && property.baths !== null ? property.baths : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Square Feet</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {property.sqft !== 'N/A' && property.sqft !== null ? property.sqft : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Type</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {property.property_type || 'N/A'}
                  </p>
                </div>
              </div>

              {/* Additional Details */}
              <div className="mt-6 space-y-3">
                <div className="flex items-start gap-3">
                  <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <p className="font-medium text-gray-900">Status</p>
                    <p className="text-sm text-gray-600">{property.status || 'Available'}</p>
                  </div>
                </div>

                {property.building_name && (
                  <div className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                    <div>
                      <p className="font-medium text-gray-900">Building</p>
                      <p className="text-sm text-gray-600">{property.building_name}</p>
                    </div>
                  </div>
                )}

                {property.bbl && (
                  <div className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    <div>
                      <p className="font-medium text-gray-900">BBL Code</p>
                      <p className="text-sm text-gray-600 font-mono">{property.bbl}</p>
                    </div>
                  </div>
                )}

                {property.url && (
                  <div className="mt-4">
                    <a
                      href={property.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-800 transition"
                    >
                      View on Zillow
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column - Watson Score Card & Chat */}
          <div className="lg:col-span-1">
            <div className="sticky top-24 space-y-6">
              {/* Cache indicator and refresh button */}
              {fromCache && (
                <div className="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
                  <div className="flex items-center gap-2 text-blue-700">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    <span className="text-sm font-medium">Loaded from cache</span>
                  </div>
                  <button
                    onClick={() => {
                      localStorage.removeItem(`watson_report_${id}`);
                      setFromCache(false);
                      triggerWatsonAnalysis(property.address, id);
                    }}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Refresh
                  </button>
                </div>
              )}
              
              <ScoreCard
                watsonResponse={watsonResponse}
                loading={watsonLoading}
                error={watsonError}
              />
              
              {/* {watsonStatus && !watsonError && (
                <div className="text-center">
                  <p className="text-sm text-gray-600">{watsonStatus}</p>
                </div>
              )} */}
              
              {/* Watson Chat - shows as soon as we have a thread OR if loaded from cache */}
              {(threadId || fromCache) && (
                <WatsonChat
                  threadId={threadId}
                  onThreadId={setThreadId}
                  propertyAddress={property?.address}
                />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PropertyDetail;
