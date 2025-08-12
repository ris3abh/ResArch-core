// src/utils/toast.ts
// Simple toast utility - replace with react-hot-toast if you install it

interface ToastOptions {
  duration?: number;
  icon?: string;
}

class SimpleToast {
  private container: HTMLDivElement | null = null;

  private createContainer() {
    if (this.container) return this.container;
    
    this.container = document.createElement('div');
    this.container.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 8px;
      pointer-events: none;
    `;
    document.body.appendChild(this.container);
    return this.container;
  }

  private showToast(message: string, type: 'success' | 'error' | 'info' = 'info', options: ToastOptions = {}) {
    const container = this.createContainer();
    const { duration = 4000, icon } = options;
    
    const toast = document.createElement('div');
    const bgColor = type === 'success' ? '#10B981' : type === 'error' ? '#EF4444' : '#3B82F6';
    
    toast.style.cssText = `
      background: ${bgColor};
      color: white;
      padding: 12px 16px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      pointer-events: auto;
      transform: translateX(100%);
      transition: transform 0.3s ease;
      max-width: 400px;
      word-wrap: break-word;
    `;
    
    toast.textContent = `${icon || ''} ${message}`.trim();
    container.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
      toast.style.transform = 'translateX(0)';
    }, 10);
    
    // Remove after duration
    setTimeout(() => {
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => {
        if (container.contains(toast)) {
          container.removeChild(toast);
        }
        if (container.children.length === 0) {
          document.body.removeChild(container);
          this.container = null;
        }
      }, 300);
    }, duration);
  }

  success(message: string, options?: ToastOptions) {
    this.showToast(message, 'success', { icon: '✅', ...options });
  }

  error(message: string, options?: ToastOptions) {
    this.showToast(message, 'error', { icon: '❌', ...options });
  }

  info(message: string, options?: ToastOptions) {
    this.showToast(message, 'info', { icon: 'ℹ️', ...options });
  }

  // For compatibility with react-hot-toast API
  (message: string, options?: ToastOptions) {
    this.showToast(message, 'info', options);
  }
}

export const toast = new SimpleToast();
export default toast;
