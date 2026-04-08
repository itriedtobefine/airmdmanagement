import React, { useState } from 'react';
import { columnsApi } from '../api/api';

const COLUMN_TYPES = [
  { value: 'text', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'date', label: 'Date' },
  { value: 'boolean', label: 'Checkbox' },
  { value: 'single_select', label: 'Single Select' },
  { value: 'multi_select', label: 'Multi Select' },
  { value: 'link_to_record', label: 'Link to Record' },
];

function CreateColumnModal({ tableId, onClose, onColumnCreated, existingTables = [] }) {
  const [name, setName] = useState('');
  const [columnType, setColumnType] = useState('text');
  const [isRequired, setIsRequired] = useState(false);
  const [isUnique, setIsUnique] = useState(false);
  const [defaultValue, setDefaultValue] = useState('');
  const [validationRule, setValidationRule] = useState('');
  const [options, setOptions] = useState('');
  const [linkedTableId, setLinkedTableId] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Column name is required');
      return;
    }

    setLoading(true);
    try {
      let optionsValue = null;
      if (columnType === 'single_select' || columnType === 'multi_select') {
        // Parse comma-separated options
        const opts = options.split(',').map(o => o.trim()).filter(o => o);
        optionsValue = opts;
      } else if (columnType === 'link_to_record') {
        optionsValue = parseInt(linkedTableId);
      }

      await columnsApi.create({
        table_id: tableId,
        name,
        column_type: columnType,
        is_required: isRequired,
        is_unique: isUnique,
        default_value: defaultValue || null,
        validation_rule: validationRule || null,
        options: optionsValue,
        position: 0,
      });
      onColumnCreated();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create column');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.modalOverlay}>
      <div style={styles.modal}>
        <h2>Create New Column</h2>
        <form onSubmit={handleSubmit}>
          <div style={styles.formGroup}>
            <label>Column Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter column name"
              style={styles.input}
            />
          </div>

          <div style={styles.formGroup}>
            <label>Column Type *</label>
            <select
              value={columnType}
              onChange={(e) => setColumnType(e.target.value)}
              style={styles.input}
            >
              {COLUMN_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          {(columnType === 'single_select' || columnType === 'multi_select') && (
            <div style={styles.formGroup}>
              <label>Options (comma-separated)</label>
              <input
                type="text"
                value={options}
                onChange={(e) => setOptions(e.target.value)}
                placeholder="Option1, Option2, Option3"
                style={styles.input}
              />
            </div>
          )}

          {columnType === 'link_to_record' && (
            <div style={styles.formGroup}>
              <label>Link to Table</label>
              <select
                value={linkedTableId}
                onChange={(e) => setLinkedTableId(e.target.value)}
                style={styles.input}
              >
                <option value="">Select a table</option>
                {existingTables.map((table) => (
                  <option key={table.id} value={table.id}>
                    {table.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div style={styles.checkboxGroup}>
            <label style={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={isRequired}
                onChange={(e) => setIsRequired(e.target.checked)}
              />
              Required field
            </label>
          </div>

          <div style={styles.checkboxGroup}>
            <label style={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={isUnique}
                onChange={(e) => setIsUnique(e.target.checked)}
              />
              Unique values
            </label>
          </div>

          <div style={styles.formGroup}>
            <label>Default Value</label>
            <input
              type="text"
              value={defaultValue}
              onChange={(e) => setDefaultValue(e.target.value)}
              placeholder="Enter default value"
              style={styles.input}
            />
          </div>

          <div style={styles.formGroup}>
            <label>Validation Rule (Regex)</label>
            <input
              type="text"
              value={validationRule}
              onChange={(e) => setValidationRule(e.target.value)}
              placeholder="e.g., ^[A-Z]{3}-\d{4}$"
              style={styles.input}
            />
          </div>

          {error && <p style={styles.error}>{error}</p>}

          <div style={styles.buttons}>
            <button type="button" onClick={onClose} style={styles.cancelBtn}>
              Cancel
            </button>
            <button type="submit" disabled={loading} style={styles.submitBtn}>
              {loading ? 'Creating...' : 'Create Column'}
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
    maxHeight: '90vh',
    overflowY: 'auto',
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
  checkboxGroup: {
    marginBottom: '12px',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    cursor: 'pointer',
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
    marginTop: '20px',
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

export default CreateColumnModal;
