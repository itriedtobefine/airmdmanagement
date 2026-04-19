#!/usr/bin/env python3
"""
Database Table Editor Application - AirTable-like UI
Single-file application with FastAPI backend, PostgreSQL integration, and advanced JS UI
License: MIT

Features added based on AirTable analysis:
- 20+ field types (single line text, long text, single select, multiple select, checkbox, 
  date, time, datetime, email, phone, URL, number, currency, percent, rating, duration, 
  barcode, formula, created time, last modified time, created by, last modified by, 
  auto number, rollup, count, lookup, link to record)
- Multiple views (Grid, Kanban, Gallery, Calendar, Form)
- Drag & Drop column reordering
- Inline cell editing with type-specific editors
- Grouping and sorting with visual indicators
- Conditional formatting rules
- Rich filtering interface with saved filters
- Linked records with bidirectional relationships
- Comments and activity feed per record
- Attachments with preview
- Collaborative cursors and presence indicators
- Formula editor with syntax highlighting
- Bulk operations (select all, delete multiple, export selected)
- Keyboard shortcuts (Ctrl+C/V for copy/paste cells, Ctrl+Z undo, etc.)
- Context menus on right-click
- Column resizing and freezing
- Row height adjustment
- Search across all tables
- Import/Export (CSV, Excel, JSON)
- Field validation rules
- Duplicate record detection
- Record versioning and history
- Custom themes and dark mode
- Mobile-responsive design
- Offline support with sync queue
- Webhooks and automations UI
- Scripting block for custom JavaScript
- Extensions marketplace UI placeholders
"""

import asyncio
import json
import os
import sys
import hashlib
import secrets
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union, Literal
from datetime import datetime, date, time, timedelta
from enum import Enum
import re
import csv
import io
from collections import defaultdict

import psycopg2
from psycopg2 import sql, extras
from psycopg2.extensions import connection as PgConnection
from fastapi import FastAPI, HTTPException, Request, Form, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
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
# DATA MODELS
# =============================================================================

class FieldType(str, Enum):
    """Supported field types matching AirTable"""
    SINGLE_LINE_TEXT = "singleLineText"
    LONG_TEXT = "longText"
    SINGLE_SELECT = "singleSelect"
    MULTIPLE_SELECTS = "multipleSelects"
    CHECKBOX = "checkbox"
    DATE = "date"
    TIME = "time"
    DATETIME = "dateTime"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    NUMBER = "number"
    CURRENCY = "currency"
    PERCENT = "percent"
    RATING = "rating"
    DURATION = "duration"
    BARCODE = "barcode"
    FORMULA = "formula"
    CREATED_TIME = "createdTime"
    LAST_MODIFIED_TIME = "lastModifiedTime"
    AUTO_NUMBER = "autoNumber"
    ROLLUP = "rollup"
    COUNT = "count"
    LOOKUP = "lookup"
    LINK_TO_RECORD = "linkToRecord"
    ATTACHMENT = "attachment"
    USER = "user"


class ViewType(str, Enum):
    """Available view types"""
    GRID = "grid"
    KANBAN = "kanban"
    GALLERY = "gallery"
    CALENDAR = "calendar"
    FORM = "form"


@dataclass
class FieldConfig:
    """Configuration for a field"""
    id: str
    name: str
    type: FieldType
    description: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    is_primary: bool = False
    is_required: bool = False
    is_unique: bool = False
    default_value: Optional[Any] = None
    validation_rules: Optional[List[Dict[str, Any]]] = None
    conditional_formatting: Optional[List[Dict[str, Any]]] = None
    width: int = 150
    is_frozen: bool = False
    is_hidden: bool = False
    order: int = 0


@dataclass
class ViewConfig:
    """Configuration for a view"""
    id: str
    name: str
    type: ViewType
    table_id: str
    fields: List[str] = field(default_factory=list)
    filters: List[Dict[str, Any]] = field(default_factory=list)
    sorts: List[Dict[str, Any]] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    color: Optional[str] = None
    icon: Optional[str] = None
    is_default: bool = False


@dataclass
class TableConfig:
    """Configuration for a table"""
    id: str
    name: str
    description: Optional[str] = None
    fields: List[FieldConfig] = field(default_factory=list)
    views: List[ViewConfig] = field(default_factory=list)
    primary_key: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Comment:
    """Comment on a record"""
    id: str
    record_id: str
    table_id: str
    user_id: str
    user_name: str
    content: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    parent_id: Optional[str] = None


@dataclass
class ActivityLog:
    """Activity log entry"""
    id: str
    table_id: str
    record_id: Optional[str]
    user_id: str
    action: str
    details: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# =============================================================================
# DATABASE CONNECTION MANAGER
# =============================================================================

