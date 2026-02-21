import { useState, useEffect } from 'react';
import { Loader2, CheckCircle, XCircle, Clock, PlayCircle } from 'lucide-react';
import { ingestionApi, IngestionJob } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';

const STATUS_CONFIG = {
  pending: { icon: Clock, color: 'text-gray-500', bg: 'bg-gray-100' },
  running: { icon: Loader2, color: 'text-blue-500', bg: 'bg-blue-100' },
  done: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100' },
  failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-100' },
  canceled: { icon: XCircle, color: 'text-gray-500', bg: 'bg-gray-100' },
};

const STEPS = [
  { key: 'extract_text', label: 'Extract Text' },
  { key: 'chunk', label: 'Chunk Text' },
  { key: 'extract_triples_rebel', label: 'REBEL Extraction' },
  { key: 'extract_triples_llm', label: 'LLM Extraction' },
  { key: 'union_pool', label: 'Union Pool' },
  { key: 'canonicalize', label: 'Canonicalize' },
  { key: 'upsert_graph', label: 'Upsert Graph' },
  { key: 'build_text_index', label: 'Build Index' },
];

export default function IngestionPage() {
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState<IngestionJob | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchJobs = async () => {
    try {
      const data = await ingestionApi.listJobs();
      console.log('Fetched jobs:', data);

      // Ensure data is an array
      if (Array.isArray(data)) {
        setJobs(data);
      } else {
        console.error('Jobs data is not an array:', data);
        setJobs([]);
      }

      // Update selected job if it exists
      if (selectedJob) {
        const updated = data.find((j) => j.id === selectedJob.id);
        if (updated) setSelectedJob(updated);
      }
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
      setJobs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();

    const interval = setInterval(() => {
      if (autoRefresh) fetchJobs();
    }, 3000);

    return () => clearInterval(interval);
  }, [autoRefresh]);

  const getStepStatus = (job: IngestionJob, stepKey: string) => {
    const stepData = job.progress[stepKey];
    if (!stepData) return 'pending';
    return stepData.status || 'pending';
  };

  return (
    <div className='max-w-7xl mx-auto'>
      <div className='mb-8 flex items-center justify-between'>
        <div>
          <h1 className='text-3xl font-bold text-gray-900 mb-2'>
            Ingestion Jobs
          </h1>
          <p className='text-gray-600'>Monitor document processing pipeline</p>
        </div>

        <label className='flex items-center gap-2 cursor-pointer'>
          <input
            type='checkbox'
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className='w-4 h-4 text-primary-600 rounded'
          />
          <span className='text-sm text-gray-700'>Auto-refresh</span>
        </label>
      </div>

      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {/* Jobs list */}
        <div className='card'>
          <h2 className='text-xl font-bold text-gray-900 mb-4'>Recent Jobs</h2>

          {loading ? (
            <div className='flex items-center justify-center py-12'>
              <Loader2 className='w-8 h-8 animate-spin text-primary-600' />
            </div>
          ) : jobs.length === 0 ? (
            <div className='text-center py-12'>
              <PlayCircle className='w-12 h-12 text-gray-400 mx-auto mb-3' />
              <p className='text-gray-600'>No ingestion jobs yet</p>
            </div>
          ) : (
            <div className='space-y-3'>
              {jobs.map((job) => {
                const StatusIcon = STATUS_CONFIG[job.status].icon;
                return (
                  <button
                    key={job.id}
                    onClick={() => setSelectedJob(job)}
                    className={clsx(
                      'w-full text-left p-4 rounded-lg border-2 transition-all',
                      selectedJob?.id === job.id
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300',
                    )}
                  >
                    <div className='flex items-start justify-between mb-2'>
                      <div className='flex items-center gap-2'>
                        <div
                          className={clsx(
                            'p-1.5 rounded',
                            STATUS_CONFIG[job.status].bg,
                          )}
                        >
                          <StatusIcon
                            className={clsx(
                              'w-4 h-4',
                              STATUS_CONFIG[job.status].color,
                              job.status === 'running' && 'animate-spin',
                            )}
                          />
                        </div>
                        <div>
                          <p className='font-medium text-gray-900'>
                            Job {job.id.slice(0, 12)}...
                          </p>
                          <p className='text-xs text-gray-500'>
                            Doc: {job.doc_id.slice(0, 12)}...
                          </p>
                        </div>
                      </div>
                      <span className='text-xs text-gray-500'>
                        {formatDistanceToNow(new Date(job.created_at), {
                          addSuffix: true,
                        })}
                      </span>
                    </div>

                    {job.current_step && (
                      <p className='text-sm text-gray-600 mt-2'>
                        Current: {job.current_step.replace(/_/g, ' ')}
                      </p>
                    )}

                    {job.error_message && (
                      <p className='text-sm text-red-600 mt-2'>
                        {job.error_message}
                      </p>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Job details */}
        <div className='card'>
          <h2 className='text-xl font-bold text-gray-900 mb-4'>
            Pipeline Steps
          </h2>

          {selectedJob ? (
            <div className='space-y-3'>
              {STEPS.map((step, idx) => {
                const status = getStepStatus(selectedJob, step.key);
                const stepData = selectedJob.progress[step.key];
                const StatusIcon = STATUS_CONFIG[status]?.icon || Clock;

                return (
                  <div key={step.key} className='relative'>
                    {idx < STEPS.length - 1 && (
                      <div className='absolute left-5 top-10 w-0.5 h-full bg-gray-200' />
                    )}

                    <div className='flex items-start gap-3'>
                      <div
                        className={clsx(
                          'p-2 rounded-lg z-10',
                          STATUS_CONFIG[status]?.bg || 'bg-gray-100',
                        )}
                      >
                        <StatusIcon
                          className={clsx(
                            'w-5 h-5',
                            STATUS_CONFIG[status]?.color || 'text-gray-500',
                            status === 'running' && 'animate-spin',
                          )}
                        />
                      </div>

                      <div className='flex-1 pt-1'>
                        <p className='font-medium text-gray-900'>
                          {step.label}
                        </p>
                        {stepData?.stats && (
                          <div className='text-sm text-gray-600 mt-1'>
                            {Object.entries(stepData.stats).map(
                              ([key, value]) => (
                                <span key={key} className='mr-3'>
                                  {key}: {String(value)}
                                </span>
                              ),
                            )}
                          </div>
                        )}
                        {stepData?.error && (
                          <p className='text-sm text-red-600 mt-1'>
                            {stepData.error}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}

              <div className='mt-6 pt-6 border-t border-gray-200'>
                <div className='grid grid-cols-2 gap-4 text-sm'>
                  <div>
                    <p className='text-gray-500'>Started</p>
                    <p className='font-medium'>
                      {selectedJob.started_at
                        ? formatDistanceToNow(
                            new Date(selectedJob.started_at),
                            { addSuffix: true },
                          )
                        : 'Not started'}
                    </p>
                  </div>
                  <div>
                    <p className='text-gray-500'>Completed</p>
                    <p className='font-medium'>
                      {selectedJob.completed_at
                        ? formatDistanceToNow(
                            new Date(selectedJob.completed_at),
                            { addSuffix: true },
                          )
                        : 'In progress'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className='text-center py-12'>
              <p className='text-gray-600'>Select a job to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
