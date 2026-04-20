import React, { useState, useEffect } from 'react';
import { projectsApi, tasksApi, timeEntriesApi } from '../api/client';

function Dashboard({ users, projects, onRefresh }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSummary();
  }, []);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      const summaryRes = await timeEntriesApi.getSummary();
      setSummary(summaryRes.data);
    } catch (err) {
      console.error('Error fetching summary:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const totalProjectCost = projects.reduce((sum, p) => sum + (p.budget || 0), 0);

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <h3>{projects.length}</h3>
          <p>Total Projects</p>
        </div>
        <div className="stat-card">
          <h3>{users.length}</h3>
          <p>Team Members</p>
        </div>
        <div className="stat-card">
          <h3>{summary ? formatTime(summary.total_time_seconds) : '0h 0m'}</h3>
          <p>Time Tracked</p>
        </div>
        <div className="stat-card">
          <h3>${summary ? summary.total_cost.toFixed(2) : '0.00'}</h3>
          <p>Total Cost</p>
        </div>
      </div>

      <div className="card">
        <h2>📁 Recent Projects</h2>
        {projects.length === 0 ? (
          <p>No projects yet. Create your first project!</p>
        ) : (
          <ul className="item-list">
            {projects.slice(0, 5).map((project) => (
              <li key={project.id} className="item-card">
                <h3>{project.name}</h3>
                <p>{project.description || 'No description'}</p>
                <div className="item-meta">
                  <span className="badge badge-active">{project.status}</span>
                  <span>Rate: ${project.hourly_rate}/hr</span>
                  {project.budget && <span>Budget: ${project.budget}</span>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h2>💡 Quick Start Guide</h2>
        <ol style={{ paddingLeft: '20px', lineHeight: '2' }}>
          <li>Create a user in the <strong>Projects</strong> tab (needed for project ownership)</li>
          <li>Create a new project with budget and hourly rate</li>
          <li>Add tasks to your project in the <strong>Tasks</strong> tab</li>
          <li>Start tracking time in the <strong>Time Tracker</strong> tab</li>
          <li>Stop the timer to calculate costs automatically</li>
          <li>View summaries and reports on this dashboard</li>
        </ol>
      </div>
    </div>
  );
}

export default Dashboard;
