// src/services/api.ts
const API_BASE_URL = 'http://localhost:8000/api/v1';

// TypeScript interfaces
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
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface ChatMessage {
  id: string;
  chat_instance_id: string;
  sender_type: string;
  agent_type?: string;
  message_content: string;
  message_type: string;
  created_at: string;
}

// Workflow interfaces
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

class ApiService {
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

  // Health Check
  async healthCheck() {
    return this.request('/health/');
  }

  // Auth Methods
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

  async testDatabase() {
    return this.request('/auth/test-db');
  }

  // Project Methods
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

  async updateProject(projectId: string, projectData: {
    name?: string;
    description?: string;
    client_name?: string;
  }): Promise<Project> {
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

  // Document Methods
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

  // Chat Methods
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

  async getChatMessages(chatId: string): Promise<ChatMessage[]> {
    return this.request(`/chats/${chatId}/messages`);
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

  // ========================================
  // WORKFLOW METHODS - NEW IMPLEMENTATIONS
  // ========================================

  async startWorkflow(workflowData: WorkflowCreateRequest): Promise<WorkflowResponse> {
    return this.request('/workflows/start', {
      method: 'POST',
      body: JSON.stringify(workflowData),
    });
  }

  async getWorkflowStatus(workflowId: string): Promise<WorkflowResponse> {
    return this.request(`/workflows/${workflowId}`);
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

  async cancelWorkflow(workflowId: string): Promise<{ message: string; workflow_id: string; status: string }> {
    return this.request(`/workflows/${workflowId}/cancel`, {
      method: 'POST',
    });
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

  // Checkpoint Methods
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

  // WebSocket Connection Helper
  createWorkflowWebSocket(workflowId: string): WebSocket {
    const token = localStorage.getItem('spinscribe_token');
    const wsUrl = `ws://localhost:8000/api/v1/ws/workflows/${workflowId}${token ? `?token=${token}` : ''}`;
    return new WebSocket(wsUrl);
  }

  createChatWebSocket(chatId: string): WebSocket {
    const token = localStorage.getItem('spinscribe_token');
    const wsUrl = `ws://localhost:8000/api/v1/ws/chats/${chatId}${token ? `?token=${token}` : ''}`;
    return new WebSocket(wsUrl);
  }

  // WebSocket Statistics
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
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;