import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { StatsResponse } from '../types/contracts';
import './StatsPage.css';

export default function StatsPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getStats();
      setStats(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load statistics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="stats-page state-container">
        <div className="spinner"></div>
        <p>Loading statistics...</p>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="stats-page state-container">
        <h2>Error Loading Statistics</h2>
        <p className="error-text">{error || 'Unknown error'}</p>
        <button className="btn-retry" onClick={fetchStats}>Retry</button>
      </div>
    );
  }

  return (
    <div className="stats-page">
      <div className="stats-container">
        <h1>Platform Statistics</h1>
        
        <div className="overall-stats">
          <div className="stat-card primary">
            <span className="stat-value">{stats.total_scans}</span>
            <span className="stat-label">Total Scans</span>
          </div>
          <div className="stat-card pass">
            <span className="stat-value">{stats.overall.pass}</span>
            <span className="stat-label">Total Passes</span>
          </div>
          <div className="stat-card fail">
            <span className="stat-value">{stats.overall.fail}</span>
            <span className="stat-label">Total Failures</span>
          </div>
        </div>

        <div className="stats-content">
          <div className="breakdown-section">
            <h2>Breakdown by Rule</h2>
            <div className="rule-stats-list">
              {Object.entries(stats.by_rule).map(([ruleId, ruleStats]) => (
                <div key={ruleId} className="rule-stat-item">
                  <h3>{ruleId}</h3>
                  <div className="rule-stat-bars">
                    <div className="stat-bar-group">
                      <span className="label">Pass ({ruleStats.pass})</span>
                      <div className="bar-bg">
                        <div className="bar-fill pass" style={{ width: `${Math.min(100, (ruleStats.pass / Math.max(1, stats.total_scans)) * 100)}%` }}></div>
                      </div>
                    </div>
                    <div className="stat-bar-group">
                      <span className="label">Fail ({ruleStats.fail})</span>
                      <div className="bar-bg">
                        <div className="bar-fill fail" style={{ width: `${Math.min(100, (ruleStats.fail / Math.max(1, stats.total_scans)) * 100)}%` }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="top-failures-section">
            <h2>Most Failed Rules</h2>
            <div className="top-failures-list">
              {stats.most_failed_rules.map((rule, idx) => (
                <div key={rule.rule_id} className="top-failure-item">
                  <span className="rank">#{idx + 1}</span>
                  <span className="rule-id">{rule.rule_id}</span>
                  <span className="count">{rule.count} failures</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
