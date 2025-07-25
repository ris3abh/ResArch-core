// src/hooks/useSessionHandler.ts
import { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

export function useSessionHandler() {
  const [sessionExpiredMessage, setSessionExpiredMessage] = useState<string | null>(null);
  const { user } = useAuth();

  useEffect(() => {
    const handleTokenExpiration = () => {
      setSessionExpiredMessage('Your session has expired. Please log in again.');
      
      // Clear the message after a few seconds so it doesn't persist
      setTimeout(() => {
        setSessionExpiredMessage(null);
      }, 5000);
    };

    window.addEventListener('token-expired', handleTokenExpiration);

    return () => {
      window.removeEventListener('token-expired', handleTokenExpiration);
    };
  }, []);

  // Clear message when user logs in
  useEffect(() => {
    if (user) {
      setSessionExpiredMessage(null);
    }
  }, [user]);

  return { sessionExpiredMessage };
}