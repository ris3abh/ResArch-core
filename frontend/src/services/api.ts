// frontend/src/services/api.ts
// COMPLETE VERSION - Your existing code + minimal safe additions for chat workflow

const API_BASE_URL = 'http://localhost:8000/api/v1';

// TypeScript interfaces (your existing ones + minimal additions)
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

// Workflow interfaces (your existing ones)
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

// NEW: Add interface for project update (needed for settings)
export interface ProjectUpdateRequest {
  name?: string;
  description?: string;
  client_name?: string;
}

// NEW: Additional interfaces for chat workflow integration
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

  // ✅ YOUR EXISTING updateProject METHOD - KEEPING AS IS
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

  // ✅ YOUR EXISTING uploadDocument METHOD - KEEPING AS IS
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
  // WORKFLOW METHODS - YOUR EXISTING IMPLEMENTATIONS
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

  // Alias method for getActiveWorkflows (uses your existing listWorkflows)
  async getActiveWorkflows(projectId: string): Promise<WorkflowResponse[]> {
    try {
      return this.listWorkflows({ 
        project_id: projectId, 
        status: 'running' 
      });
    } catch (error) {
      // If endpoint doesn't exist yet, return empty array
      console.warn('Active workflows endpoint not available:', error);
      return [];
    }
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

  // ========================================
  // NEW METHODS FOR CHAT WORKFLOW INTERFACE
  // ========================================

  // Create workflow execution (adapts your startWorkflow)
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
      
      // Map your WorkflowResponse to WorkflowExecution
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

  // Get workflow execution (adapts your getWorkflowStatus)
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

  // Send workflow message (new method for chat interface)
  async sendWorkflowMessage(workflowId: string, data: {
    content: string;
    type: string;
  }): Promise<any> {
    try {
      // This would be a new endpoint you'll need to add to your backend
      return this.request(`/workflows/${workflowId}/messages`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    } catch (error) {
      console.warn('Workflow message endpoint not available yet:', error);
      // For now, just return a mock response
      return {
        id: `msg-${Date.now()}`,
        workflow_id: workflowId,
        content: data.content,
        type: data.type,
        timestamp: new Date().toISOString(),
      };
    }
  }

  // Get workflow messages (new method for chat interface)
  async getWorkflowMessages(workflowId: string): Promise<WorkflowMessage[]> {
    try {
      // This would be a new endpoint you'll need to add to your backend
      return this.request(`/workflows/${workflowId}/messages`);
    } catch (error) {
      console.warn('Workflow messages endpoint not available yet:', error);
      // For now, return empty array
      return [];
    }
  }

  // Respond to checkpoint (adapts your existing checkpoint methods)
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

  // WebSocket Connection Helper
  createWorkflowWebSocket(workflowId: string): WebSocket {
    const token = localStorage.getItem('spinscribe_token');
    const wsUrl = `ws://localhost:8000/api/v1/ws/workflows/${workflowId}${token ? `?token=${token}` : ''}`;
    console.log('🔌 Creating workflow WebSocket connection:', wsUrl);
    return new WebSocket(wsUrl);
  }

  createChatWebSocket(chatId: string): WebSocket {
    const token = localStorage.getItem('spinscribe_token');
    const wsUrl = `ws://localhost:8000/api/v1/ws/chats/${chatId}${token ? `?token=${token}` : ''}`;
    console.log('🔌 Creating chat WebSocket connection:', wsUrl);
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

  // ========================================
  // UTILITY METHODS FOR BACKWARDS COMPATIBILITY
  // ========================================

  // Alias methods to maintain compatibility with existing code
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

  // File upload with progress (useful for large documents)
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