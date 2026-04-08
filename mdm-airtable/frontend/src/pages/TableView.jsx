import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { tablesApi, columnsApi, recordsApi } from '../api/api';
import CreateColumnModal from '../components/CreateColumnModal';

function TableView() {
  const { tableId } = useParams();
  const navigate = useNavigate();
  const [table, setTable] = useState(null);
  const [columns, setColumns] = useState([]);
  const [records, setRecords] = useState([]);
  const [allTables, setAllTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showColumnModal, setShowColumnModal] = useState(false);
  const [showAdminPanel, setShowAdminPanel] = useState(false);
  const [editingCell, setEditingCell] = useState(null);
  const [cellValue, setCellValue] = useState('');
  const [skip, setSkip] = useState(0);
  const limit = 100;

  useEffect(() => {
    loadData();
  }, [tableId, skip]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [tableRes, columnsRes, recordsRes, tablesRes] = await Promise.all([
        tablesApi.getById(tableId),
        tablesApi.getColumns(tableId),
        tablesApi.getRecords(tableId, skip, limit),
        tablesApi.getAll(),
      ]);
      setTable(tableRes.data);
      setColumns(columnsRes.data);
      setRecords(recordsRes.data);
      setAllTables(tablesRes.data);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTable = async () => {
    if (window.confirm('Are you sure you want to delete this table? This action cannot be undone.')) {
      try {
        await tablesApi.delete(tableId);
        navigate('/');
      } catch (err) {
        alert('Failed to delete table: ' + (err.response?.data?.detail || err.message));
      }
    }
  };

  const handleDeleteColumn = async (columnId) => {
    if (window.confirm('Are you sure you want to delete this column?')) {
      try {
        await columnsApi.delete(columnId);
        loadData();
      } catch (err) {
        alert('Failed to delete column: ' + (err.response?.data?.detail || err.message));
      }
    }
  };

  const handleCellClick = (record, column) => {
    const cell = record.values.find(v => v.column_id === column.id);
    setEditingCell({ recordId: record.id, columnId: column.id });
    setCellValue(cell?.value ?? '');
  };

  const handleCellSave = async () => {
    try {
      await recordsApi.update(editingCell.recordId, {
        values: [{ column_id: editingCell.columnId, value: cellValue }],
      });
      setEditingCell(null);
      loadData();
    } catch (err) {
      alert('Failed to update cell: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleAddRecord = async () => {
    try {
      await recordsApi.create({ table_id: parseInt(tableId), values: [] });
      loadData();
    } catch (err) {
      alert('Failed to add record: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDeleteRecord = async (recordId) => {
    if (window.confirm('Are you sure you want to delete this record?')) {
      try {
        await recordsApi.delete(recordId);
        loadData();
      } catch (err) {
        alert('Failed to delete record: ' + (err.response?.data?.detail || err.message));
      }
    }
  };

  const handleExportCSV = async () => {
    try {
      const response = await tablesApi.exportCSV(tableId);
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${table.name}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Failed to export CSV: ' + err.message);
    }
  };

  const handleImportCSV = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      const result = await tablesApi.importCSV(tableId, file);
      alert(`Imported ${result.data.imported} records. ${result.data.errors.length > 0 ? 'Errors: ' + result.data.errors.slice(0, 3).join(', ') : ''}`);
      loadData();
    } catch (err) {
      alert('Failed to import CSV: ' + (err.response?.data?.detail || err.message));
    }
  };

  const getCellValue = (record, column) => {
    const cell = record.values.find(v => v.column_id === column.id);
    return cell?.value ?? '';
  };

  const renderCell = (value, column) => {
    if (value === null || value === '') return '';
    
    switch (column.column_type) {
      case 'boolean':
        return value ? '✓' : '';
      case 'date':
        return new Date(value).toLocaleDateString();
      default:
        return String(value);
    }
  };

  if (loading) {
    return <div style={styles.loading}>Loading...</div>;
  }

  if (!table) {
    return <div style={styles.error}>Table not found</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <button onClick={() => navigate('/')} style={styles.backBtn}>← Back</button>
          <h1 style={styles.title}>{table.name}</h1>
          {table.description && <p style={styles.description}>{table.description}</p>}
        </div>
        <div style={styles.headerActions}>
          <label style={styles.actionBtn}>
            Import CSV
            <input type="file" accept=".csv" onChange={handleImportCSV} style={{ display: 'none' }} />
          </label>
          <button onClick={handleExportCSV} style={styles.actionBtn}>Export CSV</button>
          <button 
            onClick={() => setShowAdminPanel(!showAdminPanel)} 
            style={{...styles.actionBtn, ...styles.adminBtn}}
          >
            ⚙️ Administration
          </button>
        </div>
      </div>

      {showAdminPanel && (
        <div style={styles.adminPanel}>
          <h3>Table Administration</h3>
          <div style={styles.adminActions}>
            <button onClick={handleDeleteTable} style={styles.dangerBtn}>
              🗑️ Delete Table
            </button>
          </div>
          <h4>Columns</h4>
          <div style={styles.columnsList}>
            {columns.map((col) => (
              <div key={col.id} style={styles.columnItem}>
                <span>
                  <strong>{col.name}</strong> ({col.column_type})
                  {col.is_required && ' *'}
                  {col.is_unique && ' 🔒'}
                </span>
                <button onClick={() => handleDeleteColumn(col.id)} style={styles.deleteBtn}>
                  Delete
                </button>
              </div>
            ))}
          </div>
          <button onClick={() => setShowColumnModal(true)} style={styles.primaryBtn}>
            + Add Column
          </button>
          <button onClick={() => setShowAdminPanel(false)} style={styles.secondaryBtn}>
            Close Administration
          </button>
        </div>
      )}

      <div style={styles.tableContainer}>
        <table style={styles.table}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.id} style={styles.th}>
                  {col.name}
                  {col.is_required && <span style={styles.required}>*</span>}
                </th>
              ))}
              <th style={styles.th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.id} style={styles.tr}>
                {columns.map((col) => (
                  <td 
                    key={col.id} 
                    style={styles.td}
                    onClick={() => handleCellClick(record, col)}
                  >
                    {editingCell?.recordId === record.id && editingCell?.columnId === col.id ? (
                      <div style={styles.editCell}>
                        {col.column_type === 'boolean' ? (
                          <select
                            value={cellValue ? 'true' : 'false'}
                            onChange={(e) => setCellValue(e.target.value === 'true')}
                            style={styles.cellInput}
                            onBlur={handleCellSave}
                            autoFocus
                          >
                            <option value="false">False</option>
                            <option value="true">True</option>
                          </select>
                        ) : (
                          <input
                            type={col.column_type === 'number' ? 'number' : 'text'}
                            value={cellValue}
                            onChange={(e) => setCellValue(e.target.value)}
                            style={styles.cellInput}
                            onBlur={handleCellSave}
                            onKeyDown={(e) => e.key === 'Enter' && handleCellSave()}
                            autoFocus
                          />
                        )}
                      </div>
                    ) : (
                      renderCell(getCellValue(record, col), col)
                    )}
                  </td>
                ))}
                <td style={styles.td}>
                  <button onClick={() => handleDeleteRecord(record.id)} style={styles.deleteBtn}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={styles.footer}>
        <button onClick={handleAddRecord} style={styles.primaryBtn}>
          + Add Record
        </button>
        <span style={styles.recordCount}>
          Showing {records.length} records
          {records.length === limit && (
            <button onClick={() => setSkip(skip + limit)} style={styles.loadMoreBtn}>
              Load More
            </button>
          )}
        </span>
      </div>

      {showColumnModal && (
        <CreateColumnModal
          tableId={parseInt(tableId)}
          onClose={() => setShowColumnModal(false)}
          onColumnCreated={() => {
            setShowColumnModal(false);
            loadData();
          }}
          existingTables={allTables}
        />
      )}
    </div>
  );
}

