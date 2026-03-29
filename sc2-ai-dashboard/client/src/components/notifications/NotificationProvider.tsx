import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export type NotificationType = 'info' | 'success' | 'warning' | 'error' | 'battle' | 'system';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  priority: 'low' | 'medium' | 'high' | 'critical';
  actions?: NotificationAction[];
}

export interface NotificationAction {
  label: string;
  onClick: () => void;
  variant: 'primary' | 'secondary' | 'danger';
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
  getNotificationsByType: (type: NotificationType) => Notification[];
  getHighPriorityNotifications: () => Notification[];
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
};

const generateId = () => `notif_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = useCallback((notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    const newNotification: Notification = {
      ...notification,
      id: generateId(),
      timestamp: new Date(),
      read: false,
    };

    setNotifications(prev => {
      const updated = [newNotification, ...prev].slice(0, 100);
      localStorage.setItem('sc2_notifications', JSON.stringify(updated));
      return updated;
    });

    if (notification.priority === 'critical' || notification.priority === 'high') {
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(notification.title, {
          body: notification.message,
          icon: '/favicon.ico',
          tag: newNotification.id,
        });
      }
    }
  }, []);

  const markAsRead = useCallback((id: string) => {
    setNotifications(prev => {
      const updated = prev.map(n => n.id === id ? { ...n, read: true } : n);
      localStorage.setItem('sc2_notifications', JSON.stringify(updated));
      return updated;
    });
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => {
      const updated = prev.map(n => ({ ...n, read: true }));
      localStorage.setItem('sc2_notifications', JSON.stringify(updated));
      return updated;
    });
  }, []);

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => {
      const updated = prev.filter(n => n.id !== id);
      localStorage.setItem('sc2_notifications', JSON.stringify(updated));
      return updated;
    });
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
    localStorage.removeItem('sc2_notifications');
  }, []);

  const getNotificationsByType = useCallback((type: NotificationType) => {
    return notifications.filter(n => n.type === type);
  }, [notifications]);

  const getHighPriorityNotifications = useCallback(() => {
    return notifications.filter(n => 
      (n.priority === 'high' || n.priority === 'critical') && !n.read
    );
  }, [notifications]);

  useEffect(() => {
    const saved = localStorage.getItem('sc2_notifications');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setNotifications(parsed.map((n: Notification) => ({
          ...n,
          timestamp: new Date(n.timestamp),
        })));
      } catch {
        console.error('Failed to parse saved notifications');
      }
    }

    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        addNotification,
        markAsRead,
        markAllAsRead,
        removeNotification,
        clearAll,
        getNotificationsByType,
        getHighPriorityNotifications,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
};

export const useBattleNotifications = () => {
  const { addNotification } = useNotifications();

  const notifyBattleStart = useCallback((enemyRace: string, map: string) => {
    addNotification({
      type: 'battle',
      title: '⚔️ 전투 시작',
      message: `${enemyRace} 상대 ${map} 맵에서 교전 시작`,
      priority: 'high',
    });
  }, [addNotification]);

  const notifyBattleEnd = useCallback((result: 'win' | 'loss', duration: number) => {
    addNotification({
      type: result === 'win' ? 'success' : 'error',
      title: result === 'win' ? '🏆 승리' : '💀 패배',
      message: `${duration}초간 전투 - ${result === 'win' ? '승리' : '패배'}했습니다`,
      priority: result === 'win' ? 'medium' : 'high',
    });
  }, [addNotification]);

  const notifyArmyCritical = useCallback((current: number, threshold: number) => {
    addNotification({
      type: 'warning',
      title: '🚨 군대력 위기',
      message: `현재 군대력 ${current} - 임계값 ${threshold} 이하`,
      priority: 'critical',
    });
  }, [addNotification]);

  const notifyEnemyDetected = useCallback((enemyType: string, location: string) => {
    addNotification({
      type: 'battle',
      title: '👁️ 적 감지',
      message: `${enemyType} - ${location}에서 발견`,
      priority: 'high',
    });
  }, [addNotification]);

  return {
    notifyBattleStart,
    notifyBattleEnd,
    notifyArmyCritical,
    notifyEnemyDetected,
  };
};

export default NotificationProvider;
