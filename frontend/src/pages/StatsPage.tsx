import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { StatsResponse } from '../types/contracts';
import './StatsPage.css';

const RULE_DESCRIPTIONS: Record<string, string> = {
  R1: "Manufacturer/packer/importer name + complete address",
  R2: "Common/generic name of commodity",
  R3: "Net quantity in correct unit",
  R4: "Month & year of manufacture",
  R5: "MRP prescribed wording (the most common violation)",
  R6: "Consumer care details",
  R7: "Declarations in Hindi (Devanagari) or English",
  R8: "Minimum numeral height (MRP/quantity numerals)",
  R9: "Clear space around the quantity declaration",
  R10: "Contrast of MRP/quantity numerals",
  R11: "No misleading quantity qualifiers"
};

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
          <span className="page-header-id reveal-1">
            <span className="numeral">03</span>
            <span className="identifier">ANALYTICS</span>
          </span>
          <h1 className="page-header-title reveal-2">System Analytics</h1>
          <p className="page-header-desc reveal-3">Performance metrics and compliance trends across all inspections.</p>
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
          <div className="total-scans-card">
            <span className="stat-value">{stats.total_scans}</span>
            <span className="stat-label">TOTAL INSPECTIONS</span>
          </div>
          <div className="secondary-stats">
            <div className="stat-card pass">
              <span className="stat-label">PASSED</span>
              <span className="stat-value">{stats.overall.pass}</span>
            </div>
            <div className="stat-card fail">
              <span className="stat-label">FAILED</span>
              <span className="stat-value">{stats.overall.fail}</span>
            </div>
            <div className="stat-card review">
              <span className="stat-label">REVIEWS NEEDED</span>
              <span className="stat-value">{stats.overall.needs_review || 0}</span>
            </div>
          </div>
        </div>

        <div className="stats-content">
          <div className="breakdown-section">
            <h2>RULE ANALYSIS</h2>
            <div className="rule-stats-list">
              {Object.entries(stats.by_rule).map(([ruleId, ruleStats]) => (
                <div key={ruleId} className="rule-stat-item">
                  <div className="rule-header">
                    <span className="rule-id" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>{ruleId}</span>
                    {RULE_DESCRIPTIONS[ruleId] && (
                      <h3 style={{ margin: '0 0 16px 0', fontSize: '1rem', fontWeight: 500, lineHeight: 1.4, maxWidth: '600px' }}>{RULE_DESCRIPTIONS[ruleId]}</h3>
                    )}
                  </div>
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
            <h2>MOST FREQUENT FAILURES</h2>
            <div className="top-failures-list">
              {stats.most_failed_rules.map((rule, idx) => (
                <div key={rule.rule_id} className="top-failure-item">
                  <span className="rank">#{idx + 1}</span>
                  <div className="rule-info" style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
                    <span className="rule-id" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>{rule.rule_id}</span>
                    {RULE_DESCRIPTIONS[rule.rule_id] ? (
                      <span className="rule-desc" style={{ fontSize: '0.9rem', lineHeight: 1.3, marginTop: '2px', whiteSpace: 'normal', wordWrap: 'break-word' }}>{RULE_DESCRIPTIONS[rule.rule_id]}</span>
                    ) : (
                      <span className="rule-desc" style={{ fontSize: '0.9rem', lineHeight: 1.3, marginTop: '2px', whiteSpace: 'normal', wordWrap: 'break-word' }}>{rule.rule_id}</span>
                    )}
                  </div>
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