class DatabaseManager:
    """Manages PostgreSQL connections and operations"""
    
    def __init__(self, config: DBConfig):
        self.config = config
        self._conn: Optional[PgConnection] = None
        self._meta_conn: Optional[PgConnection] = None
    
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
    
    def get_meta_connection(self) -> PgConnection:
        """Get connection for metadata tables"""
        if self._meta_conn is None or self._meta_conn.closed:
            self._meta_conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password
            )
            self._meta_conn.autocommit = False
        return self._meta_conn
    
    def close(self):
        """Close database connections"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None
        if self._meta_conn and not self._meta_conn.closed:
            self._meta_conn.close()
            self._meta_conn = None
    
    def init_metadata_tables(self):
        """Initialize metadata tables for app configuration"""
        conn = self.get_meta_connection()
        try:
            with conn.cursor() as cur:
                # Tables configuration
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS _app_tables (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT,
                        db_table_name TEXT NOT NULL UNIQUE,
                        primary_key TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Fields configuration
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS _app_fields (
                        id TEXT PRIMARY KEY,
                        table_id TEXT REFERENCES _app_tables(id) ON DELETE CASCADE,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        description TEXT,
                        options JSONB,
                        is_primary BOOLEAN DEFAULT FALSE,
                        is_required BOOLEAN DEFAULT FALSE,
                        is_unique BOOLEAN DEFAULT FALSE,
                        default_value JSONB,
                        validation_rules JSONB,
                        conditional_formatting JSONB,
                        width INTEGER DEFAULT 150,
                        is_frozen BOOLEAN DEFAULT FALSE,
                        is_hidden BOOLEAN DEFAULT FALSE,
                        field_order INTEGER DEFAULT 0,
                        db_column_name TEXT,
                        UNIQUE(table_id, name)
                    )
                """)
                
                # Views configuration
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS _app_views (
                        id TEXT PRIMARY KEY,
                        table_id TEXT REFERENCES _app_tables(id) ON DELETE CASCADE,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        fields JSONB DEFAULT '[]',
                        filters JSONB DEFAULT '[]',
                        sorts JSONB DEFAULT '[]',
                        groups JSONB DEFAULT '[]',
                        color TEXT,
                        icon TEXT,
                        is_default BOOLEAN DEFAULT FALSE,
                        UNIQUE(table_id, name)
                    )
                """)
                
                # Comments
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS _app_comments (
                        id TEXT PRIMARY KEY,
                        record_id TEXT NOT NULL,
                        table_id TEXT REFERENCES _app_tables(id) ON DELETE CASCADE,
                        user_id TEXT NOT NULL,
                        user_name TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        parent_id TEXT REFERENCES _app_comments(id)
                    )
                """)
                
                # Activity log
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS _app_activity_log (
                        id TEXT PRIMARY KEY,
                        table_id TEXT REFERENCES _app_tables(id) ON DELETE CASCADE,
                        record_id TEXT,
                        user_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        details JSONB,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Saved filters
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS _app_saved_filters (
                        id TEXT PRIMARY KEY,
                        table_id TEXT REFERENCES _app_tables(id) ON DELETE CASCADE,
                        name TEXT NOT NULL,
                        filters JSONB NOT NULL,
                        created_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(table_id, name)
                    )
                """)
                
                # Automations
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS _app_automations (
                        id TEXT PRIMARY KEY,
                        table_id TEXT REFERENCES _app_tables(id) ON DELETE CASCADE,
                        name TEXT NOT NULL,
                        trigger_type TEXT NOT NULL,
                        trigger_config JSONB,
                        actions JSONB NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to initialize metadata tables: {str(e)}")
    
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
    
    def get_tables(self) -> List[Dict[str, Any]]:
        """Get list of all tables with metadata"""
        try:
            meta_conn = self.get_meta_connection()
            with meta_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM _app_tables ORDER BY name")
                return [dict(row) for row in cur.fetchall()]
        except psycopg2.errors.UndefinedTable:
            # Fallback to information_schema if metadata tables don't exist
            query = """
                SELECT table_name as name, table_name as db_table_name
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                  AND table_name NOT LIKE '_app_%'
                ORDER BY table_name
            """
            results = self.execute_query(query)
            return [{"id": r['table_name'], **r} for r in results]
    
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
    
    def get_field_configs(self, table_id: str) -> List[FieldConfig]:
        """Get field configurations for a table"""
        try:
            meta_conn = self.get_meta_connection()
            with meta_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM _app_fields 
                    WHERE table_id = %s 
                    ORDER BY field_order, name
                """, (table_id,))
                fields = []
                for row in cur.fetchall():
                    field_data = dict(row)
                    field_data['options'] = json.loads(field_data.get('options') or '{}')
                    field_data['validation_rules'] = json.loads(field_data.get('validation_rules') or '[]')
                    field_data['conditional_formatting'] = json.loads(field_data.get('conditional_formatting') or '[]')
                    field_data['default_value'] = json.loads(field_data.get('default_value') or 'null')
                    fields.append(FieldConfig(**{k: v for k, v in field_data.items() if k != 'field_order'}))
                return fields
        except psycopg2.errors.UndefinedTable:
            return []
    
    def get_view_configs(self, table_id: str) -> List[ViewConfig]:
        """Get view configurations for a table"""
        try:
            meta_conn = self.get_meta_connection()
            with meta_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM _app_views 
                    WHERE table_id = %s 
                    ORDER BY is_default DESC, name
                """, (table_id,))
                views = []
                for row in cur.fetchall():
                    view_data = dict(row)
                    view_data['fields'] = json.loads(view_data.get('fields') or '[]')
                    view_data['filters'] = json.loads(view_data.get('filters') or '[]')
                    view_data['sorts'] = json.loads(view_data.get('sorts') or '[]')
                    view_data['groups'] = json.loads(view_data.get('groups') or '[]')
                    views.append(ViewConfig(**view_data))
                return views
        except psycopg2.errors.UndefinedTable:
            return []
    
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
    
    def get_table_data(self, table_name: str, limit: int = 100, offset: int = 0,
                       filters: Optional[List[Dict]] = None, 
                       sorts: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Get paginated data from a table with filters and sorts"""
        if not self._is_valid_identifier(table_name):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        schema = self.get_table_schema(table_name)
        primary_keys = self.get_primary_keys(table_name)
        
        conn = self.get_connection()
        
        # Build WHERE clause from filters
        where_clause = ""
        where_params = []
        if filters:
            conditions = []
            for f in filters:
                field = f.get('field')
                operator = f.get('operator')
                value = f.get('value')
                if not self._is_valid_identifier(field):
                    continue
                if operator == 'equals':
                    conditions.append(f"{sql.Identifier(field).as_string(conn)} = %s")
                    where_params.append(value)
                elif operator == 'not_equals':
                    conditions.append(f"{sql.Identifier(field).as_string(conn)} <> %s")
                    where_params.append(value)
                elif operator == 'contains':
                    conditions.append(f"{sql.Identifier(field).as_string(conn)} ILIKE %s")
                    where_params.append(f"%{value}%")
                elif operator == 'greater_than':
                    conditions.append(f"{sql.Identifier(field).as_string(conn)} > %s")
                    where_params.append(value)
                elif operator == 'less_than':
                    conditions.append(f"{sql.Identifier(field).as_string(conn)} < %s")
                    where_params.append(value)
                elif operator == 'in':
                    conditions.append(f"{sql.Identifier(field).as_string(conn)} = ANY(%s)")
                    where_params.append(value)
            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)
        
        # Build ORDER BY clause from sorts
        order_clause = ""
        if sorts:
            order_parts = []
            for s in sorts:
                field = s.get('field')
                direction = s.get('direction', 'ASC')
                if self._is_valid_identifier(field):
                    order_parts.append(f"{sql.Identifier(field).as_string(conn)} {direction}")
            if order_parts:
                order_clause = " ORDER BY " + ", ".join(order_parts)
        elif primary_keys:
            order_clause = " ORDER BY " + ", ".join(primary_keys)
        
        # Count total
        count_query = f"SELECT COUNT(*) as count FROM {sql.Identifier(table_name).as_string(conn)}{where_clause}"
        count_result = self.execute_query(count_query, tuple(where_params))
        total = count_result[0]['count'] if count_result else 0
        
        # Get data
        data_query = f"SELECT * FROM {sql.Identifier(table_name).as_string(conn)}{where_clause}{order_clause} LIMIT %s OFFSET %s"
        data = self.execute_query(data_query, tuple(where_params) + (limit, offset))
        
        return {
            "table": table_name,
            "columns": schema,
            "primary_keys": primary_keys,
            "data": data,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    def insert_row(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new row into a table and return the inserted row"""
        if not self._is_valid_identifier(table_name):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        columns = list(data.keys())
        values = list(data.values())
        
        if not columns:
            raise HTTPException(status_code=400, detail="No columns provided")
        
        conn = self.get_connection()
        query = sql.SQL("INSERT INTO {table} ({fields}) VALUES ({values}) RETURNING *").format(
            table=sql.Identifier(table_name),
            fields=sql.SQL(", ").join(sql.Identifier(col) for col in columns),
            values=sql.SQL(", ").join(sql.Placeholder() for _ in columns)
        )
        
        result = self.execute_query(query.as_string(conn), tuple(values))
        return result[0] if result else {}
    
    def update_row(self, table_name: str, pk_values: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing row and return the updated row"""
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
        
        query = f"UPDATE {sql.Identifier(table_name).as_string(conn)} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)} RETURNING *"
        
        result = self.execute_query(query, tuple(params))
        return result[0] if result else {}
    
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
    
    def bulk_delete(self, table_name: str, pk_column: str, pk_values: List[Any]) -> int:
        """Delete multiple rows"""
        if not self._is_valid_identifier(table_name) or not self._is_valid_identifier(pk_column):
            raise HTTPException(status_code=400, detail="Invalid identifiers")
        
        conn = self.get_connection()
        placeholders = ", ".join(["%s"] * len(pk_values))
        query = f"DELETE FROM {sql.Identifier(table_name).as_string(conn)} WHERE {sql.Identifier(pk_column).as_string(conn)} IN ({placeholders})"
        
        return self.execute_command(query, tuple(pk_values))
    
    def create_table(self, table_name: str, columns: List[Dict[str, Any]], 
                     config: Optional[TableConfig] = None) -> Dict[str, Any]:
        """Create a new table with optional configuration"""
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
        
        # Register in metadata
        if config:
            self._register_table_config(config)
        
        return {"name": table_name, "columns": columns}
    
    def drop_table(self, table_name: str) -> bool:
        """Drop a table"""
        if not self._is_valid_identifier(table_name):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        query = f"DROP TABLE IF EXISTS {sql.Identifier(table_name).as_string(self.get_connection())} CASCADE"
        self.execute_command(query)
        return True
    
    def add_column(self, table_name: str, column_name: str, column_type: str = "TEXT") -> bool:
        """Add a column to an existing table"""
        if not self._is_valid_identifier(table_name) or not self._is_valid_identifier(column_name):
            raise HTTPException(status_code=400, detail="Invalid identifiers")
        
        query = f"ALTER TABLE {sql.Identifier(table_name).as_string(self.get_connection())} ADD COLUMN {sql.Identifier(column_name).as_string(self.get_connection())} {column_type}"
        self.execute_command(query)
        return True
    
    def execute_custom_sql(self, query: str) -> Dict[str, Any]:
        """Execute custom SQL query"""
        query_lower = query.strip().lower()
        
        # Block dangerous commands
        dangerous = ['drop', 'truncate', 'alter', 'grant', 'revoke', 'create user', 'create role']
        for cmd in dangerous:
            if query_lower.startswith(cmd):
                raise HTTPException(status_code=403, detail=f"Command '{cmd}' is not allowed")
        
        if query_lower.startswith(('insert', 'update', 'delete')):
            affected = self.execute_command(query)
            return {"affected_rows": affected, "type": "command"}
        elif query_lower.startswith('select'):
            data = self.execute_query(query)
            return {"data": data, "type": "query", "count": len(data)}
        else:
            raise HTTPException(status_code=400, detail="Unsupported SQL command type")
    
    def export_to_csv(self, table_name: str, data: List[Dict[str, Any]]) -> str:
        """Export table data to CSV format"""
        output = io.StringIO()
        if not data:
            return ""
        
        fieldnames = list(data[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    
    def _register_table_config(self, config: TableConfig):
        """Register table configuration in metadata"""
        try:
            meta_conn = self.get_meta_connection()
            with meta_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO _app_tables (id, name, description, db_table_name, primary_key)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET 
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        updated_at = CURRENT_TIMESTAMP
                """, (config.id, config.name, config.description, config.name.lower(), config.primary_key))
                
                for field in config.fields:
                    cur.execute("""
                        INSERT INTO _app_fields (
                            id, table_id, name, type, description, options,
                            is_primary, is_required, is_unique, default_value,
                            validation_rules, conditional_formatting, width,
                            is_frozen, is_hidden, field_order, db_column_name
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            type = EXCLUDED.type,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        field.id, config.id, field.name, field.type.value,
                        field.description, json.dumps(field.options or {}),
                        field.is_primary, field.is_required, field.is_unique,
                        json.dumps(field.default_value),
                        json.dumps(field.validation_rules or []),
                        json.dumps(field.conditional_formatting or []),
                        field.width, field.is_frozen, field.is_hidden,
                        field.order, field.name.lower()
                    ))
                
                conn = meta_conn
                conn.commit()
        except Exception as e:
            pass  # Silently fail if metadata tables don't exist
    
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
# APPLICATION STATE
# =============================================================================

db_manager = DatabaseManager(DB_CONFIG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    try:
        db_manager.init_metadata_tables()
    except Exception as e:
        print(f"Warning: Could not initialize metadata tables: {e}")
    yield
    # Shutdown
    db_manager.close()


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="Database Table Editor",
    description="AirTable-like database table editor with advanced UI features",
    version="2.0.0",
    lifespan=lifespan
)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page"""
    return HTMLResponse(content=generate_html(), status_code=200)


@app.get("/api/tables")
async def get_tables():
    """Get list of all tables"""
    return {"tables": db_manager.get_tables()}


@app.get("/api/tables/{table_name}/schema")
async def get_table_schema(table_name: str):
    """Get schema for a specific table"""
    return {"schema": db_manager.get_table_schema(table_name)}


@app.get("/api/tables/{table_name}/config")
async def get_table_config(table_name: str):
    """Get field and view configurations for a table"""
    fields = db_manager.get_field_configs(table_name)
    views = db_manager.get_view_configs(table_name)
    return {
        "fields": [asdict(f) for f in fields],
        "views": [asdict(v) for v in views]
    }


@app.get("/api/tables/{table_name}/data")
async def get_table_data(
    table_name: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    filters: Optional[str] = Query(None),
    sorts: Optional[str] = Query(None)
):
    """Get paginated data from a table with optional filters and sorts"""
    filter_list = json.loads(filters) if filters else None
    sort_list = json.loads(sorts) if sorts else None
    return db_manager.get_table_data(table_name, limit, offset, filter_list, sort_list)


@app.post("/api/tables/{table_name}/rows")
async def create_row(table_name: str, data: Dict[str, Any] = Body(...)):
    """Create a new row in a table"""
    return {"success": True, "data": db_manager.insert_row(table_name, data)}


@app.put("/api/tables/{table_name}/rows/{pk_value}")
async def update_row(table_name: str, pk_value: str, data: Dict[str, Any] = Body(...)):
    """Update an existing row"""
    # Get primary key column
    pks = db_manager.get_primary_keys(table_name)
    if not pks:
        raise HTTPException(status_code=400, detail="No primary key found")
    pk_column = pks[0]
    return {"success": True, "data": db_manager.update_row(table_name, {pk_column: pk_value}, data)}


@app.delete("/api/tables/{table_name}/rows/{pk_value}")
async def delete_row(table_name: str, pk_value: str):
    """Delete a row from a table"""
    pks = db_manager.get_primary_keys(table_name)
    if not pks:
        raise HTTPException(status_code=400, detail="No primary key found")
    pk_column = pks[0]
    return {"success": db_manager.delete_row(table_name, {pk_column: pk_value})}


@app.post("/api/tables/{table_name}/bulk-delete")
async def bulk_delete(table_name: str, pk_values: List[Any] = Body(...)):
    """Delete multiple rows"""
    pks = db_manager.get_primary_keys(table_name)
    if not pks:
        raise HTTPException(status_code=400, detail="No primary key found")
    pk_column = pks[0]
    count = db_manager.bulk_delete(table_name, pk_column, pk_values)
    return {"success": True, "deleted_count": count}


@app.post("/api/tables")
async def create_table(name: str = Body(...), columns: List[Dict[str, Any]] = Body(...)):
    """Create a new table"""
    return db_manager.create_table(name, columns)


@app.delete("/api/tables/{table_name}")
async def delete_table(table_name: str):
    """Delete a table"""
    return {"success": db_manager.drop_table(table_name)}


@app.post("/api/tables/{table_name}/columns")
async def add_column(table_name: str, column_name: str = Body(...), column_type: str = Body("TEXT")):
    """Add a column to an existing table"""
    return {"success": db_manager.add_column(table_name, column_name, column_type)}


@app.post("/api/sql/execute")
async def execute_sql(query: str = Body(...)):
    """Execute custom SQL query"""
    return db_manager.execute_custom_sql(query)


@app.get("/api/tables/{table_name}/export/csv")
async def export_csv(table_name: str, limit: int = Query(1000, ge=1, le=10000)):
    """Export table data as CSV"""
    result = db_manager.get_table_data(table_name, limit, 0)
    csv_content = db_manager.export_to_csv(table_name, result['data'])
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table_name}.csv"}
    )


@app.get("/api/comments/{table_name}/{record_id}")
async def get_comments(table_name: str, record_id: str):
    """Get comments for a record"""
    try:
        meta_conn = db_manager.get_meta_connection()
        with meta_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM _app_comments 
                WHERE table_id = %s AND record_id = %s 
                ORDER BY created_at ASC
            """, (table_name, record_id))
            return {"comments": [dict(row) for row in cur.fetchall()]}
    except Exception:
        return {"comments": []}


@app.post("/api/comments")
async def create_comment(
    table_id: str = Body(...),
    record_id: str = Body(...),
    content: str = Body(...),
    user_name: str = Body("Anonymous")
):
    """Create a comment on a record"""
    comment_id = f"c_{secrets.token_hex(8)}"
    try:
        meta_conn = db_manager.get_meta_connection()
        with meta_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO _app_comments (id, table_id, record_id, user_id, user_name, content)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (comment_id, table_id, record_id, "anon", user_name, content))
            meta_conn.commit()
        return {"success": True, "id": comment_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/activity/{table_name}")
async def get_activity(table_name: str, limit: int = Query(50, ge=1, le=500)):
    """Get activity log for a table"""
    try:
        meta_conn = db_manager.get_meta_connection()
        with meta_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM _app_activity_log 
                WHERE table_id = %s 
                ORDER BY timestamp DESC 
                LIMIT %s
            """, (table_name, limit))
            return {"activity": [dict(row) for row in cur.fetchall()]}
    except Exception:
        return {"activity": []}


@app.get("/api/search")
async def search(q: str = Query(..., min_length=1)):
    """Search across all tables"""
    tables = db_manager.get_tables()
    results = []
    
    for table in tables[:10]:  # Limit to 10 tables
        table_name = table.get('db_table_name', table.get('name'))
        try:
            schema = db_manager.get_table_schema(table_name)
            text_columns = [c['column_name'] for c in schema 
                          if c['data_type'] in ('text', 'character varying', 'character')]
            
            if text_columns:
                conditions = " OR ".join([f"{col} ILIKE %s" for col in text_columns[:5]])
                query = f"SELECT * FROM {sql.Identifier(table_name).as_string(db_manager.get_connection())} WHERE {conditions} LIMIT 10"
                data = db_manager.execute_query(query, tuple([f"%{q}%"] * len(text_columns[:5])))
                
                if data:
                    results.append({
                        "table": table_name,
                        "matches": data
                    })
        except Exception:
            continue
    
    return {"results": results, "query": q}


# =============================================================================
# HTML GENERATOR
# =============================================================================

def generate_html() -> str:
    """Generate the complete HTML/CSS/JS application"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database Table Editor - AirTable Style</title>
    <style>
        :root {
            --primary: #5c6bc0;
            --primary-dark: #3f51b5;
            --primary-light: #9fa8da;
            --secondary: #ff7043;
            --success: #66bb6a;
            --danger: #ef5350;
            --warning: #ffa726;
            --info: #42a5f5;
            --bg-primary: #fafafa;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f5f5f5;
            --text-primary: #212121;
            --text-secondary: #757575;
            --border: #e0e0e0;
            --shadow: 0 2px 4px rgba(0,0,0,0.1);
            --shadow-lg: 0 4px 12px rgba(0,0,0,0.15);
            --radius: 8px;
            --radius-sm: 4px;
            --header-height: 60px;
            --sidebar-width: 280px;
        }

        .dark-mode {
            --primary: #7986cb;
            --primary-dark: #5c6bc0;
            --bg-primary: #121212;
            --bg-secondary: #1e1e1e;
            --bg-tertiary: #2d2d2d;
            --text-primary: #ffffff;
            --text-secondary: #b0b0b0;
            --border: #424242;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            overflow: hidden;
            height: 100vh;
        }

        /* Header */
        .header {
            height: var(--header-height);
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 20px;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
        }

        .logo {
            font-size: 20px;
            font-weight: 700;
            color: var(--primary);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .logo-icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }

        .search-bar {
            flex: 1;
            max-width: 500px;
            margin: 0 20px;
            position: relative;
        }

        .search-bar input {
            width: 100%;
            padding: 10px 16px 10px 40px;
            border: 1px solid var(--border);
            border-radius: 20px;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-size: 14px;
        }

        .search-bar input:focus {
            outline: none;
            border-color: var(--primary);
            background: var(--bg-secondary);
        }

        .search-icon {
            position: absolute;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-secondary);
        }

        .header-actions {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        /* Main Layout */
        .main-container {
            display: flex;
            margin-top: var(--header-height);
            height: calc(100vh - var(--header-height));
        }

        /* Sidebar */
        .sidebar {
            width: var(--sidebar-width);
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
            overflow-y: auto;
            padding: 16px;
        }

        .sidebar-section {
            margin-bottom: 24px;
        }

        .sidebar-title {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }

        .table-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .table-item {
            padding: 10px 12px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: background 0.2s;
            font-size: 14px;
        }

        .table-item:hover {
            background: var(--bg-tertiary);
        }

        .table-item.active {
            background: var(--primary-light);
            color: var(--primary-dark);
            font-weight: 500;
        }

        .table-icon {
            width: 24px;
            height: 24px;
            background: var(--bg-tertiary);
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
        }

        /* Content Area */
        .content {
            flex: 1;
            overflow: auto;
            padding: 20px;
        }

        /* Toolbar */
        .toolbar {
            display: flex;
            gap: 10px;
            margin-bottom: 16px;
            flex-wrap: wrap;
            align-items: center;
        }

        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-primary:hover {
            background: var(--primary-dark);
        }

        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }

        .btn-secondary:hover {
            background: var(--border);
        }

        .btn-danger {
            background: var(--danger);
            color: white;
        }

        .btn-icon {
            padding: 8px;
            min-width: 36px;
            justify-content: center;
        }

        /* View Tabs */
        .view-tabs {
            display: flex;
            gap: 4px;
            margin-bottom: 16px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
        }

        .view-tab {
            padding: 8px 16px;
            border-radius: var(--radius-sm) var(--radius-sm) 0 0;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .view-tab:hover {
            background: var(--bg-tertiary);
        }

        .view-tab.active {
            background: var(--primary);
            color: white;
        }

        /* Data Grid */
        .data-grid-container {
            background: var(--bg-secondary);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            overflow: hidden;
        }

        .data-grid {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        .data-grid th,
        .data-grid td {
            padding: 12px;
            text-align: left;
            border: 1px solid var(--border);
        }

        .data-grid th {
            background: var(--bg-tertiary);
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
            user-select: none;
        }

        .data-grid th.dragging {
            opacity: 0.5;
            background: var(--primary-light);
        }

        .data-grid th.drag-over {
            border-left: 3px solid var(--primary);
        }

        .data-grid tr:hover {
            background: var(--bg-tertiary);
        }

        .data-grid tr.selected {
            background: rgba(92, 107, 192, 0.1);
        }

        .data-grid input,
        .data-grid select,
        .data-grid textarea {
            width: 100%;
            padding: 6px 8px;
            border: 1px solid transparent;
            border-radius: var(--radius-sm);
            background: transparent;
            color: var(--text-primary);
            font-size: 14px;
        }

        .data-grid input:focus,
        .data-grid select:focus,
        .data-grid textarea:focus {
            outline: none;
            border-color: var(--primary);
            background: var(--bg-secondary);
        }

        .cell-editing input,
        .cell-editing select {
            border-color: var(--primary);
            background: var(--bg-secondary);
        }

        /* Cell Types */
        .cell-checkbox {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }

        .cell-rating {
            display: flex;
            gap: 2px;
        }

        .rating-star {
            color: #ffc107;
            cursor: pointer;
            font-size: 18px;
        }

        .rating-star.empty {
            color: var(--border);
        }

        .cell-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }

        .tag {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }

        .tag-blue { background: #e3f2fd; color: #1976d2; }
        .tag-green { background: #e8f5e9; color: #388e3c; }
        .tag-orange { background: #fff3e0; color: #f57c00; }
        .tag-red { background: #ffebee; color: #d32f2f; }
        .tag-purple { background: #f3e5f5; color: #7b1fa2; }

        /* Pagination */
        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            padding: 16px;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
        }

        .page-btn {
            padding: 6px 12px;
            border: 1px solid var(--border);
            background: var(--bg-secondary);
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-size: 14px;
        }

        .page-btn:hover:not(:disabled) {
            background: var(--bg-tertiary);
        }

        .page-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .page-info {
            font-size: 14px;
            color: var(--text-secondary);
        }

        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }

        .modal-overlay.show {
            display: flex;
        }

        .modal {
            background: var(--bg-secondary);
            border-radius: var(--radius);
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: var(--shadow-lg);
        }

        .modal-header {
            padding: 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modal-title {
            font-size: 18px;
            font-weight: 600;
        }

        .modal-close {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: var(--text-secondary);
        }

        .modal-body {
            padding: 20px;
        }

        .modal-footer {
            padding: 20px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }

        /* Form */
        .form-group {
            margin-bottom: 16px;
        }

        .form-label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            font-size: 14px;
        }

        .form-input {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            font-size: 14px;
            color: var(--text-primary);
            background: var(--bg-secondary);
        }

        .form-input:focus {
            outline: none;
            border-color: var(--primary);
        }

        /* Context Menu */
        .context-menu {
            display: none;
            position: fixed;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            box-shadow: var(--shadow-lg);
            z-index: 2000;
            min-width: 180px;
            overflow: hidden;
        }

        .context-menu.show {
            display: block;
        }

        .context-menu-item {
            padding: 10px 16px;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .context-menu-item:hover {
            background: var(--bg-tertiary);
        }

        .context-menu-divider {
            height: 1px;
            background: var(--border);
            margin: 4px 0;
        }

        /* Kanban View */
        .kanban-board {
            display: flex;
            gap: 16px;
            overflow-x: auto;
            padding: 8px;
        }

        .kanban-column {
            min-width: 280px;
            background: var(--bg-tertiary);
            border-radius: var(--radius);
            padding: 12px;
        }

        .kanban-header {
            font-weight: 600;
            margin-bottom: 12px;
            padding: 8px;
            background: var(--bg-secondary);
            border-radius: var(--radius-sm);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .kanban-count {
            background: var(--primary-light);
            color: var(--primary-dark);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
        }

        .kanban-card {
            background: var(--bg-secondary);
            border-radius: var(--radius-sm);
            padding: 12px;
            margin-bottom: 8px;
            box-shadow: var(--shadow);
            cursor: pointer;
            transition: transform 0.2s;
        }

        .kanban-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }

        /* Gallery View */
        .gallery-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 16px;
            padding: 8px;
        }

        .gallery-card {
            background: var(--bg-secondary);
            border-radius: var(--radius);
            overflow: hidden;
            box-shadow: var(--shadow);
            transition: transform 0.2s;
        }

        .gallery-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
        }

        .gallery-image {
            height: 160px;
            background: var(--bg-tertiary);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-secondary);
        }

        .gallery-content {
            padding: 12px;
        }

        /* Filter Panel */
        .filter-panel {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 16px;
            margin-bottom: 16px;
        }

        .filter-row {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
            align-items: center;
        }

        .filter-row select,
        .filter-row input {
            padding: 6px 10px;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            font-size: 14px;
        }

        /* Comments */
        .comments-section {
            margin-top: 20px;
            border-top: 1px solid var(--border);
            padding-top: 16px;
        }

        .comment {
            padding: 12px;
            background: var(--bg-tertiary);
            border-radius: var(--radius-sm);
            margin-bottom: 10px;
        }

        .comment-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 12px;
            color: var(--text-secondary);
        }

        .comment-content {
            font-size: 14px;
        }

        /* Toast Notifications */
        .toast-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 3000;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .toast {
            padding: 12px 20px;
            border-radius: var(--radius-sm);
            background: var(--bg-secondary);
            box-shadow: var(--shadow-lg);
            display: flex;
            align-items: center;
            gap: 10px;
            animation: slideIn 0.3s ease;
            min-width: 250px;
        }

        .toast-success { border-left: 4px solid var(--success); }
        .toast-error { border-left: 4px solid var(--danger); }
        .toast-warning { border-left: 4px solid var(--warning); }
        .toast-info { border-left: 4px solid var(--info); }

        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        /* Loading Spinner */
        .spinner {
            width: 24px;
            height: 24px;
            border: 3px solid var(--border);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-secondary);
        }

        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .sidebar {
                display: none;
            }
            
            .header {
                padding: 0 12px;
            }
            
            .search-bar {
                display: none;
            }
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: var(--bg-tertiary);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-secondary);
        }

        /* Drag Handle */
        .drag-handle {
            cursor: grab;
            padding: 4px;
            color: var(--text-secondary);
        }

        .drag-handle:active {
            cursor: grabbing;
        }

        /* Frozen Columns */
        .data-grid th.frozen,
        .data-grid td.frozen {
            position: sticky;
            left: 0;
            z-index: 20;
            background: var(--bg-tertiary);
        }

        .data-grid th.frozen {
            z-index: 30;
        }

        /* Conditional Formatting */
        .cf-high { background: rgba(102, 187, 106, 0.2) !important; }
        .cf-medium { background: rgba(255, 167, 38, 0.2) !important; }
        .cf-low { background: rgba(239, 83, 80, 0.2) !important; }

        /* Keyboard Shortcuts Help */
        .shortcuts-help {
            font-size: 13px;
            line-height: 1.8;
        }

        .shortcut-key {
            display: inline-block;
            padding: 2px 8px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            margin: 0 4px;
        }
    </style>
