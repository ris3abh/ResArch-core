// src/services/api.ts
const API_BASE_URL = 'http://localhost:8000/api/v1';

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
      // Token expired or invalid
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
    // Clear stored auth data
    localStorage.removeItem('spinscribe_token');
    localStorage.removeItem('spinscribe_user');
    
    // Trigger logout in auth context
    window.dispatchEvent(new CustomEvent('token-expired'));
    
    // Optional: Show a notification
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

  async updateProject(
    projectId: string,
    updates: Partial<{
      name: string;
      description: string;
      client_name: string;
    }>
  ): Promise<Project> {
    return this.request(`/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async deleteProject(projectId: string): Promise<{ message: string }> {
    return this.request(`/projects/${projectId}`, {
      method: 'DELETE',
    });
  }

  // Document Methods
  async uploadDocument(projectId: string, file: File): Promise<DocumentUploadResponse> {
    const token = localStorage.getItem('spinscribe_token');
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/documents/upload/${projectId}`, {
      method: 'POST',
      headers: {
        ...(token && { 'Authorization': `Bearer ${token}` }),
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  async getProjectDocuments(projectId: string): Promise<Document[]> {
    return this.request(`/documents/project/${projectId}`);
  }

  async deleteDocument(documentId: string): Promise<{ message: string }> {
    return this.request(`/documents/${documentId}`, {
      method: 'DELETE',
    });
  }

  async getDocumentStats(): Promise<{
    total_projects: number;
    total_documents: number;
    recent_projects: Project[];
  }> {
    return this.request('/documents/stats');
  }
}

// Types
export interface Project {
  id: string;
  name: string;
  description?: string;
  client_name?: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
  document_count: number;
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

export interface DocumentUploadResponse {
  message: string;
  document: Document;
}

export const apiService = new ApiService();