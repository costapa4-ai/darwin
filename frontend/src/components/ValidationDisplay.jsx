export default function ValidationDisplay({ validation }) {
  if (!validation) return null;

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getScoreRing = (score) => {
    const percentage = score;
    const circumference = 2 * Math.PI * 40;
    const offset = circumference - (percentage / 100) * circumference;

    return { circumference, offset };
  };

  const { circumference, offset } = getScoreRing(validation.score);

  return (
    <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30">
      <div className="flex items-start gap-4">
        {/* Score Circle */}
        <div className="flex-shrink-0">
          <div className="relative w-24 h-24">
            <svg className="transform -rotate-90 w-24 h-24">
              <circle
                cx="48"
                cy="48"
                r="40"
                stroke="currentColor"
                strokeWidth="8"
                fill="transparent"
                className="text-slate-700"
              />
              <circle
                cx="48"
                cy="48"
                r="40"
                stroke="currentColor"
                strokeWidth="8"
                fill="transparent"
                strokeDasharray={circumference}
                strokeDashoffset={offset}
                className={getScoreColor(validation.score)}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className={`text-2xl font-bold ${getScoreColor(validation.score)}`}>
                  {validation.score}
                </div>
                <div className="text-xs text-slate-500">score</div>
              </div>
            </div>
          </div>
        </div>

        {/* Validation Details */}
        <div className="flex-1 space-y-3">
          {/* Status */}
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${validation.valid ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className={`font-semibold ${validation.valid ? 'text-green-400' : 'text-red-400'}`}>
              {validation.valid ? '✅ Validation Passed' : '❌ Validation Failed'}
            </span>
          </div>

          {/* Checks Passed */}
          {validation.checks_passed && validation.checks_passed.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-1">Checks Passed:</div>
              <div className="space-y-1">
                {validation.checks_passed.map((check, idx) => (
                  <div key={idx} className="text-xs text-green-400 flex items-center gap-1">
                    <span>✓</span>
                    <span>{check}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Checks Failed */}
          {validation.checks_failed && validation.checks_failed.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-1">Checks Failed:</div>
              <div className="space-y-1">
                {validation.checks_failed.map((check, idx) => (
                  <div key={idx} className="text-xs text-red-400 flex items-center gap-1">
                    <span>✗</span>
                    <span>{check}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Warnings */}
          {validation.warnings && validation.warnings.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-1">Warnings:</div>
              <div className="space-y-1">
                {validation.warnings.map((warning, idx) => (
                  <div key={idx} className="text-xs text-yellow-400 flex items-center gap-1">
                    <span>⚠</span>
                    <span>{warning}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Security Issues */}
          {validation.security_issues && validation.security_issues.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-1">Security Issues:</div>
              <div className="space-y-1">
                {validation.security_issues.map((issue, idx) => (
                  <div key={idx} className="text-xs text-red-400 flex items-center gap-1">
                    <span>🚨</span>
                    <span>{issue}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
