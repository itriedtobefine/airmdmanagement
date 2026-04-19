#!/usr/bin/env python3
"""
Database Table Editor Application
Single-file application with FastAPI backend, PostgreSQL integration, and JS UI
License: MIT
"""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import sql, extras
from psycopg2.extensions import connection as PgConnection
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from uvicorn import run


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class DBConfig:
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "appdb"
    user: str = "appuser"
    password: str = "apppass"


DB_CONFIG = DBConfig()


# =============================================================================
# DATABASE CONNECTION MANAGER
# =============================================================================

class DatabaseManager:
    """Manages PostgreSQL connections and operations"""
    
    def __init__(self, config: DBConfig):
        self.config = config
        self._conn: Optional[PgConnection] = None
    
    def get_connection(self) -> PgConnection:
        """Get or create database connection"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password
            )
            self._conn.autocommit = False
        return self._conn
    
    def close(self):
        """Close database connection"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results"""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute(query, params)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    result = []
                    for row in rows:
                        row_dict = {}
                        for col in columns:
                            val = row[col]
                            if isinstance(val, bytes):
                                val = val.decode('utf-8', errors='replace')
                            elif hasattr(val, 'isoformat'):
                                val = val.isoformat()
                            row_dict[col] = val
                        result.append(row_dict)
                    return result
                return []
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")
    
    def execute_command(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE command and return affected rows"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                affected = cur.rowcount if cur.rowcount >= 0 else 0
                conn.commit()
                return affected
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=f"Command error: {str(e)}")
    
    def get_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        results = self.execute_query(query)
        return [row['table_name'] for row in results]
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column schema for a table"""
        query = """
            SELECT column_name, data_type, is_nullable, character_maximum_length,
                   numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """
        return self.execute_query(query, (table_name,))
    
    def get_primary_keys(self, table_name: str) -> List[str]:
        """Get primary key columns for a table"""
        query = """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_schema = 'public' 
              AND tc.table_name = %s 
              AND tc.constraint_type = 'PRIMARY KEY'
        """
        results = self.execute_query(query, (table_name,))
        return [row['column_name'] for row in results]
    
    def get_table_data(self, table_name: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get paginated data from a table"""
        if not self._is_valid_identifier(table_name):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        schema = self.get_table_schema(table_name)
        primary_keys = self.get_primary_keys(table_name)
        
        conn = self.get_connection()
        order_by = ", ".join(primary_keys) if primary_keys else schema[0]['column_name'] if schema else "1"
        
        count_query = sql.SQL("SELECT COUNT(*) FROM {table}").format(
            table=sql.Identifier(table_name)
        )
        count_result = self.execute_query(count_query.as_string(conn))
        total = count_result[0]['count'] if count_result else 0
        
        data_query = sql.SQL("SELECT * FROM {table} ORDER BY {order} LIMIT %s OFFSET %s").format(
            table=sql.Identifier(table_name),
            order=sql.SQL(order_by)
        )
        data = self.execute_query(data_query.as_string(conn), (limit, offset))
        
        return {
            "table": table_name,
            "columns": schema,
            "primary_keys": primary_keys,
            "data": data,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    def insert_row(self, table_name: str, data: Dict[str, Any]) -> bool:
        """Insert a new row into a table"""
        if not self._is_valid_identifier(table_name):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        columns = list(data.keys())
        values = list(data.values())
        
        if not columns:
            raise HTTPException(status_code=400, detail="No columns provided")
        
        conn = self.get_connection()
        query = sql.SQL("INSERT INTO {table} ({fields}) VALUES ({values})").format(
            table=sql.Identifier(table_name),
            fields=sql.SQL(", ").join(sql.Identifier(col) for col in columns),
            values=sql.SQL(", ").join(sql.Placeholder() for _ in columns)
        )
        
        self.execute_command(query.as_string(conn), tuple(values))
        return True
    
    def update_row(self, table_name: str, pk_values: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Update an existing row in a table"""
        if not self._is_valid_identifier(table_name):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        if not pk_values:
            raise HTTPException(status_code=400, detail="Primary key values required")
        
        conn = self.get_connection()
        set_clauses = []
        params = []
        
        for col, val in data.items():
            set_clauses.append(f"{sql.Identifier(col).as_string(conn)} = %s")
            params.append(val)
        
        where_clauses = []
        for col, val in pk_values.items():
            where_clauses.append(f"{sql.Identifier(col).as_string(conn)} = %s")
            params.append(val)
        
        query = f"UPDATE {sql.Identifier(table_name).as_string(conn)} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
        
        self.execute_command(query, tuple(params))
        return True
    
    def delete_row(self, table_name: str, pk_values: Dict[str, Any]) -> bool:
        """Delete a row from a table"""
        if not self._is_valid_identifier(table_name):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        if not pk_values:
            raise HTTPException(status_code=400, detail="Primary key values required")
        
        conn = self.get_connection()
        where_clauses = []
        params = []
        
        for col, val in pk_values.items():
            where_clauses.append(f"{sql.Identifier(col).as_string(conn)} = %s")
            params.append(val)
        
        query = f"DELETE FROM {sql.Identifier(table_name).as_string(conn)} WHERE {' AND '.join(where_clauses)}"
        
        self.execute_command(query, tuple(params))
        return True
    
    def create_table(self, table_name: str, columns: List[Dict[str, Any]]) -> bool:
        """Create a new table"""
        if not self._is_valid_identifier(table_name):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        column_defs = []
        for col in columns:
            col_name = col.get('name')
            col_type = col.get('type', 'TEXT')
            is_pk = col.get('primary_key', False)
            is_nullable = col.get('nullable', True)
            
            if not self._is_valid_identifier(col_name):
                raise HTTPException(status_code=400, detail=f"Invalid column name: {col_name}")
            
            col_def = f"{sql.Identifier(col_name).as_string(self.get_connection())} {col_type}"
            if is_pk:
                col_def += " PRIMARY KEY"
            elif not is_nullable:
                col_def += " NOT NULL"
            
            column_defs.append(col_def)
        
        query = f"CREATE TABLE {sql.Identifier(table_name).as_string(self.get_connection())} ({', '.join(column_defs)})"
        
        self.execute_command(query)
        return True
    
    def drop_table(self, table_name: str) -> bool:
        """Drop a table"""
        if not self._is_valid_identifier(table_name):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        query = f"DROP TABLE {sql.Identifier(table_name).as_string(self.get_connection())} CASCADE"
        self.execute_command(query)
        return True
    
    def execute_custom_sql(self, query: str) -> Dict[str, Any]:
        """Execute custom SQL query"""
        query_lower = query.strip().lower()
        
        if query_lower.startswith(('insert', 'update', 'delete', 'create', 'drop', 'alter', 'truncate')):
            affected = self.execute_command(query)
            return {"affected_rows": affected, "type": "command"}
        elif query_lower.startswith('select'):
            data = self.execute_query(query)
            return {"data": data, "type": "query", "count": len(data)}
        else:
            raise HTTPException(status_code=400, detail="Unsupported SQL command type")
    
    @staticmethod
    def _is_valid_identifier(name: str) -> bool:
        """Check if name is a valid SQL identifier"""
        if not name:
            return False
        if not name[0].isalpha() and name[0] != '_':
            return False
        for char in name:
            if not (char.isalnum() or char == '_'):
                return False
        return len(name) <= 63


# =============================================================================
# HTML TEMPLATE
# =============================================================================

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database Table Editor</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header { background: #2c3e50; color: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; }
        header h1 { font-size: 24px; margin-bottom: 10px; }
        .toolbar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
        .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; transition: background 0.2s; }
        .btn-primary { background: #3498db; color: white; }
        .btn-primary:hover { background: #2980b9; }
        .btn-success { background: #27ae60; color: white; }
        .btn-success:hover { background: #219a52; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-danger:hover { background: #c0392b; }
        .btn-secondary { background: #95a5a6; color: white; }
        .btn-secondary:hover { background: #7f8c8d; }
        select, input[type="text"], input[type="number"] { padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        .panel { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .panel h2 { font-size: 18px; margin-bottom: 15px; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .table-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
        .table-item { padding: 12px; background: #ecf0f1; border-radius: 4px; cursor: pointer; transition: background 0.2s; }
        .table-item:hover { background: #3498db; color: white; }
        .table-item.active { background: #3498db; color: white; }
        .data-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        .data-table th, .data-table td { padding: 10px; text-align: left; border: 1px solid #ddd; }
        .data-table th { background: #34495e; color: white; position: sticky; top: 0; }
        .data-table tr:nth-child(even) { background: #f9f9f9; }
        .data-table tr:hover { background: #e8f4f8; }
        .data-table input, .data-table select { width: 100%; padding: 6px; border: 1px solid #ddd; border-radius: 3px; }
        .pagination { display: flex; justify-content: center; gap: 10px; margin-top: 20px; align-items: center; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; }
        .modal.show { display: flex; justify-content: center; align-items: center; }
        .modal-content { background: white; padding: 30px; border-radius: 8px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .modal-header h3 { font-size: 20px; }
        .close-btn { background: none; border: none; font-size: 24px; cursor: pointer; color: #999; }
        .close-btn:hover { color: #333; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 500; }
        .form-group input, .form-group select { width: 100%; }
        .sql-editor { width: 100%; height: 200px; font-family: monospace; font-size: 14px; padding: 12px; border: 1px solid #ddd; border-radius: 4px; resize: vertical; }
        .alert { padding: 12px 20px; border-radius: 4px; margin-bottom: 15px; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .loading { text-align: center; padding: 40px; color: #666; }
        .hidden { display: none; }
        .action-cell { white-space: nowrap; }
        .checkbox-cell { width: 40px; text-align: center; }
        #customSqlPanel { display: none; }
        .schema-info { font-size: 12px; color: #666; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🗄️ Database Table Editor</h1>
            <div class="toolbar">
                <select id="tableSelect">
                    <option value="">-- Select a table --</option>
                </select>
                <button class="btn btn-primary" onclick="loadTableData()">Load Table</button>
                <button class="btn btn-success" onclick="showCreateTableModal()">+ Create Table</button>
                <button class="btn btn-secondary" onclick="toggleSqlEditor()">SQL Query</button>
                <button class="btn btn-secondary" onclick="refreshTables()">Refresh Tables</button>
            </div>
        </header>

        <div id="alertContainer"></div>

        <div class="panel" id="customSqlPanel">
            <h2>Custom SQL Query</h2>
            <textarea id="sqlQuery" class="sql-editor" placeholder="Enter your SQL query here..."></textarea>
            <div style="margin-top: 15px;">
                <button class="btn btn-primary" onclick="executeSql()">Execute</button>
                <button class="btn btn-secondary" onclick="toggleSqlEditor()">Close</button>
            </div>
            <div id="sqlResults" class="hidden" style="margin-top: 20px;"></div>
        </div>

        <div class="panel" id="tablesPanel">
            <h2>Available Tables</h2>
            <div id="tableList" class="table-list"></div>
        </div>

        <div class="panel hidden" id="dataPanel">
            <h2 id="currentTableName">Table Data</h2>
            <div class="toolbar" style="margin-bottom: 15px;">
                <button class="btn btn-success" onclick="showAddRowModal()">+ Add Row</button>
                <button class="btn btn-danger" onclick="deleteSelectedRows()">Delete Selected</button>
                <span id="recordCount" style="margin-left: auto; color: #666;"></span>
            </div>
            <div id="tableDataContainer"></div>
            <div class="pagination" id="pagination"></div>
        </div>
    </div>

    <!-- Create Table Modal -->
    <div id="createTableModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Create New Table</h3>
                <button class="close-btn" onclick="closeModal('createTableModal')">&times;</button>
            </div>
            <div class="form-group">
                <label>Table Name</label>
                <input type="text" id="newTableName" placeholder="my_table">
            </div>
            <div id="columnDefinitions">
                <h4>Columns</h4>
                <div class="column-def" style="display: flex; gap: 10px; margin-bottom: 10px;">
                    <input type="text" placeholder="Column name" class="col-name" style="flex: 2;">
                    <select class="col-type" style="flex: 1;">
                        <option value="INTEGER">INTEGER</option>
                        <option value="VARCHAR(255)">VARCHAR</option>
                        <option value="TEXT">TEXT</option>
                        <option value="BOOLEAN">BOOLEAN</option>
                        <option value="DATE">DATE</option>
                        <option value="TIMESTAMP">TIMESTAMP</option>
                        <option value="DECIMAL(10,2)">DECIMAL</option>
                    </select>
                    <label><input type="checkbox" class="col-pk"> PK</label>
                    <label><input type="checkbox" class="col-notnull" checked> NOT NULL</label>
                </div>
            </div>
            <button class="btn btn-secondary" onclick="addColumnDef()" style="margin: 10px 0;">+ Add Column</button>
            <div style="margin-top: 20px;">
                <button class="btn btn-success" onclick="createTable()">Create Table</button>
                <button class="btn btn-secondary" onclick="closeModal('createTableModal')">Cancel</button>
            </div>
        </div>
    </div>

    <!-- Add/Edit Row Modal -->
    <div id="rowModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="rowModalTitle">Add New Row</h3>
                <button class="close-btn" onclick="closeModal('rowModal')">&times;</button>
            </div>
            <div id="rowForm"></div>
            <div style="margin-top: 20px;">
                <button class="btn btn-success" onclick="saveRow()">Save</button>
                <button class="btn btn-secondary" onclick="closeModal('rowModal')">Cancel</button>
            </div>
        </div>
    </div>

    <script>
        let currentTable = null;
        let currentPage = 0;
        const pageSize = 50;
        let tableSchema = [];
        let primaryKeys = [];
        let selectedRows = new Set();

        // Initialize app
        document.addEventListener('DOMContentLoaded', () => {
            refreshTables();
        });

        function showAlert(message, type = 'success') {
            const container = document.getElementById('alertContainer');
            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.textContent = message;
            container.appendChild(alert);
            setTimeout(() => alert.remove(), 5000);
        }

        async function apiRequest(endpoint, method = 'GET', data = null) {
            const options = {
                method,
                headers: { 'Content-Type': 'application/json' }
            };
            if (data) options.body = JSON.stringify(data);
            
            const response = await fetch(endpoint, options);
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail || 'Request failed');
            }
            return result;
        }

        async function refreshTables() {
            try {
                const tables = await apiRequest('/api/tables');
                const tableList = document.getElementById('tableList');
                const tableSelect = document.getElementById('tableSelect');
                
                tableList.innerHTML = '';
                tableSelect.innerHTML = '<option value="">-- Select a table --</option>';
                
                tables.forEach(table => {
                    const item = document.createElement('div');
                    item.className = 'table-item';
                    item.textContent = table;
                    item.onclick = () => selectTable(table);
                    tableList.appendChild(item);
                    
                    const option = document.createElement('option');
                    option.value = table;
                    option.textContent = table;
                    tableSelect.appendChild(option);
                });
            } catch (error) {
                showAlert('Failed to load tables: ' + error.message, 'error');
            }
        }

        function selectTable(tableName) {
            currentTable = tableName;
            document.querySelectorAll('.table-item').forEach(item => {
                item.classList.toggle('active', item.textContent === tableName);
            });
            document.getElementById('tableSelect').value = tableName;
            loadTableData();
        }

        async function loadTableData() {
            if (!currentTable) {
                showAlert('Please select a table', 'error');
                return;
            }
            
            try {
                const result = await apiRequest(`/api/table/${encodeURIComponent(currentTable)}?limit=${pageSize}&offset=${currentPage * pageSize}`);
                
                tableSchema = result.columns;
                primaryKeys = result.primary_keys;
                
                document.getElementById('currentTableName').textContent = `Table: ${result.table}`;
                document.getElementById('recordCount').textContent = `Total records: ${result.total}`;
                document.getElementById('tablesPanel').classList.add('hidden');
                document.getElementById('dataPanel').classList.remove('hidden');
                
                renderTable(result);
                renderPagination(result.total, result.limit, result.offset);
            } catch (error) {
                showAlert('Failed to load table data: ' + error.message, 'error');
            }
        }

        function renderTable(result) {
            const container = document.getElementById('tableDataContainer');
            
            if (result.data.length === 0) {
                container.innerHTML = '<p class="loading">No data in this table</p>';
                return;
            }
            
            let html = '<table class="data-table"><thead><tr><th class="checkbox-cell"><input type="checkbox" onchange="toggleSelectAll(this)"></th>';
            
            result.columns.forEach(col => {
                html += `<th>${col.column_name}<br><span class="schema-info">${col.data_type}</span></th>`;
            });
            
            html += '<th>Actions</th></tr></thead><tbody>';
            
            result.data.forEach((row, idx) => {
                const pkValues = primaryKeys.map(pk => encodeURIComponent(row[pk]));
                const pkParam = primaryKeys.map((pk, i) => `${pk}=${pkValues[i]}`).join('&');
                
                html += '<tr>';
                html += `<td class="checkbox-cell"><input type="checkbox" data-pk="${pkParam}" onchange="toggleRowSelection(this)"></td>`;
                
                result.columns.forEach(col => {
                    const value = row[col.column_name];
                    const displayValue = value === null ? '<em>NULL</em>' : escapeHtml(String(value));
                    html += `<td>${displayValue}</td>`;
                });
                
                html += `<td class="action-cell">
                    <button class="btn btn-primary" onclick="showEditRowModal('${pkParam}')" style="padding: 4px 8px; font-size: 12px;">Edit</button>
                    <button class="btn btn-danger" onclick="deleteRow('${pkParam}')" style="padding: 4px 8px; font-size: 12px;">Delete</button>
                </td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            container.innerHTML = html;
        }

        function renderPagination(total, limit, offset) {
            const totalPages = Math.ceil(total / limit);
            const pagination = document.getElementById('pagination');
            
            let html = '';
            html += `<button class="btn btn-secondary" onclick="goToPage(0)" ${currentPage === 0 ? 'disabled' : ''}>First</button>`;
            html += `<button class="btn btn-secondary" onclick="goToPage(${currentPage - 1})" ${currentPage === 0 ? 'disabled' : ''}>Prev</button>`;
            html += `<span>Page ${currentPage + 1} of ${totalPages || 1}</span>`;
            html += `<button class="btn btn-secondary" onclick="goToPage(${currentPage + 1})" ${currentPage >= totalPages - 1 ? 'disabled' : ''}>Next</button>`;
            html += `<button class="btn btn-secondary" onclick="goToPage(${totalPages - 1})" ${currentPage >= totalPages - 1 ? 'disabled' : ''}>Last</button>`;
            
            pagination.innerHTML = html;
        }

        function goToPage(page) {
            currentPage = page;
            loadTableData();
        }

        function toggleSelectAll(checkbox) {
            const checkboxes = document.querySelectorAll('#tableDataContainer tbody input[type="checkbox"]');
            checkboxes.forEach(cb => cb.checked = checkbox.checked);
            updateSelectedRows();
        }

        function toggleRowSelection(checkbox) {
            updateSelectedRows();
        }

        function updateSelectedRows() {
            selectedRows.clear();
            document.querySelectorAll('#tableDataContainer tbody input[type="checkbox"]:checked').forEach(cb => {
                selectedRows.add(cb.dataset.pk);
            });
        }

        function showAddRowModal() {
            document.getElementById('rowModalTitle').textContent = 'Add New Row';
            renderRowForm({});
            document.getElementById('rowModal').classList.add('show');
        }

        async function showEditRowModal(pkParam) {
            document.getElementById('rowModalTitle').textContent = 'Edit Row';
            
            const params = new URLSearchParams(pkParam);
            const pkValues = {};
            for (const [key, value] of params.entries()) {
                pkValues[key] = decodeURIComponent(value);
            }
            
            try {
                const result = await apiRequest(`/api/table/${encodeURIComponent(currentTable)}?limit=1&offset=0`);
                const row = result.data.find(r => primaryKeys.every(pk => String(r[pk]) === String(pkValues[pk])));
                
                if (row) {
                    renderRowForm(row, pkValues);
                    document.getElementById('rowModal').classList.add('show');
                }
            } catch (error) {
                showAlert('Failed to load row data: ' + error.message, 'error');
            }
        }

        function renderRowForm(data, pkValues = {}) {
            const form = document.getElementById('rowForm');
            let html = '';
            
            tableSchema.forEach(col => {
                const isPk = primaryKeys.includes(col.column_name);
                const value = data[col.column_name] !== undefined ? data[col.column_name] : '';
                const disabled = isPk && Object.keys(pkValues).length > 0 ? 'disabled' : '';
                
                let input;
                if (col.data_type === 'BOOLEAN') {
                    input = `<select ${disabled}><option value="">NULL</option><option value="true" ${value === true ? 'selected' : ''}>True</option><option value="false" ${value === false ? 'selected' : ''}>False</option></select>`;
                } else if (col.data_type.includes('DATE') || col.data_type.includes('TIME')) {
                    input = `<input type="text" value="${escapeHtml(value)}" ${disabled}>`;
                } else {
                    input = `<input type="text" value="${escapeHtml(value)}" ${disabled}>`;
                }
                
                html += `<div class="form-group">
                    <label>${col.column_name} (${col.data_type})${isPk ? ' [PK]' : ''}</label>
                    ${input}
                </div>`;
            });
            
            form.innerHTML = html;
        }

        async function saveRow() {
            const form = document.getElementById('rowForm');
            const inputs = form.querySelectorAll('input, select');
            const data = {};
            
            tableSchema.forEach((col, idx) => {
                const input = inputs[idx];
                let value = input.value;
                
                if (input.disabled) return;
                
                if (value === '') {
                    data[col.column_name] = null;
                } else if (col.data_type === 'BOOLEAN') {
                    data[col.column_name] = value === 'true';
                } else if (col.data_type.includes('INT')) {
                    data[col.column_name] = parseInt(value, 10);
                } else if (col.data_type.includes('DECIMAL') || col.data_type.includes('NUMERIC')) {
                    data[col.column_name] = parseFloat(value);
                } else {
                    data[col.column_name] = value;
                }
            });
            
            try {
                const title = document.getElementById('rowModalTitle').textContent;
                if (title.includes('Add')) {
                    await apiRequest(`/api/table/${encodeURIComponent(currentTable)}/row`, 'POST', data);
                    showAlert('Row added successfully');
                } else {
                    // Find PK values from form
                    const pkValues = {};
                    tableSchema.filter(col => primaryKeys.includes(col.column_name)).forEach(col => {
                        pkValues[col.column_name] = data[col.column_name];
                        delete data[col.column_name];
                    });
                    
                    await apiRequest(`/api/table/${encodeURIComponent(currentTable)}/row`, 'PUT', { pk_values: pkValues, data: data });
                    showAlert('Row updated successfully');
                }
                
                closeModal('rowModal');
                loadTableData();
            } catch (error) {
                showAlert('Failed to save row: ' + error.message, 'error');
            }
        }

        async function deleteRow(pkParam) {
            if (!confirm('Are you sure you want to delete this row?')) return;
            
            try {
                const params = new URLSearchParams(pkParam);
                const pkValues = {};
                for (const [key, value] of params.entries()) {
                    pkValues[key] = decodeURIComponent(value);
                }
                
                await apiRequest(`/api/table/${encodeURIComponent(currentTable)}/row`, 'DELETE', { pk_values: pkValues });
                showAlert('Row deleted successfully');
                loadTableData();
            } catch (error) {
                showAlert('Failed to delete row: ' + error.message, 'error');
            }
        }

        async function deleteSelectedRows() {
            if (selectedRows.size === 0) {
                showAlert('No rows selected', 'error');
                return;
            }
            
            if (!confirm(`Are you sure you want to delete ${selectedRows.size} rows?`)) return;
            
            try {
                for (const pkParam of selectedRows) {
                    const params = new URLSearchParams(pkParam);
                    const pkValues = {};
                    for (const [key, value] of params.entries()) {
                        pkValues[key] = decodeURIComponent(value);
                    }
                    await apiRequest(`/api/table/${encodeURIComponent(currentTable)}/row`, 'DELETE', { pk_values: pkValues });
                }
                showAlert(`${selectedRows.size} rows deleted successfully`);
                selectedRows.clear();
                loadTableData();
            } catch (error) {
                showAlert('Failed to delete rows: ' + error.message, 'error');
            }
        }

        function showCreateTableModal() {
            document.getElementById('createTableModal').classList.add('show');
        }

        function addColumnDef() {
            const container = document.getElementById('columnDefinitions');
            const div = document.createElement('div');
            div.className = 'column-def';
            div.style.cssText = 'display: flex; gap: 10px; margin-bottom: 10px;';
            div.innerHTML = `
                <input type="text" placeholder="Column name" class="col-name" style="flex: 2;">
                <select class="col-type" style="flex: 1;">
                    <option value="INTEGER">INTEGER</option>
                    <option value="VARCHAR(255)">VARCHAR</option>
                    <option value="TEXT">TEXT</option>
                    <option value="BOOLEAN">BOOLEAN</option>
                    <option value="DATE">DATE</option>
                    <option value="TIMESTAMP">TIMESTAMP</option>
                    <option value="DECIMAL(10,2)">DECIMAL</option>
                </select>
                <label><input type="checkbox" class="col-pk"> PK</label>
                <label><input type="checkbox" class="col-notnull" checked> NOT NULL</label>
                <button class="btn btn-danger" onclick="this.parentElement.remove()" style="padding: 4px 8px;">×</button>
            `;
            container.appendChild(div);
        }

        async function createTable() {
            const tableName = document.getElementById('newTableName').value.trim();
            if (!tableName) {
                showAlert('Please enter a table name', 'error');
                return;
            }
            
            const columnDefs = document.querySelectorAll('.column-def');
            const columns = [];
            
            columnDefs.forEach(def => {
                const name = def.querySelector('.col-name').value.trim();
                const type = def.querySelector('.col-type').value;
                const isPk = def.querySelector('.col-pk').checked;
                const isNullable = !def.querySelector('.col-notnull').checked;
                
                if (name) {
                    columns.push({ name, type, primary_key: isPk, nullable: isNullable });
                }
            });
            
            if (columns.length === 0) {
                showAlert('Please define at least one column', 'error');
                return;
            }
            
            try {
                await apiRequest('/api/table', 'POST', { table_name: tableName, columns });
                showAlert('Table created successfully');
                closeModal('createTableModal');
                refreshTables();
                
                // Clear form
                document.getElementById('newTableName').value = '';
                document.querySelectorAll('.column-def:not(:first-child)').forEach(el => el.remove());
            } catch (error) {
                showAlert('Failed to create table: ' + error.message, 'error');
            }
        }

        function toggleSqlEditor() {
            const panel = document.getElementById('customSqlPanel');
            panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
        }

        async function executeSql() {
            const query = document.getElementById('sqlQuery').value.trim();
            if (!query) {
                showAlert('Please enter a SQL query', 'error');
                return;
            }
            
            try {
                const result = await apiRequest('/api/sql', 'POST', { query });
                const resultsDiv = document.getElementById('sqlResults');
                resultsDiv.classList.remove('hidden');
                
                if (result.type === 'query') {
                    let html = `<p>Query returned ${result.count} rows</p><table class="data-table"><thead><tr>`;
                    if (result.data.length > 0) {
                        Object.keys(result.data[0]).forEach(key => {
                            html += `<th>${key}</th>`;
                        });
                    }
                    html += '</tr></thead><tbody>';
                    result.data.forEach(row => {
                        html += '<tr>';
                        Object.values(row).forEach(val => {
                            html += `<td>${val === null ? '<em>NULL</em>' : escapeHtml(String(val))}</td>`;
                        });
                        html += '</tr>';
                    });
                    html += '</tbody></table>';
                    resultsDiv.innerHTML = html;
                } else {
                    resultsDiv.innerHTML = `<p class="alert alert-success">Command executed successfully. Affected rows: ${result.affected_rows}</p>`;
                }
            } catch (error) {
                showAlert('SQL execution failed: ' + error.message, 'error');
            }
        }

        function closeModal(modalId) {
            document.getElementById(modalId).classList.remove('show');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Close modal on outside click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.classList.remove('show');
            });
        });
    </script>
</body>
</html>'''


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

db_manager = DatabaseManager(DB_CONFIG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    yield
    db_manager.close()


app = FastAPI(
    title="Database Table Editor",
    description="A web-based database table editor with PostgreSQL integration",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML interface"""
    return HTMLResponse(content=HTML_TEMPLATE)


@app.get("/api/tables")
async def get_tables():
    """Get list of all tables"""
    return db_manager.get_tables()


@app.get("/api/table/{table_name}")
async def get_table_data(table_name: str, limit: int = 100, offset: int = 0):
    """Get paginated data from a table"""
    return db_manager.get_table_data(table_name, limit, offset)


@app.post("/api/table")
async def create_table(request: Request):
    """Create a new table"""
    body = await request.json()
    table_name = body.get("table_name")
    columns = body.get("columns", [])
    if not table_name:
        raise HTTPException(status_code=400, detail="table_name is required")
    return {"success": db_manager.create_table(table_name, columns)}


@app.delete("/api/table/{table_name}")
async def drop_table(table_name: str):
    """Drop a table"""
    return {"success": db_manager.drop_table(table_name)}


@app.post("/api/table/{table_name}/row")
async def insert_row(table_name: str, data: Dict[str, Any]):
    """Insert a new row"""
    return {"success": db_manager.insert_row(table_name, data)}


@app.put("/api/table/{table_name}/row")
async def update_row(table_name: str, pk_values: Dict[str, Any], data: Dict[str, Any]):
    """Update an existing row"""
    return {"success": db_manager.update_row(table_name, pk_values, data)}


@app.delete("/api/table/{table_name}/row")
async def delete_row(table_name: str, pk_values: Dict[str, Any]):
    """Delete a row"""
    return {"success": db_manager.delete_row(table_name, pk_values)}


@app.post("/api/sql")
async def execute_sql(request: Request):
    """Execute custom SQL query"""
    body = await request.json()
    query = body.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    return db_manager.execute_custom_sql(query)


@app.post("/api/table/{table_name}/row")
async def insert_row(table_name: str, request: Request):
    """Insert a new row"""
    data = await request.json()
    return {"success": db_manager.insert_row(table_name, data)}


@app.put("/api/table/{table_name}/row")
async def update_row(table_name: str, request: Request):
    """Update an existing row"""
    body = await request.json()
    pk_values = body.get("pk_values", {})
    data = body.get("data", {})
    return {"success": db_manager.update_row(table_name, pk_values, data)}


@app.delete("/api/table/{table_name}/row")
async def delete_row(table_name: str, request: Request):
    """Delete a row"""
    body = await request.json()
    pk_values = body.get("pk_values", {})
    return {"success": db_manager.delete_row(table_name, pk_values)}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        db_manager.execute_query("SELECT 1 as test")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# =============================================================================
# TEST SUITE
# =============================================================================

def run_tests():
    """Run integration tests"""
    print("\n" + "="*60)
    print("RUNNING INTEGRATION TESTS")
    print("="*60 + "\n")
    
    test_db = DatabaseManager(DB_CONFIG)
    tests_passed = 0
    tests_failed = 0
    
    def test(name, condition, error_msg=""):
        nonlocal tests_passed, tests_failed
        if condition:
            print(f"✓ PASS: {name}")
            tests_passed += 1
        else:
            print(f"✗ FAIL: {name}")
            if error_msg:
                print(f"  Error: {error_msg}")
            tests_failed += 1
        return condition
    
    try:
        # Test 1: Connection
        conn = test_db.get_connection()
        test("Database connection", conn is not None and not conn.closed)
        
        # Test 2: Get tables (should have at least our test table later)
        tables = test_db.get_tables()
        test("Get tables returns list", isinstance(tables, list))
        
        # Test 3: Create test table
        test_table = "test_employees"
        try:
            test_db.drop_table(test_table)
        except:
            pass
        
        columns = [
            {"name": "id", "type": "INTEGER", "primary_key": True, "nullable": False},
            {"name": "name", "type": "VARCHAR(100)", "primary_key": False, "nullable": False},
            {"name": "email", "type": "TEXT", "primary_key": False, "nullable": True},
            {"name": "salary", "type": "DECIMAL(10,2)", "primary_key": False, "nullable": True},
            {"name": "active", "type": "BOOLEAN", "primary_key": False, "nullable": False}
        ]
        
        created = test_db.create_table(test_table, columns)
        test("Create table", created)
        
        # Test 4: Verify table exists
        tables = test_db.get_tables()
        test("Table appears in list", test_table in tables)
        
        # Test 5: Get table schema
        schema = test_db.get_table_schema(test_table)
        test("Get table schema", len(schema) == 5)
        
        # Test 6: Get primary keys
        pks = test_db.get_primary_keys(test_table)
        test("Get primary keys", pks == ["id"])
        
        # Test 7: Insert row
        test_db.insert_row(test_table, {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "salary": 50000.00,
            "active": True
        })
        test_db.insert_row(test_table, {
            "id": 2,
            "name": "Jane Smith",
            "email": "jane@example.com",
            "salary": 60000.00,
            "active": True
        })
        test("Insert rows", True)
        
        # Test 8: Get table data
        data = test_db.get_table_data(test_table, limit=10, offset=0)
        test("Get table data", data["total"] == 2 and len(data["data"]) == 2)
        
        # Test 9: Update row
        test_db.update_row(test_table, {"id": 1}, {"salary": 55000.00})
        data = test_db.get_table_data(test_table)
        test("Update row", data["data"][0]["salary"] == 55000.00)
        
        # Test 10: Delete row
        test_db.delete_row(test_table, {"id": 2})
        data = test_db.get_table_data(test_table)
        test("Delete row", data["total"] == 1)
        
        # Test 11: Custom SQL query
        result = test_db.execute_custom_sql("SELECT COUNT(*) as cnt FROM test_employees")
        test("Custom SQL SELECT", result["type"] == "query" and result["count"] == 1)
        
        # Test 12: Custom SQL command
        result = test_db.execute_custom_sql("INSERT INTO test_employees (id, name, email, salary, active) VALUES (3, 'Test User', 'test@test.com', 45000, true)")
        test("Custom SQL INSERT", result["type"] == "command" and result["affected_rows"] == 1)
        
        # Cleanup
        test_db.drop_table(test_table)
        test("Cleanup test table", True)
        
    except Exception as e:
        test(f"Unexpected error: {str(e)}", False)
    
    # Summary
    print("\n" + "-"*60)
    print(f"TESTS PASSED: {tests_passed}")
    print(f"TESTS FAILED: {tests_failed}")
    print("="*60 + "\n")
    
    return tests_failed == 0


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Table Editor")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--db-host", default="localhost", help="Database host")
    parser.add_argument("--db-port", type=int, default=5432, help="Database port")
    parser.add_argument("--db-name", default="appdb", help="Database name")
    parser.add_argument("--db-user", default="appuser", help="Database user")
    parser.add_argument("--db-password", default="apppass", help="Database password")
    parser.add_argument("--test", action="store_true", help="Run tests only")
    
    args = parser.parse_args()
    
    # Update DB config
    DB_CONFIG.host = args.db_host
    DB_CONFIG.port = args.db_port
    DB_CONFIG.database = args.db_name
    DB_CONFIG.user = args.db_user
    DB_CONFIG.password = args.db_password
    
    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)
    
    print("\n" + "="*60)
    print("DATABASE TABLE EDITOR")
    print("="*60)
    print(f"Starting server on http://{args.host}:{args.port}")
    print(f"Database: {DB_CONFIG.database}@{DB_CONFIG.host}:{DB_CONFIG.port}")
    print("="*60 + "\n")
    
    run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
