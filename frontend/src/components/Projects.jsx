import React, { useState, useEffect } from 'react';
import { projectsApi, usersApi } from '../api/client';

function Projects({ users, onRefresh }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  
  // Form state
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    owner_id: '',
    hourly_rate: 100,
    budget: '',
    status: 'active'
  });

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const response = await projectsApi.getAll();
      setProjects(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching projects:', err);
      setError('Failed to load projects');
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
        owner_id: parseInt(formData.owner_id),
        hourly_rate: parseFloat(formData.hourly_rate),
        budget: formData.budget ? parseFloat(formData.budget) : null
      };
      
      await projectsApi.create(submitData);
      setSuccessMessage('Project created successfully!');
      setShowForm(false);
      setFormData({
        name: '',
        description: '',
        owner_id: '',
        hourly_rate: 100,
        budget: '',
        status: 'active'
      });
      onRefresh();
      fetchProjects();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Error creating project:', err);
      setError('Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this project? All tasks and time entries will be deleted.')) {
      return;
    }
    
    try {
      await projectsApi.delete(id);
      setSuccessMessage('Project deleted successfully!');
      onRefresh();
      fetchProjects();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Error deleting project:', err);
      setError('Failed to delete project');
    }
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
          <h2>📁 Projects</h2>
          <button 
            className="btn btn-primary" 
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? 'Cancel' : '+ New Project'}
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleSubmit} style={{ marginBottom: '20px' }}>
            <div className="form-group">
              <label>Project Name *</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
                placeholder="Enter project name"
              />
            </div>
            
            <div className="form-group">
              <label>Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                rows="3"
                placeholder="Project description"
              />
            </div>

            <div className="form-group">
              <label>Owner *</label>
              <select
                name="owner_id"
                value={formData.owner_id}
                onChange={handleInputChange}
                required
              >
                <option value="">Select an owner</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>{user.username} ({user.email})</option>
                ))}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
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
                <label>Budget ($)</label>
                <input
                  type="number"
                  name="budget"
                  value={formData.budget}
                  onChange={handleInputChange}
                  min="0"
                  step="0.01"
                  placeholder="Optional"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Status</label>
              <select
                name="status"
                value={formData.status}
                onChange={handleInputChange}
              >
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="on-hold">On Hold</option>
              </select>
            </div>

            <button type="submit" className="btn btn-success" disabled={loading}>
              {loading ? 'Creating...' : 'Create Project'}
            </button>
          </form>
        )}

        {users.length === 0 && (
          <div className="error">
            No users found. Please note: The API requires a user to exist before creating a project.
            You may need to create a user directly via the API first using POST /api/users/
          </div>
        )}

        {loading && !showForm && <div className="loading">Loading projects...</div>}
        
        {!loading && projects.length === 0 && !showForm && (
          <p>No projects yet. Click "+ New Project" to create one.</p>
        )}

        {!loading && projects.length > 0 && (
          <ul className="item-list">
            {projects.map(project => (
              <li key={project.id} className="item-card">
                <h3>{project.name}</h3>
                <p>{project.description || 'No description'}</p>
                <div className="item-meta">
                  <span className={`badge badge-${project.status === 'active' ? 'active' : 'pending'}`}>
                    {project.status}
                  </span>
                  <span>Rate: ${project.hourly_rate}/hr</span>
                  {project.budget && <span>Budget: ${project.budget}</span>}
                  {project.total_time_seconds !== undefined && (
                    <span>Tracked: {formatTime(project.total_time_seconds)}</span>
                  )}
                  {project.total_cost !== undefined && (
                    <span>Cost: ${project.total_cost.toFixed(2)}</span>
                  )}
                </div>
                <div className="actions">
                  <button 
                    className="btn btn-danger" 
                    onClick={() => handleDelete(project.id)}
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

export default Projects;
