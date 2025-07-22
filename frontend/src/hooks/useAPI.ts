// File: frontend/src/hooks/useAPI.ts
import { useState, useEffect, useCallback } from 'react';

// Types
export interface Project {
  id: string;
  name: string;
  description?: string;
  client_name?: string;
  status: string;
  created_at: string;
}

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  document_type: string;
  processing_status: string;
  created_at: string;
  processed_at?: string;
}

export interface Chat {
  id: string;
  name: string;
  description?: string;
  chat_type: string;
  is_active: boolean;
  created_at: string;
  last_activity?: string;
}

export interface Workflow {
  workflow_id: string;
  title: string;
  content_type: string;
  status: string;
  progress_percentage: number;
  current_stage?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface ChatMessage {
  id: string;
  content: string;
  sender_type: string;
  sender_id?: string;
  agent_type?: string;
  message_type: string;
  created_at: string;
  metadata?: any;
}

export interface ContentDraft {
  id: string;
  title: string;
  content_type: string;
  status: string;
  draft_version: number;
  word_count?: number;
  created_at: string;
  updated_at: string;
}

export interface APIResponse<T> {
  data?: T;
  error?: string;
}

// API Configuration
const API_BASE_URL = 'http://localhost:8000/api/v1';

// API Service Class
class APIService {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<APIResponse<T>> {
    try {
      const url = `${this.baseURL}${endpoint}`;
      
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.error || errorMessage;
        } catch {
          // Use default error message if JSON parsing fails
        }
        
        throw new Error(errorMessage);
      }

      const data = await response.json();
      return { data };
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error);
      return { 
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      };
    }
  }

  // Health and System
  async healthCheck(): Promise<APIResponse<any>> {
    return this.request('/health', { method: 'GET' });
  }

  async getSystemStatus(): Promise<APIResponse<any>> {
    return this.request('/system/status', { method: 'GET' });
  }

  // Projects
  async getProjects(): Promise<APIResponse<Project[]>> {
    return this.request<Project[]>('/projects');
  }

  async createProject(projectData: {
    name: string;
    description?: string;
    client_name?: string;
  }): Promise<APIResponse<Project>> {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(projectData),
    });
  }

  async getProject(projectId: string): Promise<APIResponse<Project>> {
    return this.request<Project>(`/projects/${projectId}`);
  }

  async updateProject(
    projectId: string,
    projectData: {
      name: string;
      description?: string;
      client_name?: string;
    }
  ): Promise<APIResponse<Project>> {
    return this.request<Project>(`/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify(projectData),
    });
  }

  // Documents
  async getDocuments(projectId: string): Promise<APIResponse<Document[]>> {
    return this.request<Document[]>(`/projects/${projectId}/documents`);
  }

  async uploadDocument(
    projectId: string,
    file: File,
    documentType: string
  ): Promise<APIResponse<any>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    try {
      const response = await fetch(`${this.baseURL}/projects/${projectId}/documents`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed: ${response.status}`);
      }

      const data = await response.json();
      return { data };
    } catch (error) {
      console.error('Document upload failed:', error);
      return { 
        error: error instanceof Error ? error.message : 'Upload failed' 
      };
    }
  }

  // Chats
  async getChats(projectId: string): Promise<APIResponse<Chat[]>> {
    return this.request<Chat[]>(`/projects/${projectId}/chats`);
  }

  async createChat(
    projectId: string,
    chatData: {
      name: string;
      description?: string;
      chat_type: string;
    }
  ): Promise<APIResponse<Chat>> {
    return this.request<Chat>(`/projects/${projectId}/chats`, {
      method: 'POST',
      body: JSON.stringify(chatData),
    });
  }

  async getChatMessages(
    chatId: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<APIResponse<ChatMessage[]>> {
    return this.request<ChatMessage[]>(`/chats/${chatId}/messages?limit=${limit}&offset=${offset}`);
  }

  async sendMessage(
    chatId: string,
    messageData: {
      content: string;
      message_type?: string;
    }
  ): Promise<APIResponse<any>> {
    return this.request(`/chats/${chatId}/messages`, {
      method: 'POST',
      body: JSON.stringify(messageData),
    });
  }

  // Workflows
  async getWorkflows(projectId?: string): Promise<APIResponse<Workflow[]>> {
    const url = projectId ? `/workflows?project_id=${projectId}` : '/workflows';
    return this.request<Workflow[]>(url);
  }

  async createWorkflow(workflowData: {
    title: string;
    content_type: string;
    project_id: string;
    enable_checkpoints?: boolean;
    enable_human_interaction?: boolean;
    timeout_seconds?: number;
  }): Promise<APIResponse<Workflow>> {
    return this.request<Workflow>('/workflows', {
      method: 'POST',
      body: JSON.stringify(workflowData),
    });
  }

  async getWorkflowStatus(workflowId: string): Promise<APIResponse<any>> {
    return this.request(`/workflows/${workflowId}`);
  }

  async cancelWorkflow(workflowId: string): Promise<APIResponse<any>> {
    return this.request(`/workflows/${workflowId}/cancel`, {
      method: 'POST',
    });
  }

  // Content Drafts
  async getContentDrafts(projectId: string): Promise<APIResponse<ContentDraft[]>> {
    return this.request<ContentDraft[]>(`/projects/${projectId}/drafts`);
  }

  async getContentDraft(draftId: string): Promise<APIResponse<any>> {
    return this.request(`/drafts/${draftId}`);
  }

  // Analytics
  async getAnalyticsOverview(): Promise<APIResponse<any>> {
    return this.request('/analytics/overview');
  }
}

