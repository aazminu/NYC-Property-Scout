import React, { createContext, useContext, useState, useEffect } from 'react';
import { getProperties } from '../services/api';

const PropertyContext = createContext();

export const useProperty = () => {
  const context = useContext(PropertyContext);
  if (!context) {
    throw new Error('useProperty must be used within PropertyProvider');
  }
  return context;
};

export const PropertyProvider = ({ children }) => {
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    skip: 0,
    limit: 20,
    minPrice: null,
    maxPrice: null,
    beds: null,
    borough: null,
  });

  // Fetch properties based on current filters
  const fetchProperties = async (newFilters = {}) => {
    setLoading(true);
    setError(null);
    
    const queryParams = { ...filters, ...newFilters };
    
    try {
      const data = await getProperties(queryParams);
      // Ensure data is always an array
      setProperties(Array.isArray(data) ? data : []);
      setFilters(queryParams);
    } catch (err) {
      setError(err.message || 'Failed to fetch properties');
      setProperties([]); // Reset to empty array on error
      console.error('Error in fetchProperties:', err);
    } finally {
      setLoading(false);
    }
  };

  // Update filters and fetch
  const updateFilters = (newFilters) => {
    fetchProperties({ ...filters, ...newFilters, skip: 0 }); // Reset to first page when filtering
  };

  // Pagination handlers
  const nextPage = () => {
    fetchProperties({ skip: filters.skip + filters.limit });
  };

  const prevPage = () => {
    if (filters.skip > 0) {
      fetchProperties({ skip: Math.max(0, filters.skip - filters.limit) });
    }
  };

  // Reset filters
  const resetFilters = () => {
    const defaultFilters = {
      skip: 0,
      limit: 20,
      minPrice: null,
      maxPrice: null,
      beds: null,
      borough: null,
    };
    fetchProperties(defaultFilters);
  };

  // Load initial properties
  useEffect(() => {
    fetchProperties();
  }, []);

  const value = {
    properties,
    loading,
    error,
    filters,
    updateFilters,
    fetchProperties,
    nextPage,
    prevPage,
    resetFilters,
    currentPage: Math.floor(filters.skip / filters.limit) + 1,
    hasNextPage: Array.isArray(properties) && properties.length === filters.limit,
    hasPrevPage: filters.skip > 0,
  };

  return (
    <PropertyContext.Provider value={value}>
      {children}
    </PropertyContext.Provider>
  );
};

export default PropertyContext;
