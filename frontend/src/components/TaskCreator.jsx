import { useState } from 'react';
import { createTask } from '../utils/api';

export default function TaskCreator({ onTaskCreated }) {
  const [description, setDescription] = useState('');
  const [type, setType] = useState('algorithm');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!description.trim()) {
      alert('Please enter a task description');
      return;
    }

    setLoading(true);

    try {
      const task = await createTask({
        description,
        type,
        parameters: {}
      });

      console.log('Task created:', task);
      setDescription('');

      if (onTaskCreated) {
        onTaskCreated(task);
      }
    } catch (error) {
      console.error('Error creating task:', error);
      alert('Failed to create task: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
      <h2 className="text-xl font-bold mb-4 text-green-400">🎯 Create New Task</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">
            Task Description
          </label>
          <textarea
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-green-500"
            placeholder="Example: create a function that calculates factorial of a number"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            disabled={loading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            Task Type
          </label>
          <select
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            value={type}
            onChange={(e) => setType(e.target.value)}
            disabled={loading}
          >
            <option value="algorithm">Algorithm</option>
            <option value="data_processing">Data Processing</option>
            <option value="text_analysis">Text Analysis</option>
            <option value="math">Mathematics</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-green-600 hover:bg-green-700 disabled:bg-slate-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          {loading ? '⏳ Creating...' : '🚀 Create Task'}
        </button>
      </form>
    </div>
  );
}