// Global API service instance
const apiService = new APIService();

// Custom hooks for API operations
export function useAPI() {
  return apiService;
}

// Hook for projects
export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    const response = await apiService.getProjects();
    if (response.data) {
      setProjects(response.data);
    } else if (response.error) {
      setError(response.error);
    }
    
    setLoading(false);
  }, []);

  const createProject = useCallback(async (projectData: {
    name: string;
    description?: string;
    client_name?: string;
  }) => {
    const response = await apiService.createProject(projectData);
    if (response.data) {
      setProjects(prev => [response.data!, ...prev]);
      return response.data;
    } else if (response.error) {
      setError(response.error);
      throw new Error(response.error);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  return {
    projects,
    loading,
    error,
    loadProjects,
    createProject,
    setError
  };
}

// Hook for documents
export function useDocuments(projectId: string | null) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    if (!projectId) return;
    
    setLoading(true);
    setError(null);
    
    const response = await apiService.getDocuments(projectId);
    if (response.data) {
      setDocuments(response.data);
    } else if (response.error) {
      setError(response.error);
    }
    
    setLoading(false);
  }, [projectId]);

  const uploadDocument = useCallback(async (
    file: File,
    documentType: string
  ) => {
    if (!projectId) throw new Error('No project selected');
    
    const response = await apiService.uploadDocument(projectId, file, documentType);
    if (response.data) {
      await loadDocuments(); // Reload documents after upload
      return response.data;
    } else if (response.error) {
      setError(response.error);
      throw new Error(response.error);
    }
  }, [projectId, loadDocuments]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  return {
    documents,
    loading,
    error,
    loadDocuments,
    uploadDocument,
    setError
  };
}

// Hook for chats
export function useChats(projectId: string | null) {
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadChats = useCallback(async () => {
    if (!projectId) return;
    
    setLoading(true);
    setError(null);
    
    const response = await apiService.getChats(projectId);
    if (response.data) {
      setChats(response.data);
    } else if (response.error) {
      setError(response.error);
    }
    
    setLoading(false);
  }, [projectId]);

  const createChat = useCallback(async (chatData: {
    name: string;
    description?: string;
    chat_type: string;
  }) => {
    if (!projectId) throw new Error('No project selected');
    
    const response = await apiService.createChat(projectId, chatData);
    if (response.data) {
      setChats(prev => [response.data!, ...prev]);
      return response.data;
    } else if (response.error) {
      setError(response.error);
      throw new Error(response.error);
    }
  }, [projectId]);

  useEffect(() => {
    loadChats();
  }, [loadChats]);

  return {
    chats,
    loading,
    error,
    loadChats,
    createChat,
    setError
  };
}

