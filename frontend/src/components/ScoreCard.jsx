import React from 'react';

const ScoreCard = ({ watsonResponse, loading, error }) => {
  // Parse Watson response to extract structured data
  const parseReport = (response) => {
    if (!response) return null;

    console.log('Raw Watson response type:', typeof response);
    console.log('Raw Watson response preview:', response.substring(0, 200));

    try {
      // Try to parse as JSON first (if Watson returns JSON)
      // Check for ```json wrapped JSON
      const jsonMatch = response.match(/```json\n([\s\S]*?)\n```/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[1]);
      }

      // Try to parse the entire response as JSON (if it's pure JSON without markdown)
      try {
        const parsed = JSON.parse(response);
        console.log('Parsed Watson response:', parsed);
        console.log('Raw scores object:', parsed.scores);
        console.log('Financial audit object:', parsed.financial_audit);
        
        // Check if it has the expected report structure with scores
        if (parsed.scores) {
          // Normalize field names from Watson format to component format
          // Also check financial_audit for score if not in scores
          const financialScore = parsed.scores.financial_score ?? 
                                 parsed.scores.financial ?? 
                                 parsed.financial_audit?.score ??
                                 parsed.financial_audit?.financial_score;
          
          const normalized = { 
            ...parsed,
            scores: {
              overall: parsed.scores.overall_transparency_grade ?? parsed.scores.overall_grade ?? parsed.scores.overall,
              quality: parsed.scores.quality_score ?? parsed.scores.quality,
              financial: financialScore
            }
          };
          
          console.log('Normalized scores:', normalized.scores);
          
          // Check if we have actual score values
          if (normalized.scores.overall !== undefined || normalized.scores.quality !== undefined || normalized.scores.financial !== undefined) {
            return normalized;
          }
        }
        // If it's just property data without scores, ignore and try markdown parsing
        if (parsed.property && !parsed.scores) {
          console.log('Received property data, waiting for analysis...');
          return null;
        }
        
        // If parsed but no recognized structure, return with full_text for fallback display
        return { ...parsed, full_text: response };
      } catch (e) {
        console.log('JSON parse failed, trying markdown:', e.message);
        // Not pure JSON, continue to markdown parsing
      }

      // Fall back to markdown parsing
      const report = {
        property: {},
        scores: {},
        quality_audit: { recent_issues: [] },
        financial_audit: { risk_factors: [] },
        recommendation: {},
      };

      // Extract overall grade
      const overallMatch = response.match(/Overall Grade:\s*\*?\*?(\d+(?:\.\d+)?)\%/i);
      if (overallMatch) report.scores.overall = parseFloat(overallMatch[1]);

      // Extract quality score
      const qualityMatch = response.match(/Quality Score:\s*\*?\*?(\d+)\/100/i);
      if (qualityMatch) {
        report.scores.quality = parseInt(qualityMatch[1]);
        report.quality_audit.score = parseInt(qualityMatch[1]);
      }

      // Extract financial score
      const financialMatch = response.match(/Financial Score:\s*\*?\*?(\d+)\/100/i);
      if (financialMatch) {
        report.scores.financial = parseInt(financialMatch[1]);
        report.financial_audit.score = parseInt(financialMatch[1]);
      }

      // Extract city market value
      const marketValueMatch = response.match(/City Market Value:\s*\*?\*?\$?([\d,]+)/i);
      if (marketValueMatch) {
        report.financial_audit.city_market_value = parseInt(marketValueMatch[1].replace(/,/g, ''));
      }

      // Extract annual tax
      const taxMatch = response.match(/(?:Est\.|Estimated) Annual Tax:\s*\*?\*?\$?([\d,]+)/i);
      if (taxMatch) {
        report.financial_audit.annual_tax = parseInt(taxMatch[1].replace(/,/g, ''));
      }

      // Extract recent issues (simplified - captures bullet points in Quality section)
      const qualitySection = response.match(/### 1\. Building Quality Audit[\s\S]*?(?=###|\*\*Final|$)/i);
      if (qualitySection) {
        const issueMatches = qualitySection[0].matchAll(/[-–]\s*([^\n(]+)(?:\s*\(([^)]+)\))?/g);
        for (const match of issueMatches) {
          report.quality_audit.recent_issues.push({
            type: match[1].trim(),
            details: match[2] || ''
          });
        }
        
        // Extract Scout's Note
        const scoutMatch = qualitySection[0].match(/Scout's Note:\*?\*?\s*([^\n]+(?:\n(?![-–\*#])[^\n]+)*)/i);
        if (scoutMatch) {
          report.quality_audit.scouts_note = scoutMatch[1].trim();
        }
      }

      // Extract risk factors
      const financialSection = response.match(/### 2\. Financial & Tax Audit[\s\S]*?(?=###|\*\*Final|$)/i);
      if (financialSection) {
        const riskMatches = financialSection[0].matchAll(/[-–]\s*([^\n]+)/g);
        for (const match of riskMatches) {
          const risk = match[1].trim();
          if (risk && !risk.match(/^\d+/)) { // Avoid capturing numeric values
            report.financial_audit.risk_factors.push(risk);
          }
        }
      }

      // Extract final recommendation
      const recommendationMatch = response.match(/\*\*Final Recommendation:\*\*\s*\*?\*?([^–\-\n]+)(?:[–\-]\s*([^\n]+))?/i);
      if (recommendationMatch) {
        report.recommendation.level = recommendationMatch[1].trim();
        report.recommendation.reason = recommendationMatch[2]?.trim() || '';
      }

      // Keep full response as fallback
      report.full_text = response;

      return report;
    } catch (e) {
      console.error('Error parsing Watson report:', e);
      return { full_text: response };
    }
  };

  const report = parseReport(watsonResponse);
  
  console.log('Final report object:', report);
  console.log('Report scores:', report?.scores);

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-600 bg-green-100 border-green-200';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100 border-yellow-200';
    if (score >= 40) return 'text-orange-600 bg-orange-100 border-orange-200';
    return 'text-red-600 bg-red-100 border-red-200';
  };

  const getScoreIcon = (score) => {
    if (score >= 80) return '🟢';
    if (score >= 60) return '🟡';
    if (score >= 40) return '🟠';
    return '🔴';
  };

  const getRiskColor = (level) => {
    if (!level) return 'bg-gray-100 text-gray-800';
    const lower = level.toLowerCase();
    if (lower.includes('high')) return 'bg-red-100 text-red-800 border-red-200';
    if (lower.includes('medium') || lower.includes('moderate')) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    if (lower.includes('low')) return 'bg-green-100 text-green-800 border-green-200';
    return 'bg-gray-100 text-gray-800';
  };

  const formatCurrency = (value) => {
    if (!value) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0
    }).format(value);
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900">AI Transparency Report</h2>
          <div className="flex items-center gap-2 text-blue-600">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
            <span className="text-sm font-medium">Analyzing...</span>
          </div>
        </div>
        <div className="space-y-3">
          <div className="h-20 bg-gray-100 rounded animate-pulse"></div>
          <div className="h-20 bg-gray-100 rounded animate-pulse"></div>
          <div className="h-32 bg-gray-100 rounded animate-pulse"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">AI Transparency Report</h2>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Failed to load analysis: {error}</p>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">AI Transparency Report</h2>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-blue-800">Analysis will load automatically...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-6 text-white">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-2xl font-bold">AI Transparency Report</h2>
          <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
            <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
          </svg>
        </div>
        <p className="text-blue-100 text-sm">Powered by Watson AI • NYC Open Data</p>
      </div>

      <div className="p-6 space-y-6">
        {/* Overall Grade */}
        {report.scores?.overall !== null && report.scores?.overall !== undefined && (
          <div className={`p-6 rounded-lg border-2 ${getScoreColor(report.scores.overall)}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium opacity-75 mb-1">Overall Transparency Grade</p>
                <div className="flex items-baseline gap-2">
                  <p className="text-5xl font-bold">{report.scores.overall.toFixed(1)}%</p>
                  {report.recommendation?.level && (
                    <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getRiskColor(report.recommendation.level)}`}>
                      {report.recommendation.level}
                    </span>
                  )}
                </div>
              </div>
              <div className="text-6xl">{getScoreIcon(report.scores.overall)}</div>
            </div>
          </div>
        )}

        {/* Score Breakdown */}
        <div className="grid grid-cols-2 gap-4">
          {/* Quality Score */}
          {report.scores?.quality !== null && report.scores?.quality !== undefined && (
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-4 h-4 text-blue-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-xs font-medium text-gray-600">Building Quality</span>
              </div>
              <div className="flex items-end justify-between mb-2">
                <span className={`text-2xl font-bold ${
                  report.scores.quality >= 80 ? 'text-green-600' :
                  report.scores.quality >= 60 ? 'text-yellow-600' :
                  report.scores.quality >= 40 ? 'text-orange-600' : 'text-red-600'
                }`}>
                  {report.scores.quality}
                </span>
                <span className="text-xs text-gray-500">/100</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    report.scores.quality >= 80 ? 'bg-green-500' :
                    report.scores.quality >= 60 ? 'bg-yellow-500' :
                    report.scores.quality >= 40 ? 'bg-orange-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.max(0, report.scores.quality)}%` }}
                ></div>
              </div>
              <p className="text-xs text-gray-500 mt-1">311 Complaints</p>
            </div>
          )}

          {/* Financial Score */}
          {report.scores?.financial !== null && report.scores?.financial !== undefined && (
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-4 h-4 text-green-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-xs font-medium text-gray-600">Financial Health</span>
              </div>
              <div className="flex items-end justify-between mb-2">
                <span className={`text-2xl font-bold ${
                  report.scores.financial >= 80 ? 'text-green-600' :
                  report.scores.financial >= 60 ? 'text-yellow-600' :
                  report.scores.financial >= 40 ? 'text-orange-600' : 'text-red-600'
                }`}>
                  {report.scores.financial}
                </span>
                <span className="text-xs text-gray-500">/100</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    report.scores.financial >= 80 ? 'bg-green-500' :
                    report.scores.financial >= 60 ? 'bg-yellow-500' :
                    report.scores.financial >= 40 ? 'bg-orange-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.max(0, report.scores.financial)}%` }}
                ></div>
              </div>
              <p className="text-xs text-gray-500 mt-1">DOF Records</p>
            </div>
          )}
        </div>

        {/* Quality Audit Details */}
        {report.quality_audit && (report.quality_audit.recent_issues?.length > 0 || report.quality_audit.scouts_note) && (
          <div className="border border-gray-200 rounded-lg p-5">
            <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
              Building Quality Audit
            </h3>
            
            {report.quality_audit.recent_issues?.length > 0 && (
              <div className="mb-4">
                <p className="text-sm font-semibold text-gray-700 mb-2">Recent Issues (311 Complaints):</p>
                <div className="space-y-2">
                  {report.quality_audit.recent_issues.slice(0, 5).map((issue, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm">
                      <span className="text-red-500 mt-0.5">▪</span>
                      <div className="flex-1">
                        <span className="font-medium text-gray-800">{issue.type}</span>
                        {issue.details && <span className="text-gray-600"> - {issue.details}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {report.quality_audit.scouts_note && (
              <div className="bg-blue-50 border-l-4 border-blue-500 p-3 rounded">
                <p className="text-sm font-semibold text-blue-900 mb-1">Scout's Note:</p>
                <p className="text-sm text-blue-800">{report.quality_audit.scouts_note}</p>
              </div>
            )}
          </div>
        )}

        {/* Financial Audit Details */}
        {report.financial_audit && (report.financial_audit.city_market_value || report.financial_audit.risk_factors?.length > 0) && (
          <div className="border border-gray-200 rounded-lg p-5">
            <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
              <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              Financial & Tax Audit
            </h3>

            <div className="grid grid-cols-2 gap-4 mb-4">
              {report.financial_audit.city_market_value && (
                <div>
                  <p className="text-xs text-gray-600 mb-1">City Market Value</p>
                  <p className="text-xl font-bold text-gray-900">{formatCurrency(report.financial_audit.city_market_value)}</p>
                </div>
              )}
              {report.financial_audit.annual_tax && (
                <div>
                  <p className="text-xs text-gray-600 mb-1">Est. Annual Tax</p>
                  <p className="text-xl font-bold text-gray-900">{formatCurrency(report.financial_audit.annual_tax)}</p>
                </div>
              )}
            </div>

            {report.financial_audit.risk_factors?.length > 0 && (
              <div>
                <p className="text-sm font-semibold text-gray-700 mb-2">Risk Factors:</p>
                <div className="space-y-1">
                  {report.financial_audit.risk_factors.map((factor, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm">
                      <span className="text-yellow-600 mt-0.5">⚠</span>
                      <span className="text-gray-700">{factor}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Final Recommendation */}
        {report.recommendation?.reason && (
          <div className={`p-4 rounded-lg border-2 ${getRiskColor(report.recommendation.level)}`}>
            <div className="flex items-start gap-3">
              <svg className="w-6 h-6 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <p className="font-bold mb-1">Final Recommendation:</p>
                <p className="text-sm">{report.recommendation.reason}</p>
              </div>
            </div>
          </div>
        )}

        {/* Fallback: Show full text if structured parsing failed */}
        {report.full_text && !report.scores?.overall && (
          <div className="border-t border-gray-200 pt-4">
            <details>
              <summary className="text-sm font-semibold text-gray-700 cursor-pointer hover:text-gray-900">
                View Full Report
              </summary>
              <div className="mt-3 prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
                {report.full_text}
              </div>
            </details>
          </div>
        )}
      </div>
    </div>
  );
};

export default ScoreCard;
