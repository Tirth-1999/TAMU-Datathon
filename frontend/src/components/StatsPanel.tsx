/**
 * Statistics panel component
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { ClassificationCategory } from '../types/classification';
import type { ClassificationResult } from '../types/classification';

interface StatsPanelProps {
  results: ClassificationResult[];
}

const CATEGORY_COLORS = {
  [ClassificationCategory.PUBLIC]: '#10b981',
  [ClassificationCategory.CONFIDENTIAL]: '#f59e0b',
  [ClassificationCategory.HIGHLY_SENSITIVE]: '#ef4444',
  [ClassificationCategory.UNSAFE]: '#8b5cf6',
};

export const StatsPanel: React.FC<StatsPanelProps> = ({ results }) => {
  if (results.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
        <p className="text-sm text-gray-500">No data available yet. Upload and classify documents to see statistics.</p>
      </div>
    );
  }

  // Calculate statistics
  const categoryCounts = results.reduce((acc, result) => {
    acc[result.classification] = (acc[result.classification] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const pieData = Object.entries(categoryCounts).map(([name, value]) => ({
    name,
    value,
  }));

  const avgConfidence = results.reduce((sum, r) => sum + r.confidence, 0) / results.length;
  const avgProcessingTime = results.reduce((sum, r) => sum + r.processing_time, 0) / results.length;
  const reviewNeeded = results.filter(r => r.requires_review).length;
  const unsafeCount = results.filter(r => !r.safety_check.is_safe).length;

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-sm text-gray-500 mb-1">Total Documents</p>
          <p className="text-2xl font-bold text-gray-900">{results.length}</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-sm text-gray-500 mb-1">Avg Confidence</p>
          <p className="text-2xl font-bold text-gray-900">{Math.round(avgConfidence * 100)}%</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-sm text-gray-500 mb-1">Needs Review</p>
          <p className="text-2xl font-bold text-yellow-600">{reviewNeeded}</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-sm text-gray-500 mb-1">Unsafe Content</p>
          <p className="text-2xl font-bold text-red-600">{unsafeCount}</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Classification Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[entry.name as ClassificationCategory] || '#94a3b8'} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Bar Chart */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Confidence Levels</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={results.slice(0, 10)}>
              <XAxis dataKey="filename" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" height={80} />
              <YAxis domain={[0, 1]} tickFormatter={(value) => `${Math.round(value * 100)}%`} />
              <Tooltip formatter={(value: any) => `${Math.round(value * 100)}%`} />
              <Bar dataKey="confidence" fill="#0ea5e9" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Additional Stats */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Processing Metrics</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-gray-500 mb-1">Avg Processing Time</p>
            <p className="text-lg font-semibold text-gray-900">{avgProcessingTime.toFixed(2)}s</p>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">Total Pages Processed</p>
            <p className="text-lg font-semibold text-gray-900">
              {results.reduce((sum, r) => sum + r.page_count, 0)}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">Total Images Analyzed</p>
            <p className="text-lg font-semibold text-gray-900">
              {results.reduce((sum, r) => sum + r.image_count, 0)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
