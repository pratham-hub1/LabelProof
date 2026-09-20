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

  return (
    <div className="stats-page">
      <div className="page-header">
        <span className="page-header-id reveal-1">03 / ANALYTICS</span>
        <h1 className="page-header-title reveal-2">Compliance Intelligence</h1>
        <p className="page-header-desc reveal-3">Macro-level statistics across all scanned products and declarations.</p>
      </div>

      <div className="stats-container reveal-4">
        {loading ? (
          <div className="state-container">
            <div className="spinner"></div>
          </div>
        ) : error || !stats ? (
          <div className="state-container">
            <p className="error-text">ERROR: {error || 'Unknown error'}</p>
            <button className="btn-primary" style={{ marginTop: '16px' }} onClick={fetchStats}>RETRY</button>
          </div>
        ) : stats.total_scans === 0 ? (
          <div className="empty-state">
            <div className="empty-state-ghost">03</div>
            <p className="empty-state-text">ANALYTICS AWAITING DATA</p>
            <p className="empty-state-subtext">Run inspections to populate compliance analytics.</p>
          </div>
        ) : (
          <>
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
                      <div className="label">
                        <span>PASS</span>
                        <span>{ruleStats.pass}</span>
                      </div>
                      <div className="bar-bg">
                        <div className="bar-fill pass" style={{ width: `${Math.min(100, (ruleStats.pass / Math.max(1, stats.total_scans)) * 100)}%` }}></div>
                      </div>
                    </div>
                    <div className="stat-bar-group">
                      <div className="label">
                        <span>FAIL</span>
                        <span>{ruleStats.fail}</span>
                      </div>
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
        </>
        )}
      </div>
    </div>
  );
}
