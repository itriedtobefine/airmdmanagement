import React, { useState, useEffect } from 'react';
import { tasksApi, projectsApi } from '../api/client';

function Tasks({ projects, onRefresh }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  
  // Form state
  const [showForm, setShowForm] = useState(false);
  const [selectedProject, setSelectedProject] = useState('');
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    project_id: '',
    status: 'pending',
    estimated_hours: ''
  });

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const response = await tasksApi.getAll();
      setTasks(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching tasks:', err);
      setError('Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const submitData = {
        ...formData,
        project_id: parseInt(formData.project_id),
        estimated_hours: formData.estimated_hours ? parseFloat(formData.estimated_hours) : null
      };
      
      await tasksApi.create(submitData);
      setSuccessMessage('Task created successfully!');
      setShowForm(false);
      setFormData({
        title: '',
        description: '',
        project_id: '',
        status: 'pending',
        estimated_hours: ''
      });
      onRefresh();
      fetchTasks();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Error creating task:', err);
      setError('Failed to create task');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this task? All time entries will be deleted.')) {
      return;
    }
    
    try {
      await tasksApi.delete(id);
      setSuccessMessage('Task deleted successfully!');
      onRefresh();
      fetchTasks();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Error deleting task:', err);
      setError('Failed to delete task');
    }
  };

  const getProjectName = (projectId) => {
    const project = projects.find(p => p.id === projectId);
    return project ? project.name : 'Unknown Project';
  };

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  return (
    <div>
      {error && <div className="error">{error}</div>}
      {successMessage && <div className="success-message">{successMessage}</div>}

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2>✅ Tasks</h2>
          <button 
            className="btn btn-primary" 
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? 'Cancel' : '+ New Task'}
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleSubmit} style={{ marginBottom: '20px' }}>
            <div className="form-group">
              <label>Task Title *</label>
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleInputChange}
                required
                placeholder="Enter task title"
              />
            </div>
            
            <div className="form-group">
              <label>Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                rows="3"
                placeholder="Task description"
              />
            </div>

            <div className="form-group">
              <label>Project *</label>
              <select
                name="project_id"
                value={formData.project_id}
                onChange={handleInputChange}
                required
              >
                <option value="">Select a project</option>
                {projects.map(project => (
                  <option key={project.id} value={project.id}>{project.name}</option>
                ))}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div className="form-group">
                <label>Status</label>
                <select
                  name="status"
                  value={formData.status}
                  onChange={handleInputChange}
                >
                  <option value="pending">Pending</option>
                  <option value="in-progress">In Progress</option>
                  <option value="completed">Completed</option>
                </select>
              </div>

              <div className="form-group">
                <label>Estimated Hours</label>
                <input
                  type="number"
                  name="estimated_hours"
                  value={formData.estimated_hours}
                  onChange={handleInputChange}
                  min="0"
                  step="0.5"
                  placeholder="Optional"
                />
              </div>
            </div>

            <button type="submit" className="btn btn-success" disabled={loading}>
              {loading ? 'Creating...' : 'Create Task'}
            </button>
          </form>
        )}

        {projects.length === 0 && (
          <div className="error">
            No projects found. Create a project first before adding tasks.
          </div>
        )}

        {loading && !showForm && <div className="loading">Loading tasks...</div>}
        
        {!loading && tasks.length === 0 && !showForm && (
          <p>No tasks yet. Click "+ New Task" to create one.</p>
        )}

        {!loading && tasks.length > 0 && (
          <ul className="item-list">
            {tasks.map(task => (
              <li key={task.id} className="item-card">
                <h3>{task.title}</h3>
                <p>{task.description || 'No description'}</p>
                <div className="item-meta">
                  <span className={`badge badge-${task.status === 'completed' ? 'completed' : 'pending'}`}>
                    {task.status}
                  </span>
                  <span>Project: {getProjectName(task.project_id)}</span>
                  {task.estimated_hours && <span>Est: {task.estimated_hours}h</span>}
                  {task.total_time_seconds !== undefined && (
                    <span>Tracked: {formatTime(task.total_time_seconds)}</span>
                  )}
                  {task.total_cost !== undefined && (
                    <span>Cost: ${task.total_cost.toFixed(2)}</span>
                  )}
                </div>
                <div className="actions">
                  <button 
                    className="btn btn-danger" 
                    onClick={() => handleDelete(task.id)}
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default Tasks;
