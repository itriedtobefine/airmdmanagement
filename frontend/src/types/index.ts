export interface Entity {
  id: string;
  entity_code: string;
  entity_name: string;
  version: number;
  json_schema?: any;
  description?: string;
  is_active: boolean;
  created_at: string;
}

export interface Record {
  id: string;
  version: number;
  data: any;
  created_at: string;
  updated_at?: string;
  created_by: string;
  updated_by?: string;
}

export interface RecordHistory {
  id: string;
  version: number;
  action: 'CREATE' | 'UPDATE' | 'DELETE' | 'RESTORE';
  payload_before?: any;
  payload_after?: any;
  user_id: string;
  timestamp: string;
}

export interface User {
  user_id: string;
  role: 'admin' | 'data_steward' | 'viewer';
  allowed_entities: string[];
}
