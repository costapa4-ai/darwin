import { useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../utils/config';

export default function IdleTimer() {
  const [idleTime, setIdleTime] = useState(0); // seconds
  const [isIdle, setIsIdle] = useState(false);
  const [dreamStatus, setDreamStatus] = useState(null);

  const API_URL = API_BASE;
  const IDLE_THRESHOLD = 5 * 60; // 5 minutes in seconds

  // Track user activity
  const resetIdleTimer = useCallback(() => {
    setIdleTime(0);
    setIsIdle(false);
  }, []);

  useEffect(() => {
    // Activity listeners
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];

    events.forEach(event => {
      document.addEventListener(event, resetIdleTimer, true);
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, resetIdleTimer, true);
      });
    };
  }, [resetIdleTimer]);

  // Increment idle timer every second
  useEffect(() => {
    const interval = setInterval(() => {
      setIdleTime(prev => {
        const newTime = prev + 1;
        if (newTime >= IDLE_THRESHOLD && !isIdle) {
          setIsIdle(true);
        }
        return newTime;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isIdle]);

  // Fetch dream status periodically
  useEffect(() => {
    const fetchDreamStatus = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/phase3/dreams/status`);
        const data = await response.json();
        setDreamStatus(data);
      } catch (error) {
        console.error('Failed to fetch dream status:', error);
      }
    };

    fetchDreamStatus();
    const interval = setInterval(fetchDreamStatus, 10000); // Every 10 seconds

    return () => clearInterval(interval);
  }, []);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getIdlePercentage = () => {
    return Math.min((idleTime / IDLE_THRESHOLD) * 100, 100);
  };

  const shouldDream = dreamStatus?.idle_status?.should_dream;
  const currentlyDreaming = dreamStatus?.currently_dreaming;

  return (
    <div className="bg-slate-800 rounded-lg p-4 shadow-lg border border-slate-700">
      <div className="flex items-center justify-between">
        {/* Left: Idle Status */}
        <div className="flex items-center gap-4">
          <div className="relative">
            {/* Circular Progress */}
            <svg className="transform -rotate-90 w-16 h-16">
              <circle
                cx="32"
                cy="32"
                r="28"
                stroke="currentColor"
                strokeWidth="4"
                fill="transparent"
                className="text-slate-700"
              />
              <circle
                cx="32"
                cy="32"
                r="28"
                stroke="currentColor"
                strokeWidth="4"
                fill="transparent"
                strokeDasharray={`${2 * Math.PI * 28}`}
                strokeDashoffset={`${2 * Math.PI * 28 * (1 - getIdlePercentage() / 100)}`}
                className={`${
                  currentlyDreaming ? 'text-purple-500' :
                  isIdle ? 'text-yellow-500' :
                  'text-blue-500'
                } transition-all duration-1000`}
                strokeLinecap="round"
              />
            </svg>

            {/* Center Icon */}
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl">
                {currentlyDreaming ? '💭' : isIdle ? '😴' : '👁️'}
              </span>
            </div>
          </div>

          <div>
            <div className="text-sm font-semibold text-white">
              {currentlyDreaming ? '💭 Dreaming...' :
               isIdle ? '😴 System Idle' :
               '👁️ Active'}
            </div>
            <div className="text-xs text-slate-400">
              Idle: {formatTime(idleTime)} / {formatTime(IDLE_THRESHOLD)}
            </div>
            {isIdle && !currentlyDreaming && (
              <div className="text-xs text-yellow-400 mt-1">
                {shouldDream ? '⏳ Dream mode ready to start' : '⏳ Preparing to dream...'}
              </div>
            )}
          </div>
        </div>

        {/* Right: Dream Mode Info */}
        {dreamStatus && (
          <div className="text-right">
            <div className="text-xs text-slate-500">Dream Mode</div>
            <div className={`text-sm font-semibold ${
              dreamStatus.is_active ? 'text-purple-400' : 'text-slate-500'
            }`}>
              {dreamStatus.is_active ? 'Active' : 'Inactive'}
            </div>
            {dreamStatus.total_dreams > 0 && (
              <div className="text-xs text-slate-400 mt-1">
                {dreamStatus.total_dreams} dreams so far
              </div>
            )}
            {currentlyDreaming && dreamStatus.current_dream && (
              <div className="text-xs text-purple-400 mt-1">
                {dreamStatus.current_dream.dream_type}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="mt-3">
        <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-1000 ${
              currentlyDreaming ? 'bg-purple-500' :
              isIdle ? 'bg-yellow-500' :
              'bg-blue-500'
            }`}
            style={{ width: `${getIdlePercentage()}%` }}
          />
        </div>
      </div>

      {/* Info Text */}
      <div className="mt-2 text-xs text-slate-500">
        {currentlyDreaming ? (
          '🌟 Darwin is exploring and learning autonomously'
        ) : isIdle ? (
          '💤 No activity detected. Dream mode will start soon...'
        ) : (
          `System will enter idle mode after ${formatTime(IDLE_THRESHOLD - idleTime)} of inactivity`
        )}
      </div>
    </div>
  );
}
