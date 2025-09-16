// frontend/src/services/api.ts
// COMPLETE API SERVICE WITH WEBSOCKET INTEGRATION
// Based on backend endpoints from SpinScribe project

const API_BASE_URL = 'http://localhost:8000/api/v1';

// ========================================
// TYPE DEFINITIONS
// ========================================

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  client_name?: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
  document_count?: number;
}

export interface Document {
  id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  file_type: string;
  file_path: string;
  project_id: string;
  uploaded_by_id: string;
  created_at: string;
  updated_at: string;
}

export interface ChatInstance {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  chat_type: string;
  is_active: boolean;
  created_by: string;
  agent_config?: Record<string, any>;
  workflow_id?: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
  active_workflows?: string[];
}

export interface ChatMessage {
  id: string;
  chat_instance_id: string;
  sender_id?: string;
  sender_type: 'user' | 'agent' | 'system';
  agent_type?: string;
  message_content: string;
  message_type: string;
  message_metadata?: Record<string, any>;
  parent_message_id?: string;
  is_edited: boolean;
  created_at: string;
  updated_at?: string;
  workflow_id?: string;
  stage?: string;
}

// Workflow interfaces based on backend schemas
export interface WorkflowConfig {
  title: string;
  contentType: string;
  hasInitialDraft: boolean;
  initialDraft?: string;
  useProjectDocuments: boolean;
  enableCheckpoints: boolean;
}

export interface WorkflowCreateRequest {
  project_id: string;
  chat_id?: string;
  title: string;
  content_type: string;
  initial_draft?: string;
  use_project_documents: boolean;
}

export interface WorkflowResponse {
  workflow_id: string;
  status: string;
  current_stage?: string;
  progress?: number;
  message?: string;
  project_id: string;
  chat_id?: string;
  title: string;
  content_type: string;
  final_content?: string;
  created_at?: string;
  completed_at?: string;
  live_data?: any;
}

export interface CheckpointResponse {
  id: string;
  workflow_id: string;
  checkpoint_type: string;
  stage: string;
  title: string;
  description: string;
  status: string;
  checkpoint_data: any;
  created_at: string;
  approved_by?: string;
  approval_notes?: string;
}

export interface CheckpointApproval {
  feedback?: string;
}

// Additional interfaces for enhanced features
export interface WorkflowExecution {
  workflow_id: string;
  project_id: string;
  title: string;
  content_type: string;
  status: string;
  current_stage?: string;
  progress?: number;
  final_content?: string;
  created_at: string;
  completed_at?: string;
}

export interface WorkflowMessage {
  id: string;
  type: 'agent' | 'human' | 'system' | 'checkpoint';
  sender: string;
  content: string;
  timestamp: string;
  metadata?: {
    agent_type?: string;
    stage?: string;
    workflow_id?: string;
    checkpoint_id?: string;
    requires_approval?: boolean;
    message_type?: string;
  };
}

export interface AgentMessage {
  id: string;
  agent_type: string;
  message_content: string;
  message_type: 'solution' | 'instruction' | 'question' | 'progress';
  stage: string;
  timestamp: string;
}

export interface HumanInputRequest {
  request_id: string;
  question: string;
  question_type: 'yes_no' | 'multiple_choice' | 'text';
  options?: string[];
  timeout?: number;
}

export interface WorkflowStage {
  id: string;
  name: string;
  agent: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  progress: number;
  message?: string;
  output?: string;
  timestamp?: string;
}

export interface ProjectUpdateRequest {
  name?: string;
  description?: string;
  client_name?: string;
}

export interface DocumentStats {
  total_projects: number;
  total_documents: number;
  recent_projects: Project[];
}

// ========================================
// API SERVICE CLASS
// ========================================

class ApiService {
  private activeWebSockets: Map<string, WebSocket> = new Map();