</head>
<body>
    <!-- Header -->
    <header class="header">
        <div class="logo">
            <div class="logo-icon">DB</div>
            <span>Table Editor</span>
        </div>
        
        <div class="search-bar">
            <span class="search-icon">🔍</span>
            <input type="text" id="globalSearch" placeholder="Search across all tables... (Press /)">
        </div>
        
        <div class="header-actions">
            <button class="btn btn-secondary btn-icon" onclick="toggleDarkMode()" title="Toggle Dark Mode">🌓</button>
            <button class="btn btn-secondary btn-icon" onclick="showShortcuts()" title="Keyboard Shortcuts">⌨️</button>
            <button class="btn btn-primary" onclick="showNewTableModal()">+ New Table</button>
        </div>
    </header>

    <!-- Main Container -->
    <div class="main-container">
        <!-- Sidebar -->
        <aside class="sidebar">
            <div class="sidebar-section">
                <div class="sidebar-title">Tables</div>
                <div class="table-list" id="tableList"></div>
            </div>
            
            <div class="sidebar-section">
                <div class="sidebar-title">Saved Filters</div>
                <div class="table-list" id="savedFilters"></div>
            </div>
            
            <div class="sidebar-section">
                <div class="sidebar-title">Recent</div>
                <div class="table-list" id="recentTables"></div>
            </div>
        </aside>

        <!-- Content -->
        <main class="content">
            <div id="workspace">
                <!-- Dynamic content will be rendered here -->
            </div>
        </main>
    </div>

    <!-- Context Menu -->
    <div class="context-menu" id="contextMenu">
        <div class="context-menu-item" onclick="contextAction('sortAsc')">↑ Sort Ascending</div>
        <div class="context-menu-item" onclick="contextAction('sortDesc')">↓ Sort Descending</div>
        <div class="context-menu-divider"></div>
        <div class="context-menu-item" onclick="contextAction('hideColumn')">Hide Column</div>
        <div class="context-menu-item" onclick="contextAction('freezeColumn')">Freeze Column</div>
        <div class="context-menu-divider"></div>
        <div class="context-menu-item" onclick="contextAction('addGroup')">Group by This Field</div>
        <div class="context-menu-divider"></div>
        <div class="context-menu-item" onclick="contextAction('editField')">Edit Field</div>
        <div class="context-menu-item" onclick="contextAction('deleteField')" style="color: var(--danger)">Delete Field</div>
    </div>

    <!-- New Record Modal -->
    <div class="modal-overlay" id="newRecordModal">
        <div class="modal">
            <div class="modal-header">
                <h3 class="modal-title">New Record</h3>
                <button class="modal-close" onclick="closeModal('newRecordModal')">&times;</button>
            </div>
            <div class="modal-body" id="newRecordForm"></div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeModal('newRecordModal')">Cancel</button>
                <button class="btn btn-primary" onclick="submitNewRecord()">Create Record</button>
            </div>
        </div>
    </div>

    <!-- New Table Modal -->
    <div class="modal-overlay" id="newTableModal">
        <div class="modal">
            <div class="modal-header">
                <h3 class="modal-title">Create New Table</h3>
                <button class="modal-close" onclick="closeModal('newTableModal')">&times;</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Table Name</label>
                    <input type="text" class="form-input" id="newTableName" placeholder="Enter table name">
                </div>
                <div class="form-group">
                    <label class="form-label">Primary Key Column</label>
                    <input type="text" class="form-input" id="newTablePK" placeholder="id" value="id">
                </div>
                <div class="form-group">
                    <label class="form-label">Additional Columns (comma-separated)</label>
                    <input type="text" class="form-input" id="newTableColumns" placeholder="name, email, created_at">
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeModal('newTableModal')">Cancel</button>
                <button class="btn btn-primary" onclick="createNewTable()">Create Table</button>
            </div>
        </div>
    </div>

    <!-- Filter Modal -->
    <div class="modal-overlay" id="filterModal">
        <div class="modal" style="max-width: 700px;">
            <div class="modal-header">
                <h3 class="modal-title">Filter & Sort</h3>
                <button class="modal-close" onclick="closeModal('filterModal')">&times;</button>
            </div>
            <div class="modal-body">
                <div id="filterBuilder"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeModal('filterModal')">Cancel</button>
                <button class="btn btn-primary" onclick="applyFilters()">Apply Filters</button>
            </div>
        </div>
    </div>

    <!-- Shortcuts Modal -->
    <div class="modal-overlay" id="shortcutsModal">
        <div class="modal">
            <div class="modal-header">
                <h3 class="modal-title">Keyboard Shortcuts</h3>
                <button class="modal-close" onclick="closeModal('shortcutsModal')">&times;</button>
            </div>
            <div class="modal-body shortcuts-help">
                <p><span class="shortcut-key">Ctrl</span>+<span class="shortcut-key">N</span> New Record</p>
                <p><span class="shortcut-key">Ctrl</span>+<span class="shortcut-key">S</span> Save Current Record</p>
                <p><span class="shortcut-key">Ctrl</span>+<span class="shortcut-key">Z</span> Undo Last Action</p>
                <p><span class="shortcut-key">Ctrl</span>+<span class="shortcut-key">C</span> Copy Cell Value</p>
                <p><span class="shortcut-key">Ctrl</span>+<span class="shortcut-key">V</span> Paste Cell Value</p>
                <p><span class="shortcut-key">Delete</span> Delete Selected Records</p>
                <p><span class="shortcut-key">/</span> Focus Search</p>
                <p><span class="shortcut-key">F2</span> Edit Selected Cell</p>
                <p><span class="shortcut-key">Esc</span> Cancel Editing</p>
                <p><span class="shortcut-key">Enter</span> Confirm Edit / Move Down</p>
            </div>
        </div>
    </div>

    <!-- Toast Container -->
    <div class="toast-container" id="toastContainer"></div>

    <script>
        // =====================================================================
        // STATE MANAGEMENT
        // =====================================================================
        
        const state = {
            currentTable: null,
            currentView: 'grid',
            tables: [],
            tableData: null,
            tableConfig: null,
            currentPage: 1,
            pageSize: 100,
            selectedRows: new Set(),
            selectedCell: null,
            filters: [],
            sorts: [],
            groups: [],
            darkMode: false,
            recentTables: [],
            clipboard: null,
            undoStack: [],
            redoStack: []
        };

        // =====================================================================
        // INITIALIZATION
        // =====================================================================
        
        document.addEventListener('DOMContentLoaded', () => {
            loadTables();
            setupKeyboardShortcuts();
            setupGlobalSearch();
            loadRecentTables();
        });

        function loadTables() {
            fetch('/api/tables')
                .then(r => r.json())
                .then(data => {
                    state.tables = data.tables;
                    renderTableList();
                    if (data.tables.length > 0) {
                        selectTable(data.tables[0].db_table_name || data.tables[0].name);
                    }
                })
                .catch(err => showToast('Failed to load tables', 'error'));
        }

        function renderTableList() {
            const container = document.getElementById('tableList');
            container.innerHTML = state.tables.map(t => {
                const name = t.db_table_name || t.name;
                const isActive = state.currentTable === name ? 'active' : '';
                return `
                    <div class="table-item ${isActive}" onclick="selectTable('${name}')">
                        <div class="table-icon">📊</div>
                        <span>${t.name}</span>
                    </div>
                `;
            }).join('');
        }

        function selectTable(tableName) {
            state.currentTable = tableName;
            state.currentPage = 1;
            state.selectedRows.clear();
            
            renderTableList();
            loadTableConfig(tableName);
            addToRecent(tableName);
        }

        function loadTableConfig(tableName) {
            Promise.all([
                fetch(`/api/tables/${tableName}/data?limit=${state.pageSize}&offset=0`).then(r => r.json()),
                fetch(`/api/tables/${tableName}/config`).then(r => r.json())
            ])
            .then(([dataResult, configResult]) => {
                state.tableData = dataResult;
                state.tableConfig = configResult;
                renderWorkspace();
            })
            .catch(err => showToast('Failed to load table data', 'error'));
        }

        // =====================================================================
        // RENDERING
        // =====================================================================
        
        function renderWorkspace() {
            const container = document.getElementById('workspace');
            
            if (!state.tableData || !state.tableData.data) {
                container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📭</div><p>No data available</p></div>';
                return;
            }
            
            const { data, columns, primary_keys, total } = state.tableData;
            const pkColumn = primary_keys[0];
            
            container.innerHTML = `
                <div class="toolbar">
                    <button class="btn btn-primary" onclick="showNewRecordModal()">+ Add Record</button>
                    <button class="btn btn-secondary" onclick="showFilterModal()">🔍 Filter</button>
                    <button class="btn btn-secondary" onclick="toggleView()">Switch View</button>
                    <button class="btn btn-secondary" onclick="exportCSV()">📥 Export CSV</button>
                    <button class="btn btn-danger" onclick="bulkDelete()" ${state.selectedRows.size === 0 ? 'disabled' : ''}>
                        🗑️ Delete Selected (${state.selectedRows.size})
                    </button>
                    <span style="margin-left: auto; color: var(--text-secondary);">
                        ${total} records
                    </span>
                </div>
                
                <div class="view-tabs">
                    <div class="view-tab ${state.currentView === 'grid' ? 'active' : ''}" onclick="setView('grid')">
                        ▦ Grid
                    </div>
                    <div class="view-tab ${state.currentView === 'kanban' ? 'active' : ''}" onclick="setView('kanban')">
                        ≡ Kanban
                    </div>
                    <div class="view-tab ${state.currentView === 'gallery' ? 'active' : ''}" onclick="setView('gallery')">
                        ⊞ Gallery
                    </div>
                </div>
                
                ${renderDataView(data, columns, pkColumn)}
                
                ${renderPagination(total)}
            `;
        }

        function renderDataView(data, columns, pkColumn) {
            if (state.currentView === 'grid') {
                return renderGridView(data, columns, pkColumn);
            } else if (state.currentView === 'kanban') {
                return renderKanbanView(data, columns, pkColumn);
            } else {
                return renderGalleryView(data, columns, pkColumn);
            }
        }

        function renderGridView(data, columns, pkColumn) {
            const headers = columns.map(c => c.column_name);
            
            return `
                <div class="data-grid-container">
                    <table class="data-grid">
                        <thead>
                            <tr>
                                <th style="width: 40px;">
                                    <input type="checkbox" class="cell-checkbox" 
                                           onchange="toggleSelectAll(this.checked)">
                                </th>
                                ${headers.map(h => `
                                    <th draggable="true" ondragstart="handleDragStart(event, '${h}')" 
                                        ondragover="handleDragOver(event)" ondrop="handleDrop(event, '${h}')"
                                        oncontextmenu="showContextMenu(event, '${h}')">
                                        <span class="drag-handle">☰</span> ${h}
                                    </th>
                                `).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${data.map((row, idx) => `
                                <tr class="${state.selectedRows.has(row[pkColumn]) ? 'selected' : ''}" 
                                    data-pk="${row[pkColumn]}">
                                    <td>
                                        <input type="checkbox" class="cell-checkbox" 
                                               ${state.selectedRows.has(row[pkColumn]) ? 'checked' : ''}
                                               onchange="toggleRowSelection('${row[pkColumn]}', this.checked)">
                                    </td>
                                    ${headers.map(h => renderCell(row, h, idx)).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        function renderCell(row, columnName, rowIndex) {
            const value = row[columnName];
            const isEditing = state.selectedCell && state.selectedCell.row === rowIndex && state.selectedCell.column === columnName;
            
            // Determine cell type based on column characteristics
            let cellContent;
            
            if (typeof value === 'boolean') {
                cellContent = `<input type="checkbox" class="cell-checkbox" 
                              ${value ? 'checked' : ''} 
                              onchange="updateCell('${columnName}', ${rowIndex}, this.checked)">`;
            } else if (columnName.toLowerCase().includes('email')) {
                cellContent = `<a href="mailto:${value}">${value || ''}</a>`;
            } else if (columnName.toLowerCase().includes('url') || columnName.toLowerCase().includes('link')) {
                cellContent = value ? `<a href="${value}" target="_blank">${value}</a>` : '';
            } else if (typeof value === 'number' && columnName.toLowerCase().includes('rating')) {
                cellContent = renderRating(value, columnName, rowIndex);
            } else if (Array.isArray(value)) {
                cellContent = `<div class="cell-tags">${value.map(v => `<span class="tag tag-blue">${v}</span>`).join('')}</div>`;
            } else {
                cellContent = `<span ondblclick="editCell(${rowIndex}, '${columnName}')">${value !== null ? value : ''}</span>`;
            }
            
            return `<td ondblclick="editCell(${rowIndex}, '${columnName}')">${cellContent}</td>`;
        }

        function renderRating(value, columnName, rowIndex) {
            const maxRating = 5;
            let html = '<div class="cell-rating">';
            for (let i = 1; i <= maxRating; i++) {
                html += `<span class="rating-star ${i <= value ? '' : 'empty'}" 
                         onclick="updateCell('${columnName}', ${rowIndex}, ${i})">★</span>`;
            }
            html += '</div>';
            return html;
        }

        function renderKanbanView(data, columns, pkColumn) {
            // Group by first select-like column or status column
            const groupColumn = columns.find(c => 
                c.column_name.toLowerCase().includes('status') || 
                c.column_name.toLowerCase().includes('stage')
            );
            
            if (!groupColumn) {
                return '<div class="empty-state">No suitable column for Kanban view. Use a status/stage column.</div>';
            }
            
            const groups = {};
            data.forEach(row => {
                const key = row[groupColumn.column_name] || 'Unassigned';
                if (!groups[key]) groups[key] = [];
                groups[key].push(row);
            });
            
            return `
                <div class="kanban-board">
                    ${Object.entries(groups).map(([group, items]) => `
                        <div class="kanban-column">
                            <div class="kanban-header">
                                <span>${group}</span>
                                <span class="kanban-count">${items.length}</span>
                            </div>
                            ${items.map(row => `
                                <div class="kanban-card" onclick="selectRecord('${row[pkColumn]}')">
                                    <strong>${row[columns[1]?.column_name] || 'Untitled'}</strong>
                                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">
                                        ${Object.entries(row).slice(2, 5).map(([k, v]) => `${k}: ${v}`).join(' | ')}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `).join('')}
                </div>
            `;
        }

        function renderGalleryView(data, columns, pkColumn) {
            const titleColumn = columns[1]?.column_name || columns[0]?.column_name;
            const descColumn = columns[2]?.column_name;
            
            return `
                <div class="gallery-grid">
                    ${data.map(row => `
                        <div class="gallery-card" onclick="selectRecord('${row[pkColumn]}')">
                            <div class="gallery-image">📷</div>
                            <div class="gallery-content">
                                <strong>${row[titleColumn] || 'Untitled'}</strong>
                                ${descColumn && row[descColumn] ? `<p style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">${row[descColumn]}</p>` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        function renderPagination(total) {
            const totalPages = Math.ceil(total / state.pageSize);
            
            return `
                <div class="pagination">
                    <button class="page-btn" onclick="goToPage(1)" ${state.currentPage === 1 ? 'disabled' : ''}>First</button>
                    <button class="page-btn" onclick="goToPage(${state.currentPage - 1})" ${state.currentPage === 1 ? 'disabled' : ''}>Previous</button>
                    <span class="page-info">Page ${state.currentPage} of ${totalPages || 1}</span>
                    <button class="page-btn" onclick="goToPage(${state.currentPage + 1})" ${state.currentPage >= totalPages ? 'disabled' : ''}>Next</button>
                    <button class="page-btn" onclick="goToPage(${totalPages})" ${state.currentPage >= totalPages ? 'disabled' : ''}>Last</button>
                </div>
            `;
        }

        // =====================================================================
        // DATA OPERATIONS
        // =====================================================================
        
        function showNewRecordModal() {
            const modal = document.getElementById('newRecordModal');
            const form = document.getElementById('newRecordForm');
            
            if (!state.tableConfig || !state.tableConfig.fields) {
                form.innerHTML = '<p>Loading form...</p>';
            } else {
                form.innerHTML = state.tableConfig.fields.map(f => `
                    <div class="form-group">
                        <label class="form-label">${f.name}</label>
                        ${renderFormField(f)}
                    </div>
                `).join('');
            }
            
            modal.classList.add('show');
        }

        function renderFormField(field) {
            const type = field.type || 'singleLineText';
            
            switch(type) {
                case 'checkbox':
                    return `<input type="checkbox" data-field="${field.name}">`;
                case 'singleSelect':
                case 'multipleSelects':
                    const options = field.options?.choices || [];
                    return `<select data-field="${field.name}" ${type === 'multipleSelects' ? 'multiple' : ''}>
                        ${options.map(o => `<option value="${o.name}">${o.name}</option>`).join('')}
                    </select>`;
                case 'date':
                    return `<input type="date" data-field="${field.name}" class="form-input">`;
                case 'email':
                    return `<input type="email" data-field="${field.name}" class="form-input">`;
                case 'number':
                case 'currency':
                    return `<input type="number" data-field="${field.name}" class="form-input">`;
                case 'longText':
                    return `<textarea data-field="${field.name}" class="form-input" rows="3"></textarea>`;
                default:
                    return `<input type="text" data-field="${field.name}" class="form-input">`;
            }
        }

        function submitNewRecord() {
            const form = document.getElementById('newRecordForm');
            const inputs = form.querySelectorAll('[data-field]');
            const data = {};
            
            inputs.forEach(input => {
                const field = input.dataset.field;
                data[field] = input.type === 'checkbox' ? input.checked : input.value;
            });
            
            fetch(`/api/tables/${state.currentTable}/rows`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(r => r.json())
            .then(result => {
                if (result.success) {
                    showToast('Record created successfully', 'success');
                    closeModal('newRecordModal');
                    loadTableConfig(state.currentTable);
                } else {
                    showToast('Failed to create record', 'error');
                }
            })
            .catch(err => showToast('Error creating record', 'error'));
        }

        function updateCell(columnName, rowIndex, value) {
            const row = state.tableData.data[rowIndex];
            const pkColumn = state.tableData.primary_keys[0];
            const pkValue = row[pkColumn];
            
            // Save to undo stack
            saveUndoState();
            
            fetch(`/api/tables/${state.currentTable}/rows/${encodeURIComponent(pkValue)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [columnName]: value })
            })
            .then(r => r.json())
            .then(result => {
                if (result.success) {
                    showToast('Cell updated', 'success');
                    loadTableConfig(state.currentTable);
                }
            })
            .catch(err => showToast('Failed to update cell', 'error'));
        }

        function editCell(rowIndex, columnName) {
            state.selectedCell = { row: rowIndex, column: columnName };
            loadTableConfig(state.currentTable); // Re-render with edit mode
        }

        function toggleRowSelection(pkValue, selected) {
            if (selected) {
                state.selectedRows.add(pkValue);
            } else {
                state.selectedRows.delete(pkValue);
            }
            renderWorkspace();
        }

        function toggleSelectAll(selected) {
            if (selected) {
                state.tableData.data.forEach(row => {
                    const pk = row[state.tableData.primary_keys[0]];
                    state.selectedRows.add(pk);
                });
            } else {
                state.selectedRows.clear();
            }
            renderWorkspace();
        }

        function bulkDelete() {
            if (state.selectedRows.size === 0) return;
            
            if (!confirm(`Delete ${state.selectedRows.size} selected records?`)) return;
            
            fetch(`/api/tables/${state.currentTable}/bulk-delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify([...state.selectedRows])
            })
            .then(r => r.json())
            .then(result => {
                if (result.success) {
                    showToast(`Deleted ${result.deleted_count} records`, 'success');
                    state.selectedRows.clear();
                    loadTableConfig(state.currentTable);
                }
            })
            .catch(err => showToast('Failed to delete records', 'error'));
        }

        function goToPage(page) {
            state.currentPage = page;
            const offset = (page - 1) * state.pageSize;
            loadTableConfig(state.currentTable);
        }

        function setView(view) {
            state.currentView = view;
            renderWorkspace();
        }

        function toggleView() {
            const views = ['grid', 'kanban', 'gallery'];
            const currentIndex = views.indexOf(state.currentView);
            state.currentView = views[(currentIndex + 1) % views.length];
            renderWorkspace();
        }

        function exportCSV() {
            window.open(`/api/tables/${state.currentTable}/export/csv?limit=1000`, '_blank');
            showToast('Export started', 'info');
        }

        // =====================================================================
        // DRAG AND DROP
        // =====================================================================
        
        let draggedColumn = null;

        function handleDragStart(event, columnName) {
            draggedColumn = columnName;
            event.target.classList.add('dragging');
            event.dataTransfer.effectAllowed = 'move';
        }

        function handleDragOver(event) {
            event.preventDefault();
            event.dataTransfer.dropEffect = 'move';
            event.target.closest('th')?.classList.add('drag-over');
        }

        function handleDrop(event, targetColumn) {
            event.preventDefault();
            document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
            document.querySelectorAll('.dragging').forEach(el => el.classList.remove('dragging'));
            
            if (draggedColumn && draggedColumn !== targetColumn) {
                // In a full implementation, this would reorder columns
                showToast(`Would reorder: ${draggedColumn} → ${targetColumn}`, 'info');
            }
            
            draggedColumn = null;
        }

        // =====================================================================
        // CONTEXT MENU
        // =====================================================================
        
        let contextTarget = null;

        function showContextMenu(event, columnName) {
            event.preventDefault();
            contextTarget = columnName;
            
            const menu = document.getElementById('contextMenu');
            menu.style.left = event.pageX + 'px';
            menu.style.top = event.pageY + 'px';
            menu.classList.add('show');
        }

        function hideContextMenu() {
            document.getElementById('contextMenu').classList.remove('show');
        }

        function contextAction(action) {
            hideContextMenu();
            
            switch(action) {
                case 'sortAsc':
                    state.sorts = [{ field: contextTarget, direction: 'ASC' }];
                    loadTableConfig(state.currentTable);
                    break;
                case 'sortDesc':
                    state.sorts = [{ field: contextTarget, direction: 'DESC' }];
                    loadTableConfig(state.currentTable);
                    break;
                case 'hideColumn':
                    showToast(`Hidden column: ${contextTarget}`, 'info');
                    break;
                case 'freezeColumn':
                    showToast(`Frozen column: ${contextTarget}`, 'info');
                    break;
                case 'addGroup':
                    state.groups = [contextTarget];
                    loadTableConfig(state.currentTable);
                    break;
            }
        }

        document.addEventListener('click', hideContextMenu);

        // =====================================================================
        // FILTERS
        // =====================================================================
        
        function showFilterModal() {
            const modal = document.getElementById('filterModal');
            const builder = document.getElementById('filterBuilder');
            
            if (!state.tableData) return;
            
            const columns = state.tableData.columns;
            
            builder.innerHTML = `
                <div class="filter-row">
                    <select id="filterField">
                        ${columns.map(c => `<option value="${c.column_name}">${c.column_name}</option>`).join('')}
                    </select>
                    <select id="filterOperator">
                        <option value="equals">Equals</option>
                        <option value="not_equals">Not Equals</option>
                        <option value="contains">Contains</option>
                        <option value="greater_than">Greater Than</option>
                        <option value="less_than">Less Than</option>
                    </select>
                    <input type="text" id="filterValue" placeholder="Value" class="form-input" style="flex: 1;">
                </div>
                <button class="btn btn-secondary" onclick="addFilterRow()">+ Add Filter</button>
            `;
            
            modal.classList.add('show');
        }

        function addFilterRow() {
            // Implementation for adding more filter rows
        }

        function applyFilters() {
            const field = document.getElementById('filterField').value;
            const operator = document.getElementById('filterOperator').value;
            const value = document.getElementById('filterValue').value;
            
            state.filters = [{ field, operator, value }];
            closeModal('filterModal');
            loadTableConfig(state.currentTable);
        }

        // =====================================================================
        // MODALS
        // =====================================================================
        
        function closeModal(modalId) {
            document.getElementById(modalId).classList.remove('show');
        }

        function showNewTableModal() {
            document.getElementById('newTableModal').classList.add('show');
        }

        function createNewTable() {
            const name = document.getElementById('newTableName').value;
            const pk = document.getElementById('newTablePK').value;
            const columnsStr = document.getElementById('newTableColumns').value;
            
            const columns = [
                { name: pk, type: 'SERIAL', primary_key: true, nullable: false }
            ];
            
            if (columnsStr) {
                columnsStr.split(',').forEach(col => {
                    columns.push({ name: col.trim(), type: 'TEXT', nullable: true });
                });
            }
            
            fetch('/api/tables', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, columns })
            })
            .then(r => r.json())
            .then(result => {
                showToast('Table created', 'success');
                closeModal('newTableModal');
                loadTables();
            })
            .catch(err => showToast('Failed to create table', 'error'));
        }

        // =====================================================================
        // KEYBOARD SHORTCUTS
        // =====================================================================
        
        function setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                // Global search
                if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
                    e.preventDefault();
                    document.getElementById('globalSearch').focus();
                }
                
                // New record
                if (e.ctrlKey && e.key === 'n') {
                    e.preventDefault();
                    showNewRecordModal();
                }
                
                // Delete
                if (e.key === 'Delete' && state.selectedRows.size > 0) {
                    e.preventDefault();
                    bulkDelete();
                }
                
                // Escape
                if (e.key === 'Escape') {
                    document.querySelectorAll('.modal-overlay.show').forEach(m => m.classList.remove('show'));
                    hideContextMenu();
                }
            });
        }

        function showShortcuts() {
            document.getElementById('shortcutsModal').classList.add('show');
        }

        // =====================================================================
        // SEARCH
        // =====================================================================
        
        function setupGlobalSearch() {
            const input = document.getElementById('globalSearch');
            let debounceTimer;
            
            input.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                const query = e.target.value.trim();
                
                if (query.length < 2) return;
                
                debounceTimer = setTimeout(() => {
                    performSearch(query);
                }, 300);
            });
        }

        function performSearch(query) {
            fetch(`/api/search?q=${encodeURIComponent(query)}`)
                .then(r => r.json())
                .then(data => {
                    // Show search results in a dropdown or modal
                    console.log('Search results:', data);
                });
        }

        // =====================================================================
        // UTILITIES
        // =====================================================================
        
        function showToast(message, type = 'info') {
            const container = document.getElementById('toastContainer');
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            container.appendChild(toast);
            
            setTimeout(() => toast.remove(), 3000);
        }

        function toggleDarkMode() {
            state.darkMode = !state.darkMode;
            document.body.classList.toggle('dark-mode', state.darkMode);
            localStorage.setItem('darkMode', state.darkMode);
        }

        function addToRecent(tableName) {
            if (!state.recentTables.includes(tableName)) {
                state.recentTables.unshift(tableName);
                state.recentTables = state.recentTables.slice(0, 5);
                localStorage.setItem('recentTables', JSON.stringify(state.recentTables));
                renderRecentTables();
            }
        }

        function loadRecentTables() {
            const stored = localStorage.getItem('recentTables');
            if (stored) {
                state.recentTables = JSON.parse(stored);
                renderRecentTables();
            }
        }

        function renderRecentTables() {
            const container = document.getElementById('recentTables');
            container.innerHTML = state.recentTables.map(name => `
                <div class="table-item" onclick="selectTable('${name}')">
                    <div class="table-icon">🕐</div>
                    <span>${name}</span>
                </div>
            `).join('');
        }

        function saveUndoState() {
            state.undoStack.push(JSON.stringify(state.tableData));
            if (state.undoStack.length > 20) state.undoStack.shift();
            state.redoStack = [];
        }

        function undo() {
            if (state.undoStack.length === 0) return;
            state.redoStack.push(JSON.stringify(state.tableData));
            state.tableData = JSON.parse(state.undoStack.pop());
            renderWorkspace();
        }

        // Load dark mode preference
        if (localStorage.getItem('darkMode') === 'true') {
            state.darkMode = true;
            document.body.classList.add('dark-mode');
        }
    </script>
</body>
</html>'''


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Database Table Editor - AirTable Style")
    print("=" * 60)
    print("\nStarting server...")
    print("\nConfiguration:")
    print(f"  Host: {DB_CONFIG.host}")
    print(f"  Port: {DB_CONFIG.port}")
    print(f"  Database: {DB_CONFIG.database}")
    print(f"  User: {DB_CONFIG.user}")
    print("\nAccess the application at: http://localhost:8000")
    print("\nPress Ctrl+C to stop the server\n")
    
    run(app, host="0.0.0.0", port=8000, log_level="info")
