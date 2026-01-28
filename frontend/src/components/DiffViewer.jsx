import { useState } from 'react';

export default function DiffViewer({ original, modified, filename }) {
  const [viewMode, setViewMode] = useState('split'); // 'split' or 'unified'

  const createDiff = () => {
    const originalLines = original.split('\n');
    const modifiedLines = modified.split('\n');

    const diff = [];
    const maxLength = Math.max(originalLines.length, modifiedLines.length);

    for (let i = 0; i < maxLength; i++) {
      const origLine = originalLines[i] || '';
      const modLine = modifiedLines[i] || '';

      if (origLine === modLine) {
        diff.push({ type: 'unchanged', original: origLine, modified: modLine, lineNum: i + 1 });
      } else if (origLine && !modLine) {
        diff.push({ type: 'removed', original: origLine, modified: '', lineNum: i + 1 });
      } else if (!origLine && modLine) {
        diff.push({ type: 'added', original: '', modified: modLine, lineNum: i + 1 });
      } else {
        diff.push({ type: 'modified', original: origLine, modified: modLine, lineNum: i + 1 });
      }
    }

    return diff;
  };

  const diff = createDiff();

  const getLineClass = (type) => {
    switch (type) {
      case 'added':
        return 'bg-green-900/20 border-l-4 border-green-500';
      case 'removed':
        return 'bg-red-900/20 border-l-4 border-red-500';
      case 'modified':
        return 'bg-yellow-900/20 border-l-4 border-yellow-500';
      default:
        return 'bg-slate-800/30';
    }
  };

  const getLinePrefix = (type) => {
    switch (type) {
      case 'added':
        return '+';
      case 'removed':
        return '-';
      case 'modified':
        return '~';
      default:
        return ' ';
    }
  };

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono text-slate-400">{filename}</span>
          <span className="text-xs px-2 py-0.5 bg-purple-900/30 text-purple-400 rounded border border-purple-500/30">
            DIFF
          </span>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('split')}
            className={`px-3 py-1 text-xs rounded ${
              viewMode === 'split'
                ? 'bg-purple-600 text-white'
                : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
            }`}
          >
            Split View
          </button>
          <button
            onClick={() => setViewMode('unified')}
            className={`px-3 py-1 text-xs rounded ${
              viewMode === 'unified'
                ? 'bg-purple-600 text-white'
                : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
            }`}
          >
            Unified
          </button>
        </div>
      </div>

      {/* Diff Content */}
      <div className="max-h-96 overflow-auto">
        {viewMode === 'split' ? (
          /* Split View - Side by Side */
          <div className="grid grid-cols-2 divide-x divide-slate-700">
            {/* Original (Left) */}
            <div>
              <div className="px-4 py-2 bg-slate-800 border-b border-slate-700 text-xs text-slate-400 font-semibold">
                Original
              </div>
              <div className="font-mono text-xs">
                {diff.map((line, idx) => (
                  <div
                    key={`orig-${idx}`}
                    className={`px-4 py-1 ${
                      line.type === 'removed' || line.type === 'modified'
                        ? 'bg-red-900/20'
                        : 'bg-slate-800/30'
                    }`}
                  >
                    <span className="text-slate-600 w-8 inline-block select-none">
                      {line.original ? line.lineNum : ''}
                    </span>
                    <span className={`${
                      line.type === 'removed' || line.type === 'modified'
                        ? 'text-red-400'
                        : 'text-slate-300'
                    }`}>
                      {line.original || '\u00A0'}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Modified (Right) */}
            <div>
              <div className="px-4 py-2 bg-slate-800 border-b border-slate-700 text-xs text-slate-400 font-semibold">
                Proposed
              </div>
              <div className="font-mono text-xs">
                {diff.map((line, idx) => (
                  <div
                    key={`mod-${idx}`}
                    className={`px-4 py-1 ${
                      line.type === 'added' || line.type === 'modified'
                        ? 'bg-green-900/20'
                        : 'bg-slate-800/30'
                    }`}
                  >
                    <span className="text-slate-600 w-8 inline-block select-none">
                      {line.modified ? line.lineNum : ''}
                    </span>
                    <span className={`${
                      line.type === 'added' || line.type === 'modified'
                        ? 'text-green-400'
                        : 'text-slate-300'
                    }`}>
                      {line.modified || '\u00A0'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Unified View */
          <div className="font-mono text-xs">
            <div className="px-4 py-2 bg-slate-800 border-b border-slate-700 text-xs text-slate-400 font-semibold">
              Unified Diff
            </div>
            {diff.map((line, idx) => (
              <div key={`unified-${idx}`} className={`px-4 py-1 ${getLineClass(line.type)}`}>
                <span className="text-slate-600 w-8 inline-block select-none">
                  {line.lineNum}
                </span>
                <span className="text-slate-500 w-4 inline-block select-none">
                  {getLinePrefix(line.type)}
                </span>
                <span className={`${
                  line.type === 'added' ? 'text-green-400' :
                  line.type === 'removed' ? 'text-red-400' :
                  line.type === 'modified' ? 'text-yellow-400' :
                  'text-slate-300'
                }`}>
                  {line.type === 'removed' ? line.original :
                   line.type === 'added' ? line.modified :
                   line.type === 'modified' ? line.modified :
                   line.original || '\u00A0'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="px-4 py-2 border-t border-slate-700 flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 bg-green-500 rounded"></span>
          <span className="text-slate-400">
            {diff.filter(l => l.type === 'added').length} additions
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 bg-red-500 rounded"></span>
          <span className="text-slate-400">
            {diff.filter(l => l.type === 'removed').length} deletions
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 bg-yellow-500 rounded"></span>
          <span className="text-slate-400">
            {diff.filter(l => l.type === 'modified').length} modifications
          </span>
        </div>
      </div>
    </div>
  );
}