  private getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem('spinscribe_token');
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
    };
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const config: RequestInit = {
      headers: this.getAuthHeaders(),
      ...options,
    };

    const response = await fetch(url, config);

    // Handle token expiration
    if (response.status === 401) {
      this.handleTokenExpiration();
      throw new Error('Session expired. Please log in again.');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Network error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  private handleTokenExpiration() {
    localStorage.removeItem('spinscribe_token');
    localStorage.removeItem('spinscribe_user');
    window.dispatchEvent(new CustomEvent('token-expired'));
    console.log('Session expired. Redirecting to login...');
  }

  // ========================================
  // HEALTH CHECK ENDPOINTS
  // ========================================
  
  async healthCheck() {
    return this.request('/health/');
  }

  // ========================================
  // AUTHENTICATION ENDPOINTS (backend/app/api/v1/endpoints/auth.py)
  // ========================================

  async login(email: string, password: string) {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    return response.json();
  }

  async register(userData: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
  }) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async getCurrentUser(): Promise<User> {
    return this.request('/auth/me');
  }

  async testDatabase() {
    return this.request('/auth/test-db');
  }

  // ========================================
  // PROJECT ENDPOINTS (backend/app/api/v1/endpoints/projects.py)
  // ========================================

  async getProjects(): Promise<Project[]> {
    return this.request('/projects/');
  }

  async createProject(projectData: {
    name: string;
    description?: string;
    client_name?: string;
  }): Promise<Project> {
    return this.request('/projects/', {
      method: 'POST',
      body: JSON.stringify(projectData),
    });
  }

  async getProject(projectId: string): Promise<Project> {
    return this.request(`/projects/${projectId}`);
  }

  async updateProject(projectId: string, projectData: ProjectUpdateRequest): Promise<Project> {
    return this.request(`/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify(projectData),
    });
  }

  async deleteProject(projectId: string): Promise<void> {
    return this.request(`/projects/${projectId}`, {
      method: 'DELETE',
    });
  }

  // ========================================
  // DOCUMENT ENDPOINTS (backend/app/api/v1/endpoints/documents.py)
  // ========================================

  async getProjectDocuments(projectId: string): Promise<Document[]> {
    return this.request(`/documents/project/${projectId}`);
  }

  async uploadDocument(projectId: string, file: File): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);

    const token = localStorage.getItem('spinscribe_token');
    const response = await fetch(`${API_BASE_URL}/documents/upload/${projectId}`, {
      method: 'POST',
      headers: {
        ...(token && { 'Authorization': `Bearer ${token}` }),
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  async deleteDocument(documentId: string): Promise<void> {
    return this.request(`/documents/${documentId}`, {
      method: 'DELETE',
    });
  }

  async downloadDocument(documentId: string): Promise<Blob> {
    const token = localStorage.getItem('spinscribe_token');
    const response = await fetch(`${API_BASE_URL}/documents/${documentId}/download`, {
      headers: {
        ...(token && { 'Authorization': `Bearer ${token}` }),
      },
    });

    if (!response.ok) {
      throw new Error('Download failed');
    }

    return response.blob();
  }

  async getDocumentStats(): Promise<DocumentStats> {
    return this.request('/documents/stats');
  }

  // ========================================
  // CHAT ENDPOINTS (backend/app/api/v1/endpoints/chats.py)
  // ========================================

  async getProjectChats(projectId: string): Promise<ChatInstance[]> {
    return this.request(`/chats/project/${projectId}`);
  }

  async createChat(projectId: string, chatData: {
    name: string;
    description?: string;
    chat_type?: string;
  }): Promise<ChatInstance> {
    return this.request('/chats/', {
      method: 'POST',
      body: JSON.stringify({
        ...chatData,
        project_id: projectId,
      }),
    });
  }

  async getChatInstance(chatId: string): Promise<ChatInstance> {
    return this.request(`/chats/${chatId}`);
  }

  async updateChatInstance(chatId: string, chatData: {
    name?: string;
    description?: string;
    is_active?: boolean;
  }): Promise<ChatInstance> {
    return this.request(`/chats/${chatId}`, {
      method: 'PUT',
      body: JSON.stringify(chatData),
    });
  }

  async deleteChatInstance(chatId: string): Promise<void> {
    return this.request(`/chats/${chatId}`, {
      method: 'DELETE',
    });
  }

  async getChatMessages(chatId: string, params?: {
    limit?: number;
    offset?: number;
    include_workflow_context?: boolean;
  }): Promise<ChatMessage[]> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value.toString());
        }
      });
    }
    
    const queryString = searchParams.toString();
    const endpoint = queryString ? `/chats/${chatId}/messages?${queryString}` : `/chats/${chatId}/messages`;
    
    return this.request(endpoint);
  }

  async sendChatMessage(chatId: string, content: string): Promise<ChatMessage> {
    return this.request(`/chats/${chatId}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        message_content: content,
        message_type: 'text',
      }),
    });
  }

  async updateChatMessage(chatId: string, messageId: string, content: string): Promise<ChatMessage> {
    return this.request(`/chats/${chatId}/messages/${messageId}`, {
      method: 'PUT',
      body: JSON.stringify({
        message_content: content,
      }),
    });
  }

  async deleteChatMessage(chatId: string, messageId: string): Promise<void> {
    return this.request(`/chats/${chatId}/messages/${messageId}`, {
      method: 'DELETE',
    });
  }

  async sendAgentMessage(chatId: string, agentData: {
    agent_type: string;
    message_content: string;
    message_type?: string;
    workflow_id?: string;
    stage?: string;
    metadata?: Record<string, any>;
  }): Promise<ChatMessage> {
    return this.request(`/chats/${chatId}/agent-message`, {
      method: 'POST',
      body: JSON.stringify(agentData),
    });
  }

  async sendWorkflowUpdate(chatId: string, update: {
    workflow_id: string;
    status: string;
    stage?: string;
    message?: string;
  }): Promise<any> {
    return this.request(`/chats/${chatId}/workflow-update`, {
      method: 'POST',
      body: JSON.stringify(update),
    });
  }

  async startSpinscribeWorkflow(chatId: string, task: string): Promise<any> {
    return this.request(`/chats/${chatId}/start-spinscribe`, {
      method: 'POST',
      body: JSON.stringify({
        task_description: task,
      }),
    });
  }

  // ========================================
  // WORKFLOW ENDPOINTS (backend/app/api/v1/endpoints/workflows.py)
  // ========================================

  async startWorkflow(workflowData: WorkflowCreateRequest): Promise<WorkflowResponse> {
    return this.request('/workflows/start', {
      method: 'POST',
      body: JSON.stringify(workflowData),
    });
  }

  async getWorkflowStatus(workflowId: string): Promise<WorkflowResponse> {
    return this.request(`/workflows/status/${workflowId}`);
  }

  async cancelWorkflow(workflowId: string): Promise<{ 
    message: string; 
    workflow_id: string; 
    status: string 
  }> {
    return this.request(`/workflows/${workflowId}/cancel`, {
      method: 'POST',
    });
  }

  async listWorkflows(params?: {
    project_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<WorkflowResponse[]> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value.toString());
        }
      });
    }
    
    const queryString = searchParams.toString();
    const endpoint = queryString ? `/workflows/?${queryString}` : '/workflows/';
    
    return this.request(endpoint);
  }

  async getWorkflowContent(workflowId: string): Promise<{
    workflow_id: string;
    title: string;
    content_type: string;
    content: string;
    status: string;
    created_at: string;
    completed_at?: string;
  }> {
    return this.request(`/workflows/${workflowId}/content`);
  }

  // ========================================
  // CHECKPOINT ENDPOINTS (backend/app/api/v1/endpoints/workflows.py)
  // ========================================

  async getWorkflowCheckpoints(workflowId: string): Promise<CheckpointResponse[]> {
    return this.request(`/workflows/${workflowId}/checkpoints`);
  }

  async approveCheckpoint(checkpointId: string, approval: CheckpointApproval): Promise<{
    message: string;
    checkpoint_id: string;
    workflow_id: string;
    status: string;
  }> {
    return this.request(`/workflows/checkpoints/${checkpointId}/approve`, {
      method: 'POST',
      body: JSON.stringify(approval),
    });
  }

  async rejectCheckpoint(checkpointId: string, rejection: CheckpointApproval): Promise<{
    message: string;
    checkpoint_id: string;
    workflow_id: string;
    status: string;
  }> {
    return this.request(`/workflows/checkpoints/${checkpointId}/reject`, {
      method: 'POST',
      body: JSON.stringify(rejection),
    });
  }

  // ========================================
  // WEBSOCKET METHODS
  // ========================================

  // In your api.ts file, update these methods:

  // ========================================
  // WEBSOCKET METHODS
  // ========================================

  createWorkflowWebSocket(workflowId: string): WebSocket {
    // Close existing connection if any
    this.closeWorkflowWebSocket(workflowId);
    
    const token = localStorage.getItem('spinscribe_token');
    const wsUrl = `ws://localhost:8000/api/v1/ws/workflows/${workflowId}${token ? `?token=${token}` : ''}`;
    console.log('🔌 Creating workflow WebSocket connection:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    
    // Set up event handlers
    ws.onopen = () => {
      console.log(`✅ WebSocket connected for workflow ${workflowId}`);
    };
    
    ws.onerror = (error) => {
      console.error(`❌ WebSocket error for workflow ${workflowId}:`, error);
    };
    
    ws.onclose = (event) => {
      console.log(`🔌 WebSocket closed for workflow ${workflowId}. Code: ${event.code}, Reason: ${event.reason}`);
      this.activeWebSockets.delete(workflowId);
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log(`📨 Message received for workflow ${workflowId}:`, data.type);
        
        // Handle heartbeat
        if (data.type === 'heartbeat') {
          ws.send(JSON.stringify({ type: 'pong' }));
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
    
    // Store the connection
    this.activeWebSockets.set(workflowId, ws);
    
    return ws;
  }

  createChatWebSocket(chatId: string): WebSocket {
    const token = localStorage.getItem('spinscribe_token');
    const wsUrl = `ws://localhost:8000/api/v1/ws/chats/${chatId}${token ? `?token=${token}` : ''}`;
    console.log('🔌 Creating chat WebSocket connection:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    
    // Set up event handlers
    ws.onopen = () => {
      console.log(`✅ WebSocket connected for chat ${chatId}`);
    };
    
    ws.onerror = (error) => {
      console.error(`❌ WebSocket error for chat ${chatId}:`, error);
    };
    
    ws.onclose = (event) => {
      console.log(`🔌 WebSocket closed for chat ${chatId}. Code: ${event.code}, Reason: ${event.reason}`);
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log(`📨 Message received for chat ${chatId}:`, data.type);
        
        // Handle heartbeat
        if (data.type === 'heartbeat') {
          ws.send(JSON.stringify({ type: 'pong' }));
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
    
    return ws;
  }

  // Add a method to setup keep-alive for WebSockets
  setupWebSocketKeepAlive(ws: WebSocket, interval: number = 25000): NodeJS.Timer {
    return setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, interval);
  }

  closeWorkflowWebSocket(workflowId: string): void {
    const ws = this.activeWebSockets.get(workflowId);
    if (ws) {
      ws.close(1000, 'Closing connection');
      this.activeWebSockets.delete(workflowId);
    }
  }

  private getActiveWebSocket(workflowId: string): WebSocket | null {
    return this.activeWebSockets.get(workflowId) || null;
  }

  // Send human response through WebSocket (based on backend/app/api/v1/endpoints/websocket.py)
  async sendHumanResponse(workflowId: string, requestId: string, response: string): Promise<void> {
    const ws = this.getActiveWebSocket(workflowId);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'human_response',
        request_id: requestId,
        response: response,
        workflow_id: workflowId
      }));
    } else {
      throw new Error('WebSocket not connected');
    }
  }

  // Send WebSocket message (generic)
  async sendWebSocketMessage(workflowId: string, message: any): Promise<void> {
    const ws = this.getActiveWebSocket(workflowId);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    } else {
      throw new Error('WebSocket not connected');
    }
  }

  // Get workflow status through WebSocket
  async requestWorkflowStatus(workflowId: string): Promise<void> {
    return this.sendWebSocketMessage(workflowId, { type: 'get_status' });
  }

  // Send ping to keep connection alive
  async pingWorkflow(workflowId: string): Promise<void> {
    return this.sendWebSocketMessage(workflowId, { type: 'ping' });
  }

  // ========================================
  // WEBSOCKET STATS ENDPOINT
  // ========================================

  async getWebSocketStats(): Promise<{
    status: string;
    connections: {
      total_connections: number;
      workflow_connections: number;
      chat_connections: number;
      user_connections: number;
    };
    timestamp: string;
  }> {
    return this.request('/ws/stats');
  }

  // ========================================
  // ADDITIONAL METHODS FOR CHAT WORKFLOW INTERFACE
  // ========================================

  async createWorkflowExecution(data: {
    project_id: string;
    title: string;
    content_type: string;
    initial_draft?: string;
    use_project_documents?: boolean;
  }): Promise<WorkflowExecution> {
    try {
      const workflowData: WorkflowCreateRequest = {
        project_id: data.project_id,
        title: data.title,
        content_type: data.content_type,
        initial_draft: data.initial_draft,
        use_project_documents: data.use_project_documents || true,
      };

      const response = await this.startWorkflow(workflowData);
      
      return {
        workflow_id: response.workflow_id,
        project_id: response.project_id,
        title: response.title,
        content_type: response.content_type,
        status: response.status,
        current_stage: response.current_stage,
        progress: response.progress,
        final_content: response.final_content,
        created_at: response.created_at || new Date().toISOString(),
        completed_at: response.completed_at,
      };
    } catch (error) {
      console.error('Failed to create workflow execution:', error);
      throw error;
    }
  }

  async getWorkflowExecution(workflowId: string): Promise<WorkflowExecution> {
    try {
      const response = await this.getWorkflowStatus(workflowId);
      
      return {
        workflow_id: response.workflow_id,
        project_id: response.project_id,
        title: response.title,
        content_type: response.content_type,
        status: response.status,
        current_stage: response.current_stage,
        progress: response.progress,
        final_content: response.final_content,
        created_at: response.created_at || new Date().toISOString(),
        completed_at: response.completed_at,
      };
    } catch (error) {
      console.error('Failed to get workflow execution:', error);
      throw error;
    }
  }

  async sendWorkflowMessage(workflowId: string, data: {
    content: string;
    type: string;
  }): Promise<any> {
    // Since this endpoint is not yet implemented in backend,
    // we'll use WebSocket for now
    return this.sendWebSocketMessage(workflowId, {
      type: 'workflow_message',
      content: data.content,
      message_type: data.type,
      timestamp: new Date().toISOString()
    });
  }

  async respondToCheckpoint(workflowId: string, checkpointId: string, data: {
    approved: boolean;
    feedback?: string;
  }): Promise<any> {
    try {
      const approval: CheckpointApproval = {
        feedback: data.feedback,
      };

      if (data.approved) {
        return this.approveCheckpoint(checkpointId, approval);
      } else {
        return this.rejectCheckpoint(checkpointId, approval);
      }
    } catch (error) {
      console.error('Failed to respond to checkpoint:', error);
      throw error;
    }
  }

  // ========================================
  // UTILITY METHODS FOR BACKWARDS COMPATIBILITY
  // ========================================

  async getDocuments(projectId: string): Promise<Document[]> {
    return this.getProjectDocuments(projectId);
  }

  async getChatInstances(projectId: string): Promise<ChatInstance[]> {
    return this.getProjectChats(projectId);
  }

  async createChatInstance(projectId: string, data: {
    name: string;
    description?: string;
  }): Promise<ChatInstance> {
    return this.createChat(projectId, {
      ...data,
      chat_type: 'project',
    });
  }

  async getActiveWorkflows(projectId: string): Promise<WorkflowResponse[]> {
    try {
      return this.listWorkflows({ 
        project_id: projectId, 
        status: 'running' 
      });
    } catch (error) {
      console.warn('Active workflows endpoint not available:', error);
      return [];
    }
  }

  // File upload with progress
  async uploadWithProgress(
    endpoint: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      const formData = new FormData();
      formData.append('file', file);

      const xhr = new XMLHttpRequest();
      const token = localStorage.getItem('spinscribe_token');

      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable && onProgress) {
          const progress = (event.loaded / event.total) * 100;
          onProgress(progress);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch (error) {
            resolve(xhr.responseText);
          }
        } else {
          reject(new Error(`Upload failed: ${xhr.statusText}`));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed'));
      });

      xhr.open('POST', `${API_BASE_URL}${endpoint}`);
      
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      xhr.send(formData);
    });
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;