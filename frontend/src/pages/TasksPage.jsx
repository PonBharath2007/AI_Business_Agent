import React, { useState, useEffect, useCallback } from 'react';
import {
  CheckSquare,
  Plus,
  Filter,
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  Sparkles,
  Trash2,
  User,
  Calendar
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';

const TasksPage = ({ onNavigate }) => {
  const { addToast } = useNotifications();

  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [createModalOpen, setCreateModalOpen] = useState(false);

  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    priority: 'Medium',
    status: 'Pending',
    due_date: new Date().toISOString().split('T')[0],
    assigned_user: 'Digital Employee'
  });

  const fetchTasks = useCallback(async () => {
    try {
      const res = await api.get('/tasks');
      setTasks(res.data || []);
    } catch (err) {
      console.error('Error fetching tasks:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleCreateTask = async (e) => {
    e.preventDefault();
    try {
      await api.post('/tasks', newTask);
      addToast('success', 'Task Created', `Task '${newTask.title}' added.`);
      setCreateModalOpen(false);
      setNewTask({
        title: '',
        description: '',
        priority: 'Medium',
        status: 'Pending',
        due_date: new Date().toISOString().split('T')[0],
        assigned_user: 'Digital Employee'
      });
      fetchTasks();
    } catch (err) {
      addToast('error', 'Error', 'Failed to create task.');
    }
  };

  const handleCompleteTask = async (taskId) => {
    try {
      await api.post(`/tasks/${taskId}/complete`);
      addToast('success', 'Task Resolved', 'Marked task as Completed.');
      fetchTasks();
    } catch (err) {
      addToast('error', 'Error', 'Failed to complete task.');
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (!window.confirm('Delete this task?')) return;
    try {
      await api.delete(`/tasks/${taskId}`);
      addToast('info', 'Task Removed', 'Task deleted.');
      fetchTasks();
    } catch (err) {
      addToast('error', 'Error', 'Failed to delete task.');
    }
  };

  const filteredTasks = tasks.filter((t) => {
    const q = searchQuery.toLowerCase();
    const matchesQuery = t.title?.toLowerCase().includes(q) || t.description?.toLowerCase().includes(q);
    const matchesPriority = priorityFilter === 'all' || t.priority?.toLowerCase() === priorityFilter.toLowerCase();
    const matchesStatus = statusFilter === 'all' || t.status?.toLowerCase() === statusFilter.toLowerCase();
    return matchesQuery && matchesPriority && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Operations & AI Task Center
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Auto-detected tasks from invoices and contracts, prioritized by urgency and impact.
          </p>
        </div>

        <Button
          onClick={() => setCreateModalOpen(true)}
          variant="primary"
          size="sm"
          icon={Plus}
          className="text-xs self-start sm:self-auto"
        >
          Create Task
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-panel p-3 rounded-2xl border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          {/* Priority pills */}
          <div className="flex items-center gap-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
            {['all', 'High', 'Medium', 'Low'].map((p) => (
              <button
                key={p}
                onClick={() => setPriorityFilter(p)}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                  priorityFilter === p ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
                }`}
              >
                {p}
              </button>
            ))}
          </div>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Statuses</option>
            <option value="Pending">Pending</option>
            <option value="In Progress">In Progress</option>
            <option value="Completed">Completed</option>
          </select>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tasks..."
            className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Task List */}
      <div className="space-y-3">
        {!filteredTasks.length ? (
          <EmptyState
            icon={CheckSquare}
            title="No tasks found"
            description="You're all caught up! No tasks match the current filters."
            actionText="Create New Task"
            onAction={() => setCreateModalOpen(true)}
          />
        ) : (
          filteredTasks.map((task) => {
            const isDone = task.status === 'Completed';
            const isHigh = task.priority === 'High';

            return (
              <div
                key={task.id}
                className={`glass-panel rounded-2xl p-4 sm:p-5 border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                  isDone
                    ? 'opacity-60 border-slate-800/60 bg-slate-950/30'
                    : isHigh
                    ? 'border-rose-500/30 bg-gradient-to-r from-rose-950/15 via-slate-900/50 to-slate-900/40'
                    : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-start gap-3.5 min-w-0">
                  <button
                    onClick={() => handleCompleteTask(task.id)}
                    className={`mt-0.5 w-5 h-5 rounded-lg border flex items-center justify-center transition-colors cursor-pointer shrink-0 ${
                      isDone
                        ? 'bg-emerald-500 border-emerald-500 text-white'
                        : 'border-slate-600 hover:border-emerald-400 text-transparent hover:text-emerald-400'
                    }`}
                  >
                    <CheckCircle2 className="w-4 h-4" />
                  </button>

                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className={`text-sm font-bold ${isDone ? 'line-through text-slate-400' : 'text-white'}`}>
                        {task.title}
                      </h4>
                      <Badge variant={task.priority === 'High' ? 'urgent' : (task.priority === 'Medium' ? 'warning' : 'info')}>
                        {task.priority} Priority
                      </Badge>
                      <Badge variant={task.source_type === 'AI Workflow' || task.source_type === 'AI Document' ? 'ai' : 'gray'}>
                        {task.source_type}
                      </Badge>
                    </div>

                    {task.description && (
                      <p className="text-xs text-slate-300 mt-1 leading-relaxed">{task.description}</p>
                    )}

                    <div className="flex flex-wrap items-center gap-4 mt-2.5 text-[11px] text-slate-400">
                      <span className="flex items-center gap-1">
                        <User className="w-3.5 h-3.5 text-slate-500" />
                        Assigned: <strong className="text-slate-300">{task.assigned_user}</strong>
                      </span>
                      {task.due_date && (
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5 text-slate-500" />
                          Due: <strong className={isHigh ? 'text-rose-300' : 'text-slate-300'}>{task.due_date}</strong>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                  {!isDone && (
                    <Button
                      onClick={() => handleCompleteTask(task.id)}
                      variant="success"
                      size="sm"
                      icon={CheckCircle2}
                      className="text-xs"
                    >
                      Complete
                    </Button>
                  )}
                  <button
                    onClick={() => handleDeleteTask(task.id)}
                    className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
                    title="Delete Task"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Create Task Modal */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Create New Operations Task"
      >
        <form onSubmit={handleCreateTask} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Task Title</label>
            <input
              type="text"
              value={newTask.title}
              onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
              placeholder="e.g. Follow up with ABC Ltd regarding overdue payment"
              required
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Description</label>
            <textarea
              value={newTask.description}
              onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
              placeholder="Details and context..."
              rows={3}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Priority</label>
              <select
                value={newTask.priority}
                onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="High">High</option>
                <option value="Medium">Medium</option>
                <option value="Low">Low</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Due Date</label>
              <input
                type="date"
                value={newTask.due_date}
                onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Assignee</label>
            <input
              type="text"
              value={newTask.assigned_user}
              onChange={(e) => setNewTask({ ...newTask, assigned_user: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
            <Button onClick={() => setCreateModalOpen(false)} variant="ghost" size="sm">
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm">
              Save Task
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default TasksPage;