// Hook for workflows
export function useWorkflows(projectId: string | null = null) {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadWorkflows = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    const response = await apiService.getWorkflows(projectId || undefined);
    if (response.data) {
      setWorkflows(response.data);
    } else if (response.error) {
      setError(response.error);
    }
    
    setLoading(false);
  }, [projectId]);

  const createWorkflow = useCallback(async (workflowData: {
    title: string;
    content_type: string;
    project_id: string;
    enable_checkpoints?: boolean;
    enable_human_interaction?: boolean;
    timeout_seconds?: number;
  }) => {
    const response = await apiService.createWorkflow(workflowData);
    if (response.data) {
      setWorkflows(prev => [response.data!, ...prev]);
      return response.data;
    } else if (response.error) {
      setError(response.error);
      throw new Error(response.error);
    }
  }, []);

  const cancelWorkflow = useCallback(async (workflowId: string) => {
    const response = await apiService.cancelWorkflow(workflowId);
    if (response.data) {
      await loadWorkflows(); // Reload workflows after cancellation
      return response.data;
    } else if (response.error) {
      setError(response.error);
      throw new Error(response.error);
    }
  }, [loadWorkflows]);

  useEffect(() => {
    loadWorkflows();
  }, [loadWorkflows]);

  return {
    workflows,
    loading,
    error,
    loadWorkflows,
    createWorkflow,
    cancelWorkflow,
    setError
  };
}

// Hook for real-time workflow status updates
export function useWorkflowStatus(workflowId: string | null) {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    if (!workflowId) return;
    
    setLoading(true);
    setError(null);
    
    const response = await apiService.getWorkflowStatus(workflowId);
    if (response.data) {
      setStatus(response.data);
    } else if (response.error) {
      setError(response.error);
    }
    
    setLoading(false);
  }, [workflowId]);

  useEffect(() => {
    loadStatus();
    
    // Poll for updates every 5 seconds for running workflows
    const interval = setInterval(() => {
      if (status?.status === 'running' || status?.status === 'pending') {
        loadStatus();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [loadStatus, status?.status]);

  return {
    status,
    loading,
    error,
    loadStatus,
    setError
  };
}

// Hook for WebSocket connections
export function useWebSocket(
  type: 'chat' | 'workflow',
  resourceId: string | null
) {
  const [isConnected, setIsConnected] = useState(false);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!resourceId) return;

    const wsUrl = `ws://localhost:8000/api/v1/ws/${type}/${resourceId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
      console.log(`WebSocket connected to ${type}:${resourceId}`);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMessages(prev => [...prev, data]);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log(`WebSocket disconnected from ${type}:${resourceId}`);
    };

    ws.onerror = (error) => {
      setError('WebSocket connection failed');
      console.error('WebSocket error:', error);
    };

    setSocket(ws);

    return () => {
      ws.close();
    };
  }, [type, resourceId]);

  const sendMessage = useCallback((message: any) => {
    if (socket && isConnected) {
      socket.send(JSON.stringify(message));
    }
  }, [socket, isConnected]);

  return {
    isConnected,
    messages,
    error,
    sendMessage
  };
}

// Hook for analytics
export function useAnalytics() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    const response = await apiService.getAnalyticsOverview();
    if (response.data) {
      setAnalytics(response.data);
    } else if (response.error) {
      setError(response.error);
    }
    
    setLoading(false);
  }, []);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  return {
    analytics,
    loading,
    error,
    loadAnalytics,
    setError
  };
}

export default apiService;