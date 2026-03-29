import React, { useState, useRef, useEffect } from 'react';
import { useNotifications, Notification, NotificationType } from './NotificationProvider';

const typeColors: Record<NotificationType, { bg: string; border: string; icon: string }> = {
  info: { bg: 'bg-blue-50', border: 'border-blue-400', icon: '💬' },
  success: { bg: 'bg-green-50', border: 'border-green-400', icon: '✅' },
  warning: { bg: 'bg-yellow-50', border: 'border-yellow-400', icon: '⚠️' },
  error: { bg: 'bg-red-50', border: 'border-red-400', icon: '❌' },
  battle: { bg: 'bg-orange-50', border: 'border-orange-400', icon: '⚔️' },
  system: { bg: 'bg-purple-50', border: 'border-purple-400', icon: '⚙️' },
};

const priorityBadge: Record<string, { color: string; label: string }> = {
  low: { color: 'bg-gray-100 text-gray-600', label: 'LOW' },
  medium: { color: 'bg-blue-100 text-blue-600', label: 'MED' },
  high: { color: 'bg-orange-100 text-orange-600', label: 'HIGH' },
  critical: { color: 'bg-red-100 text-red-600', label: 'CRIT' },
};

const NotificationPanel: React.FC = () => {
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
  } = useNotifications();

  const [isOpen, setIsOpen] = useState(false);
  const [filter, setFilter] = useState<NotificationType | 'all'>('all');
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const filteredNotifications = filter === 'all'
    ? notifications
    : notifications.filter(n => n.type === filter);

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
  };

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.read) {
      markAsRead(notification.id);
    }
  };

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors"
      >
        <span className="text-xl">🔔</span>
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 max-h-[500px] bg-white rounded-lg shadow-xl border border-gray-200 z-50 overflow-hidden">
          <div className="p-4 bg-gradient-to-r from-purple-500 to-indigo-500 text-white">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold">알림 센터</h3>
              <div className="flex gap-2">
                <button
                  onClick={markAllAsRead}
                  className="text-xs bg-white/20 hover:bg-white/30 px-2 py-1 rounded"
                >
                  전체 읽기
                </button>
                <button
                  onClick={clearAll}
                  className="text-xs bg-red-500/50 hover:bg-red-500/70 px-2 py-1 rounded"
                >
                  전체 삭제
                </button>
              </div>
            </div>

            <div className="flex gap-1 mt-3">
              {(['all', 'battle', 'warning', 'error', 'success'] as const).map(type => (
                <button
                  key={type}
                  onClick={() => setFilter(type)}
                  className={`text-xs px-3 py-1 rounded-full transition-colors ${
                    filter === type
                      ? 'bg-white text-purple-600'
                      : 'bg-white/20 text-white hover:bg-white/30'
                  }`}
                >
                  {type === 'all' ? '전체' :
                   type === 'battle' ? '⚔️ 전투' :
                   type === 'warning' ? '⚠️ 경고' :
                   type === 'error' ? '❌ 에러' : '✅ 성공'}
                </button>
              ))}
            </div>
          </div>

          <div className="max-h-[350px] overflow-y-auto">
            {filteredNotifications.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <span className="text-4xl">📭</span>
                <p className="mt-2">알림이 없습니다</p>
              </div>
            ) : (
              filteredNotifications.map(notification => {
                const colors = typeColors[notification.type];
                const prio = priorityBadge[notification.priority];

                return (
                  <div
                    key={notification.id}
                    onClick={() => handleNotificationClick(notification)}
                    className={`p-3 border-l-4 ${colors.border} ${colors.bg} ${
                      !notification.read ? 'font-semibold' : 'opacity-75'
                    } hover:opacity-100 transition-opacity cursor-pointer border-b border-gray-100`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-2">
                        <span className="text-lg">{colors.icon}</span>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{notification.title}</span>
                            <span className={`text-xs px-1.5 py-0.5 rounded ${prio.color}`}>
                              {prio.label}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 mt-0.5">{notification.message}</p>
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeNotification(notification.id);
                        }}
                        className="text-gray-400 hover:text-gray-600 text-sm"
                      >
                        ✕
                      </button>
                    </div>
                    <div className="text-xs text-gray-400 mt-1 ml-7">
                      {formatTime(notification.timestamp)}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <div className="p-2 bg-gray-50 border-t text-center text-xs text-gray-500">
            {filteredNotifications.length}건 알림 • {unreadCount}건 읽지 않음
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationPanel;
