import axios, { AxiosInstance } from 'axios';

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

interface Project {
  id: string;
  name: string;
  description?: string;
  client_name?: string;
  project_type: 'personal' | 'shared';
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

interface AgentTask {
  task_id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  task_type: string;
  created_at: string;
  output_data?: any;
}

interface ChatMessage {
  id: string;
  sender_type: 'user' | 'agent';
  sender_id?: string;
  agent_name?: string;
  message_content: string;
  message_type: string;
  timestamp: string;
  metadata?: any;
}

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: 'http://localhost:8000',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth token to requests
    this.api.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle auth errors
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          window.location.href = '/';
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth methods
  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await this.api.post('/api/auth/login', { email, password });
    return response.data;
  }

  async signup(email: string, password: string, first_name: string, last_name: string): Promise<AuthResponse> {
    const response = await this.api.post('/api/auth/signup', {
      email,
      password,
      first_name,
      last_name,
    });
    return response.data;
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.api.get('/api/auth/me');
    return response.data;
  }

  // Project methods
  async getProjects(): Promise<Project[]> {
    const response = await this.api.get('/api/projects');
    return response.data;
  }

  async createProject(projectData: Partial<Project>): Promise<Project> {
    const response = await this.api.post('/api/projects', projectData);
    return response.data;
  }

  async deleteProject(projectId: string): Promise<void> {
    await this.api.delete(`/api/projects/${projectId}`);
  }

  // Document methods
  async uploadDocument(projectId: string, file: File, documentType?: string): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    if (documentType) {
      formData.append('document_type', documentType);
    }

    const response = await this.api.post(`/api/projects/${projectId}/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async getProjectDocuments(projectId: string): Promise<any[]> {
    const response = await this.api.get(`/api/projects/${projectId}/documents`);
    return response.data;
  }

  // Agent methods
  async createAgentTask(projectId: string, taskType: string, inputData: any, chatInstanceId?: string): Promise<AgentTask> {
    const response = await this.api.post(`/api/projects/${projectId}/agent-tasks`, {
      task_type: taskType,
      input_data: inputData,
      chat_instance_id: chatInstanceId,
    });
    return response.data;
  }

  async getTaskStatus(taskId: string): Promise<AgentTask> {
    const response = await this.api.get(`/api/tasks/${taskId}`);
    return response.data;
  }

  async getProjectTasks(projectId: string): Promise<AgentTask[]> {
    const response = await this.api.get(`/api/projects/${projectId}/tasks`);
    return response.data;
  }

  async getAgentsStatus(): Promise<any> {
    const response = await this.api.get('/api/agents/status');
    return response.data;
  }

  // Chat methods
  async getProjectChats(projectId: string): Promise<any[]> {
    const response = await this.api.get(`/api/projects/${projectId}/chats`);
    return response.data;
  }

  async createChat(projectId: string, chatData: any): Promise<any> {
    const response = await this.api.post(`/api/projects/${projectId}/chats`, chatData);
    return response.data;
  }

  async getChatMessages(chatId: string, page = 1, limit = 50): Promise<ChatMessage[]> {
    const response = await this.api.get(`/api/chats/${chatId}/messages`, {
      params: { page, limit }
    });
    return response.data;
  }

  async sendMessage(chatId: string, messageContent: string, messageType = 'text'): Promise<ChatMessage> {
    const response = await this.api.post(`/api/chats/${chatId}/messages`, {
      message_content: messageContent,
      message_type: messageType,
    });
    return response.data;
  }

  // Health check
  async healthCheck(): Promise<any> {
    const response = await this.api.get('/health');
    return response.data;
  }
}

export const apiService = new ApiService();
export type { User, Project, AuthResponse, AgentTask, ChatMessage };
