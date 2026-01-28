import { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import './DarwinMessages.css';

/**
 * DarwinMessages - Real-time communication feed from Darwin
 * Shows proactive messages about activities, discoveries, learnings, etc.
 */
export default function DarwinMessages() {
  const { events, isConnected } = useWebSocket();
  const [messages, setMessages] = useState([]);
  const [filter, setFilter] = useState('all'); // all, high, medium, low
  const messagesEndRef = useRef(null);

  // Filter Darwin messages from WebSocket events
  useEffect(() => {
    const darwinMessages = events
      .filter(event => event.type === 'darwin_message')
      .slice(-50); // Keep last 50 messages

    setMessages(darwinMessages);
  }, [events]);

  // Auto-scroll to bottom when new message arrives
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Get emoji for message type
  const getMessageIcon = (messageType) => {
    const icons = {
      activity_start: '🚀',
      activity_complete: '✅',
      discovery: '🔍',
      learning: '🧠',
      celebration: '🎉',
      frustration: '😤',
      question: '❓',
      curiosity: '✨',
      reflection: '💭',
      surprise: '😲',
      insight: '💡'
    };
    return icons[messageType] || '📢';
  };

  // Get color class for priority
  const getPriorityClass = (priority) => {
    const classes = {
      urgent: 'priority-urgent',
      high: 'priority-high',
      medium: 'priority-medium',
      low: 'priority-low'
    };
    return classes[priority] || 'priority-medium';
  };

  // Format timestamp
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('pt-PT', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // Filter messages by priority
  const filteredMessages = messages.filter(msg => {
    if (filter === 'all') return true;
    return msg.priority === filter;
  });

  // Get message stats
  const stats = {
    total: messages.length,
    urgent: messages.filter(m => m.priority === 'urgent').length,
    high: messages.filter(m => m.priority === 'high').length,
    medium: messages.filter(m => m.priority === 'medium').length,
    low: messages.filter(m => m.priority === 'low').length
  };

  return (
    <div className="darwin-messages">
      <div className="darwin-messages-header">
        <h2>
          <span className="darwin-icon">🗣️</span>
          Darwin's Messages
          <span className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '🟢 Live' : '🔴 Offline'}
          </span>
        </h2>

        <div className="message-stats">
          <span className="stat">Total: {stats.total}</span>
          {stats.urgent > 0 && <span className="stat urgent">🚨 {stats.urgent}</span>}
          {stats.high > 0 && <span className="stat high">⚠️ {stats.high}</span>}
          <span className="stat medium">📊 {stats.medium}</span>
          <span className="stat low">💬 {stats.low}</span>
        </div>

        <div className="message-filters">
          <button
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          {stats.urgent > 0 && (
            <button
              className={filter === 'urgent' ? 'active' : ''}
              onClick={() => setFilter('urgent')}
            >
              Urgent
            </button>
          )}
          <button
            className={filter === 'high' ? 'active' : ''}
            onClick={() => setFilter('high')}
          >
            High
          </button>
          <button
            className={filter === 'medium' ? 'active' : ''}
            onClick={() => setFilter('medium')}
          >
            Medium
          </button>
          <button
            className={filter === 'low' ? 'active' : ''}
            onClick={() => setFilter('low')}
          >
            Low
          </button>
        </div>
      </div>

      <div className="messages-feed">
        {filteredMessages.length === 0 ? (
          <div className="no-messages">
            <p>
              {isConnected
                ? '🎧 Listening for Darwin\'s messages...'
                : '⚠️ Reconnecting to Darwin...'}
            </p>
            <p className="hint">
              Darwin will share thoughts, discoveries, and updates here in real-time
            </p>
          </div>
        ) : (
          filteredMessages.map((msg, index) => (
            <div
              key={msg.id || `${msg.timestamp}-${msg.message_type}-${index}`}
              className={`message-card ${getPriorityClass(msg.priority)} message-enter`}
            >
              <div className="message-header">
                <span className="message-icon">
                  {getMessageIcon(msg.message_type)}
                </span>
                <span className="message-type">
                  {msg.message_type?.replace(/_/g, ' ')}
                </span>
                <span className="message-time">
                  {formatTime(msg.timestamp)}
                </span>
                <span className={`priority-badge ${msg.priority}`}>
                  {msg.priority}
                </span>
              </div>

              <div className="message-content">
                {msg.message}
              </div>

              {msg.data && Object.keys(msg.data).length > 0 && (
                <details className="message-details">
                  <summary>View details</summary>
                  <div className="message-data">
                    {Object.entries(msg.data).map(([key, value]) => (
                      <div key={key} className="data-item">
                        <strong>{key}:</strong>
                        <span>{JSON.stringify(value, null, 2)}</span>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
