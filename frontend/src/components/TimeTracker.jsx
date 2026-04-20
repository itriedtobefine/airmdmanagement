import React, { useState, useEffect } from 'react';
import { timeEntriesApi, tasksApi } from '../api/client';

function TimeTracker({ users, projects, onRefresh }) {
  const [tasks, setTasks] = useState([]);
  const [activeEntries, setActiveEntries] = useState([]);
  const [recentEntries, setRecentEntries] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  
  // Form state for starting timer
  const [showStartForm, setShowStartForm] = useState(false);
  const [formData, setFormData] = useState({
    task_id: '',
    project_id: '',
    user_id: '',
    hourly_rate: 100,
    description: ''
  });

  // Timer state
  const [timerRunning, setTimerRunning] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    let interval;
    if (timerRunning && activeEntries.length > 0) {
      interval = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [timerRunning, activeEntries]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [tasksRes, entriesRes, summaryRes] = await Promise.all([
        tasksApi.getAll(),
        timeEntriesApi.getAll({ limit: 10 }),
        timeEntriesApi.getSummary()
      ]);
      setTasks(tasksRes.data);
      setRecentEntries(entriesRes.data);
      setSummary(summaryRes.data);
      
      // Find active entries
      const active = entriesRes.data.filter(e => e.is_active);
      setActiveEntries(active);
      setTimerRunning(active.length > 0);
      
      if (active.length > 0) {
        const entry = active[0];
        const startTime = new Date(entry.start_time);
        const now = new Date();
        setElapsedTime(Math.floor((now - startTime) / 1000));
      } else {
        setElapsedTime(0);
      }
      
      setError(null);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to load time tracking data');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleProjectChange = (e) => {
    const projectId = parseInt(e.target.value);
    setFormData(prev => ({ 
      ...prev, 
      project_id: projectId,
      task_id: '' // Reset task when project changes
    }));
  };

  const handleStartTimer = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const submitData = {
        ...formData,
        task_id: parseInt(formData.task_id),
        project_id: parseInt(formData.project_id),
        user_id: parseInt(formData.user_id),
        hourly_rate: parseFloat(formData.hourly_rate)
      };
      
      await timeEntriesApi.start(submitData);
      setSuccessMessage('Timer started successfully!');
      setShowStartForm(false);
      setFormData({
        task_id: '',
        project_id: '',
        user_id: '',
        hourly_rate: 100,
        description: ''
      });
      setTimerRunning(true);
      setElapsedTime(0);
      onRefresh();
      fetchData();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Error starting timer:', err);
      setError(err.response?.data?.detail || 'Failed to start timer');
    } finally {
      setLoading(false);
    }
  };

  const handleStopTimer = async (entryId) => {
    try {
      setLoading(true);
      await timeEntriesApi.stop(entryId);
      setSuccessMessage('Timer stopped! Time and cost calculated.');
      setTimerRunning(false);
      setElapsedTime(0);
      onRefresh();
      fetchData();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Error stopping timer:', err);
      setError('Failed to stop timer');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatTimeShort = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const getTaskName = (taskId) => {
    const task = tasks.find(t => t.id === taskId);
    return task ? task.title : 'Unknown Task';
  };

  const getProjectName = (projectId) => {
    const project = projects.find(p => p.id === projectId);
    return project ? project.name : 'Unknown Project';
  };

  const getUserName = (userId) => {
    const user = users.find(u => u.id === userId);
    return user ? user.username : 'Unknown User';
  };

  const filteredTasks = formData.project_id 
    ? tasks.filter(t => t.project_id === parseInt(formData.project_id))
    : [];

  return (
    <div>
      {error && <div className="error">{error}</div>}
      {successMessage && <div className="success-message">{successMessage}</div>}

      {/* Timer Display */}
      <div className="card">
        <h2>⏲️ Active Timer</h2>
        
        {timerRunning && activeEntries.length > 0 ? (
          <div>
            <div className="timer-display">
              {formatTime(elapsedTime)}
            </div>
            <p style={{ textAlign: 'center', marginBottom: '20px' }}>
              Tracking: <strong>{getTaskName(activeEntries[0].task_id)}</strong> in{' '}
              <strong>{getProjectName(activeEntries[0].project_id)}</strong>
            </p>
            <div style={{ textAlign: 'center' }}>
              <button 
                className="btn btn-danger" 
                onClick={() => handleStopTimer(activeEntries[0].id)}
                disabled={loading}
              >
                {loading ? 'Stopping...' : '⏹️ Stop Timer'}
              </button>
            </div>
          </div>
        ) : (
          <div>
            <p style={{ textAlign: 'center', color: '#718096' }}>No active timer</p>
            <div style={{ textAlign: 'center' }}>
              <button 
                className="btn btn-success" 
                onClick={() => setShowStartForm(!showStartForm)}
              >
                {showStartForm ? 'Cancel' : '▶️ Start New Timer'}
              </button>
            </div>
          </div>
        )}

        {/* Start Timer Form */}
        {showStartForm && !timerRunning && (
          <form onSubmit={handleStartTimer} style={{ marginTop: '20px' }}>
            <div className="form-group">
              <label>User *</label>
              <select
                name="user_id"
                value={formData.user_id}
                onChange={handleInputChange}
                required
              >
                <option value="">Select a user</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>{user.username} ({user.email})</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Project *</label>
              <select
                name="project_id"
                value={formData.project_id}
                onChange={handleProjectChange}
                required
              >
                <option value="">Select a project</option>
                {projects.map(project => (
                  <option key={project.id} value={project.id}>{project.name}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Task *</label>
              <select
                name="task_id"
                value={formData.task_id}
                onChange={handleInputChange}
                required
                disabled={!formData.project_id}
              >
                <option value="">Select a task</option>
                {filteredTasks.map(task => (
                  <option key={task.id} value={task.id}>{task.title}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Hourly Rate ($)</label>
              <input
                type="number"
                name="hourly_rate"
                value={formData.hourly_rate}
                onChange={handleInputChange}
                min="0"
                step="0.01"
              />
            </div>

            <div className="form-group">
              <label>Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                rows="2"
                placeholder="What are you working on?"
              />
            </div>

            <button type="submit" className="btn btn-success" disabled={loading}>
              {loading ? 'Starting...' : '▶️ Start Timer'}
            </button>
          </form>
        )}
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="stats-grid" style={{ marginTop: '20px' }}>
          <div className="stat-card">
            <h3>{formatTimeShort(summary.total_time_seconds)}</h3>
            <p>Total Time Tracked</p>
          </div>
          <div className="stat-card">
            <h3>${summary.total_cost.toFixed(2)}</h3>
            <p>Total Cost</p>
          </div>
          <div className="stat-card">
            <h3>{summary.total_entries}</h3>
            <p>Total Entries</p>
          </div>
          <div className="stat-card">
            <h3>{summary.active_entries}</h3>
            <p>Active Timers</p>
          </div>
        </div>
      )}

      {/* Recent Entries */}
      <div className="card" style={{ marginTop: '20px' }}>
        <h2>📋 Recent Time Entries</h2>
        
        {loading && recentEntries.length === 0 && (
          <div className="loading">Loading entries...</div>
        )}
        
        {!loading && recentEntries.length === 0 && (
          <p>No time entries yet. Start a timer to begin tracking!</p>
        )}
        
        {recentEntries.length > 0 && (
          <ul className="item-list">
            {recentEntries.map(entry => (
              <li key={entry.id} className="item-card">
                <h3>{getTaskName(entry.task_id)}</h3>
                <p>{entry.description || 'No description'}</p>
                <div className="item-meta">
                  <span className={`badge badge-${entry.is_active ? 'active' : 'completed'}`}>
                    {entry.is_active ? '🔴 Active' : '✅ Completed'}
                  </span>
                  <span>Project: {getProjectName(entry.project_id)}</span>
                  <span>User: {getUserName(entry.user_id)}</span>
                  <span>Duration: {formatTimeShort(entry.duration_seconds)}</span>
                  <span>Cost: ${entry.total_cost.toFixed(2)}</span>
                  <span>Rate: ${entry.hourly_rate}/hr</span>
                </div>
                {entry.is_active && (
                  <div className="actions">
                    <button 
                      className="btn btn-danger" 
                      onClick={() => handleStopTimer(entry.id)}
                      disabled={loading}
                    >
                      Stop
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default TimeTracker;
