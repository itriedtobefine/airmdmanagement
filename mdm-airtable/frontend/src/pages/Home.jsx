import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { tablesApi } from '../api/api';
import CreateTableModal from '../components/CreateTableModal';

function Home() {
  const navigate = useNavigate();
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    loadTables();
  }, []);

  const loadTables = async () => {
    try {
      setLoading(true);
      const response = await tablesApi.getAll();
      setTables(response.data);
    } catch (err) {
      console.error('Failed to load tables:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTable = async (tableId, e) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this table? This action cannot be undone.')) {
      try {
        await tablesApi.delete(tableId);
        loadTables();
      } catch (err) {
        alert('Failed to delete table: ' + (err.response?.data?.detail || err.message));
      }
    }
  };

  if (loading) {
    return <div style={styles.loading}>Loading...</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>MDM AirTable Clone</h1>
        <p style={styles.subtitle}>Master Data Management System</p>
      </div>

      <div style={styles.toolbar}>
        <button onClick={() => setShowCreateModal(true)} style={styles.createBtn}>
          + Create New Table
        </button>
      </div>

      <div style={styles.tablesGrid}>
        {tables.length === 0 ? (
          <div style={styles.emptyState}>
            <p>No tables yet. Create your first table to get started!</p>
          </div>
        ) : (
          tables.map((table) => (
            <div
              key={table.id}
              style={styles.tableCard}
              onClick={() => navigate(`/table/${table.id}`)}
            >
              <div style={styles.cardHeader}>
                <h3 style={styles.cardTitle}>{table.name}</h3>
                <button
                  onClick={(e) => handleDeleteTable(table.id, e)}
                  style={styles.deleteBtn}
                  title="Delete table"
                >
                  🗑️
                </button>
              </div>
              {table.description && (
                <p style={styles.cardDescription}>{table.description}</p>
              )}
              <div style={styles.cardFooter}>
                <span style={styles.cardDate}>
                  Created: {new Date(table.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {showCreateModal && (
        <CreateTableModal
          onClose={() => setShowCreateModal(false)}
          onTableCreated={() => {
            setShowCreateModal(false);
            loadTables();
          }}
        />
      )}
    </div>
  );
}

const styles = {
  container: {
    padding: '20px',
    maxWidth: '1200px',
    margin: '0 auto',
  },
  header: {
    marginBottom: '30px',
  },
  title: {
    fontSize: '32px',
    fontWeight: 'bold',
    color: '#1a1a1a',
    marginBottom: '8px',
  },
  subtitle: {
    fontSize: '16px',
    color: '#666',
  },
  toolbar: {
    marginBottom: '24px',
  },
  createBtn: {
    padding: '12px 24px',
    border: 'none',
    borderRadius: '6px',
    backgroundColor: '#1a73e8',
    color: 'white',
    fontSize: '16px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  tablesGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: '20px',
  },
  tableCard: {
    backgroundColor: 'white',
    border: '1px solid #e0e0e0',
    borderRadius: '8px',
    padding: '20px',
    cursor: 'pointer',
    transition: 'box-shadow 0.2s, transform 0.2s',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '12px',
  },
  cardTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#1a1a1a',
    margin: 0,
  },
  cardDescription: {
    fontSize: '14px',
    color: '#666',
    marginBottom: '16px',
    lineHeight: '1.5',
  },
  cardFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: '12px',
    borderTop: '1px solid #f0f0f0',
  },
  cardDate: {
    fontSize: '12px',
    color: '#999',
  },
  deleteBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: '18px',
    padding: '4px',
    opacity: 0.6,
    transition: 'opacity 0.2s',
  },
  emptyState: {
    gridColumn: '1 / -1',
    textAlign: 'center',
    padding: '60px 20px',
    color: '#666',
    fontSize: '16px',
    backgroundColor: '#f9f9f9',
    borderRadius: '8px',
  },
  loading: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '200px',
    fontSize: '18px',
    color: '#666',
  },
};

export default Home;