const styles = {
  container: {
    padding: '20px',
    maxWidth: '1400px',
    margin: '0 auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '20px',
  },
  title: {
    fontSize: '24px',
    fontWeight: 'bold',
    margin: '8px 0',
  },
  description: {
    color: '#666',
    fontSize: '14px',
  },
  backBtn: {
    padding: '6px 12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    backgroundColor: 'white',
    cursor: 'pointer',
  },
  headerActions: {
    display: 'flex',
    gap: '8px',
  },
  actionBtn: {
    padding: '8px 16px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    backgroundColor: 'white',
    cursor: 'pointer',
    fontSize: '14px',
  },
  adminBtn: {
    backgroundColor: '#f0f0f0',
  },
  adminPanel: {
    backgroundColor: '#f9f9f9',
    padding: '20px',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  adminActions: {
    marginBottom: '20px',
  },
  columnsList: {
    marginBottom: '16px',
  },
  columnItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 0',
    borderBottom: '1px solid #eee',
  },
  primaryBtn: {
    padding: '8px 16px',
    border: 'none',
    borderRadius: '4px',
    backgroundColor: '#1a73e8',
    color: 'white',
    cursor: 'pointer',
    marginRight: '8px',
  },
  secondaryBtn: {
    padding: '8px 16px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    backgroundColor: 'white',
    cursor: 'pointer',
  },
  dangerBtn: {
    padding: '8px 16px',
    border: 'none',
    borderRadius: '4px',
    backgroundColor: '#dc3545',
    color: 'white',
    cursor: 'pointer',
  },
  deleteBtn: {
    padding: '4px 8px',
    border: '1px solid #dc3545',
    borderRadius: '4px',
    backgroundColor: 'white',
    color: '#dc3545',
    cursor: 'pointer',
    fontSize: '12px',
  },
  tableContainer: {
    overflowX: 'auto',
    marginBottom: '20px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  th: {
    textAlign: 'left',
    padding: '12px',
    borderBottom: '2px solid #ddd',
    backgroundColor: '#f5f5f5',
    fontWeight: '600',
  },
  tr: {
    borderBottom: '1px solid #eee',
  },
  td: {
    padding: '12px',
    cursor: 'pointer',
    minWidth: '150px',
  },
  editCell: {
    width: '100%',
  },
  cellInput: {
    width: '100%',
    padding: '4px 8px',
    border: '2px solid #1a73e8',
    borderRadius: '4px',
    fontSize: '14px',
  },
  required: {
    color: '#dc3545',
    marginLeft: '4px',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  recordCount: {
    color: '#666',
    fontSize: '14px',
  },
  loadMoreBtn: {
    marginLeft: '12px',
    padding: '4px 12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    backgroundColor: 'white',
    cursor: 'pointer',
  },
  loading: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '200px',
    fontSize: '18px',
    color: '#666',
  },
  error: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '200px',
    fontSize: '18px',
    color: '#dc3545',
  },
};

export default TableView;
