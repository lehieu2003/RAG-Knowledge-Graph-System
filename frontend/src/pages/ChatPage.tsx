import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Info, Network, List } from 'lucide-react';
import { chatApi, ChatResponse, Evidence } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import clsx from 'clsx';
import GraphVisualization from '@/components/GraphVisualization';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  response?: ChatResponse;
  loading?: boolean;
}

const MODES = [
  {
    value: 'auto',
    label: 'Auto',
    description: 'Intelligent routing (recommended)',
  },
  { value: 'graph', label: 'Graph', description: 'GraphRAG only' },
  { value: 'text', label: 'Text', description: 'BM25 only' },
  { value: 'hybrid', label: 'Hybrid', description: 'Combined approach' },
] as const;

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<'auto' | 'graph' | 'text' | 'hybrid'>(
    'auto',
  );
  const [isLoading, setIsLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'text' | 'graph'>('text');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', content: input };
    const loadingMessage: Message = {
      role: 'assistant',
      content: '',
      loading: true,
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await chatApi.ask({ question: input, mode });

      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: 'assistant',
          content: response.answer,
          response,
          loading: false,
        };
        return updated;
      });
    } catch (error: any) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: 'assistant',
          content: `Error: ${error.response?.data?.detail || error.message}`,
          loading: false,
        };
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className='flex flex-col'>
      {/* Header */}
      <div className='mb-6'>
        <h1 className='text-3xl font-bold text-gray-900 mb-2'>
          Chat with Knowledge Graph
        </h1>
        <p className='text-gray-600'>Ask questions about your documents</p>
      </div>

      {/* Mode selector */}
      <div className='card'>
        <label className='block text-sm font-medium text-gray-700 mb-2'>
          Retrieval Mode
        </label>
        <div className='grid grid-cols-2 md:grid-cols-4 gap-2'>
          {MODES.map((m) => (
            <button
              key={m.value}
              onClick={() => setMode(m.value)}
              className={clsx(
                'p-3 rounded-lg border-2 transition-all text-left',
                mode === m.value
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300',
              )}
            >
              <div className='font-semibold text-sm'>{m.label}</div>
              <div className='text-xs text-gray-500 mt-1'>{m.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className='flex-1 card overflow-y-auto mb-4 space-y-4'>
        {messages.length === 0 && (
          <div className='text-center py-12'>
            <div className='w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4'>
              <Info className='w-8 h-8 text-primary-600' />
            </div>
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>
              Start a conversation
            </h3>
            <p className='text-gray-600 max-w-md mx-auto'>
              Ask questions about your documents and I'll retrieve relevant
              information from the knowledge graph.
            </p>
          </div>
        )}

        {messages.map((message, idx) => (
          <div
            key={idx}
            className={clsx(
              'flex',
              message.role === 'user' ? 'justify-end' : 'justify-start',
            )}
          >
            <div
              className={clsx(
                'max-w-[80%] rounded-lg px-4 py-3',
                message.role === 'user'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-900',
              )}
            >
              {message.loading ? (
                <div className='flex items-center gap-2'>
                  <Loader2 className='w-4 h-4 animate-spin' />
                  <span className='text-sm'>Thinking...</span>
                </div>
              ) : (
                <>
                  <div className='prose prose-sm max-w-none'>
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>

                  {message.response && (
                    <div className='mt-3 pt-3 border-t border-gray-200'>
                      <div className='flex items-center justify-between mb-2'>
                        <div className='flex items-center gap-4 text-xs text-gray-600'>
                          <span className='font-medium'>
                            Mode:{' '}
                            <span className='text-primary-600'>
                              {message.response.mode_used}
                            </span>
                          </span>
                          <span>
                            Confidence:{' '}
                            {(message.response.confidence * 100).toFixed(0)}%
                          </span>
                          <span>
                            Sources: {message.response.evidence.length}
                          </span>
                        </div>

                        {/* View mode toggle */}
                        {message.response.evidence.length > 0 && (
                          <div className='flex items-center gap-1 bg-white rounded-lg p-1'>
                            <button
                              onClick={() => setViewMode('text')}
                              className={clsx(
                                'px-2 py-1 rounded text-xs font-medium transition-colors',
                                viewMode === 'text'
                                  ? 'bg-primary-100 text-primary-700'
                                  : 'text-gray-600 hover:bg-gray-100',
                              )}
                            >
                              <List className='w-3 h-3 inline mr-1' />
                              List
                            </button>
                            <button
                              onClick={() => setViewMode('graph')}
                              className={clsx(
                                'px-2 py-1 rounded text-xs font-medium transition-colors',
                                viewMode === 'graph'
                                  ? 'bg-primary-100 text-primary-700'
                                  : 'text-gray-600 hover:bg-gray-100',
                              )}
                            >
                              <Network className='w-3 h-3 inline mr-1' />
                              Graph
                            </button>
                          </div>
                        )}
                      </div>

                      {message.response.evidence.length > 0 && (
                        <>
                          {viewMode === 'text' ? (
                            <div className='space-y-2'>
                              {message.response.evidence
                                .slice(0, 3)
                                .map((ev, i) => (
                                  <div
                                    key={i}
                                    className='text-xs bg-white rounded p-2'
                                  >
                                    <div className='font-medium text-gray-700'>
                                      📄 Document {ev.doc_id.slice(0, 12)}...
                                    </div>
                                    <div className='text-gray-500'>
                                      Page {ev.page_start}-{ev.page_end} •
                                      Score: {(ev.score * 100).toFixed(0)}%
                                    </div>
                                    {ev.snippet && (
                                      <div className='text-gray-600 mt-1 text-xs italic'>
                                        {ev.snippet.length > 100
                                          ? ev.snippet.substring(0, 100) + '...'
                                          : ev.snippet}
                                      </div>
                                    )}
                                  </div>
                                ))}
                            </div>
                          ) : (
                            <GraphVisualization
                              evidence={message.response.evidence}
                            />
                          )}
                        </>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className='card'>
        <div className='flex gap-2'>
          <input
            type='text'
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder='Ask a question about your documents...'
            className='input flex-1'
            disabled={isLoading}
          />
          <button
            type='submit'
            disabled={isLoading || !input.trim()}
            className='btn-primary flex items-center gap-2'
          >
            {isLoading ? (
              <Loader2 className='w-5 h-5 animate-spin' />
            ) : (
              <Send className='w-5 h-5' />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
