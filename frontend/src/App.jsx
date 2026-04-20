import React, { useState, useEffect } from 'react';
import Projects from './components/Projects';
import Tasks from './components/Tasks';
import TimeTracker from './components/TimeTracker';
import Dashboard from './components/Dashboard';
import { usersApi, projectsApi } from './api/client';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [users, setUsers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [usersRes, projectsRes] = await Promise.all([
        usersApi.getAll(),
        projectsApi.getAll()
      ]);
      setUsers(usersRes.data);
      setProjects(projectsRes.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to load data. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const renderContent = () => {
    if (loading) {
      return <div className="loading">Loading...</div>;
    }

    if (error) {
      return <div className="error">{error}</div>;
    }

    switch (activeTab) {
      case 'dashboard':
        return <Dashboard users={users} projects={projects} onRefresh={fetchData} />;
      case 'projects':
        return <Projects users={users} onRefresh={fetchData} />;
      case 'tasks':
        return <Tasks projects={projects} onRefresh={fetchData} />;
      case 'timetracker':
        return <TimeTracker users={users} projects={projects} onRefresh={fetchData} />;
      default:
        return <Dashboard users={users} projects={projects} onRefresh={fetchData} />;
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>⏱️ TimeTracker Pro</h1>
        <p>Manage projects, track time, and calculate costs</p>
      </header>

      <nav className="nav-tabs">
        <button
          className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          📊 Dashboard
        </button>
        <button
          className={`nav-tab ${activeTab === 'projects' ? 'active' : ''}`}
          onClick={() => setActiveTab('projects')}
        >
          📁 Projects
        </button>
        <button
          className={`nav-tab ${activeTab === 'tasks' ? 'active' : ''}`}
          onClick={() => setActiveTab('tasks')}
        >
          ✅ Tasks
        </button>
        <button
          className={`nav-tab ${activeTab === 'timetracker' ? 'active' : ''}`}
          onClick={() => setActiveTab('timetracker')}
        >
          ⏲️ Time Tracker
        </button>
      </nav>

      <main>
        {renderContent()}
      </main>
    </div>
  );
}

export default App;
