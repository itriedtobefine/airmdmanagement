import React, { useState } from 'react';
import { tablesApi } from '../api/api';

function CreateTableModal({ onClose, onTableCreated }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Table name is required');
      return;
    }

    setLoading(true);
    try {
      await tablesApi.create({ name, description });
      onTableCreated();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create table');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.modalOverlay}>
      <div style={styles.modal}>
        <h2>Create New Table</h2>
        <form onSubmit={handleSubmit}>
          <div style={styles.formGroup}>
            <label>Table Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter table name"
              style={styles.input}
            />
          </div>
          <div style={styles.formGroup}>
            <label>Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter description"
              style={styles.textarea}
            />
          </div>
          {error && <p style={styles.error}>{error}</p>}
          <div style={styles.buttons}>
            <button type="button" onClick={onClose} style={styles.cancelBtn}>
              Cancel
            </button>
            <button type="submit" disabled={loading} style={styles.submitBtn}>
              {loading ? 'Creating...' : 'Create Table'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const styles = {
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    backgroundColor: 'white',
    padding: '24px',
    borderRadius: '8px',
    width: '500px',
    maxWidth: '90%',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
  },
  formGroup: {
    marginBottom: '16px',
  },
  input: {
    width: '100%',
    padding: '8px 12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '14px',
    marginTop: '4px',
  },
  textarea: {
    width: '100%',
    padding: '8px 12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '14px',
    marginTop: '4px',
    minHeight: '80px',
    resize: 'vertical',
  },
  error: {
    color: '#dc3545',
    fontSize: '14px',
    marginBottom: '16px',
  },
  buttons: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '8px',
  },
  cancelBtn: {
    padding: '8px 16px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    backgroundColor: 'white',
    cursor: 'pointer',
  },
  submitBtn: {
    padding: '8px 16px',
    border: 'none',
    borderRadius: '4px',
    backgroundColor: '#1a73e8',
    color: 'white',
    cursor: 'pointer',
  },
};

export default CreateTableModal;
