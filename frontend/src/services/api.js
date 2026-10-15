import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Fetch properties with optional filters
 * @param {Object} params - Filter parameters
 * @param {number} params.skip - Number of properties to skip (pagination)
 * @param {number} params.limit - Number of properties to return
 * @param {number} params.minPrice - Minimum price filter
 * @param {number} params.maxPrice - Maximum price filter
 * @param {number} params.beds - Number of bedrooms filter
 * @param {string} params.borough - Borough filter (Brooklyn, Manhattan, Queens, Bronx, Staten Island)
 * @returns {Promise} - Array of property objects
 */
export const getProperties = async (params = {}) => {
  try {
    const response = await api.get('/properties', { params });
    // Backend returns { properties: [...] }, extract the array
    return response.data.properties || [];
  } catch (error) {
    console.error('Error fetching properties:', error);
    throw error;
  }
};

/**
 * Fetch a single property by ID
 * @param {string} propertyId - The property ID (zpid)
 * @returns {Promise} - Property object
 */
export const getPropertyById = async (propertyId) => {
  try {
    const response = await api.get(`/properties/${propertyId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching property:', error);
    throw error;
  }
};

/**
 * Fetch a property by address
 * @param {string} address - The property address
 * @returns {Promise} - Property object
 */
export const getPropertyByAddress = async (address) => {
  try {
    const response = await api.get(`/properties/address/${encodeURIComponent(address)}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching property by address:', error);
    throw error;
  }
};

/**
 * Stream Watson analysis for a property address using POST with SSE
 * @param {string} message - The message to send to Watson
 * @param {string} threadId - Optional thread ID for conversation continuity
 * @param {Function} onMessage - Callback for each message chunk
 * @param {Function} onStatus - Callback for status updates
 * @param {Function} onError - Callback for errors
 * @param {Function} onComplete - Callback when streaming completes
 * @returns {Function} - Cleanup function to abort the stream
 */
export const streamWatsonAnalysis = (message, threadId, onMessage, onStatus, onError, onComplete) => {
  const controller = new AbortController();
  
  const streamRequest = async () => {
    try {
      const body = {
        message: message,
      };
      
      // Add thread_id if provided for conversation continuity
      if (threadId) {
        body.thread_id = threadId;
      }
      
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            
            if (!data) continue;

            try {
              const parsed = JSON.parse(data);
              
              // Handle different event types based on the data structure
              if (parsed.type === 'connected') {
                console.log('Watson stream connected:', parsed.run_id);
              } else if (parsed.type === 'status') {
                if (onStatus) onStatus(parsed.status);
              } else if (parsed.type === 'message') {
                // Watson returns JSON as a string in the content field
                // Try to parse it, otherwise use as-is
                let content = parsed.content;
                try {
                  // If content is a JSON string, parse it and re-stringify for display
                  const contentObj = JSON.parse(content);
                  // Pretty print the JSON for better readability
                  content = JSON.stringify(contentObj, null, 2);
                } catch (e) {
                  // Content is not JSON, use as-is (markdown text)
                }
                if (onMessage) onMessage(content);
              } else if (parsed.type === 'done') {
                if (onComplete) onComplete(parsed.thread_id);
              } else if (parsed.type === 'error') {
                if (onError) onError(parsed.error);
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e, data);
            }
          }
        }
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('Stream aborted');
      } else {
        console.error('Stream error:', error);
        if (onError) onError(error.message);
      }
    }
  };

  streamRequest();

  // Return cleanup function
  return () => {
    controller.abort();
  };
};

export default api;
