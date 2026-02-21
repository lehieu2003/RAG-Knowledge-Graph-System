import { useState, useEffect } from 'react';
import { Search, Loader2, GitGraph, Users, FileText } from 'lucide-react';
import { kgApi, Entity } from '@/lib/api';

export default function KnowledgeGraphPage() {
  const [query, setQuery] = useState('');
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<{
    entities: number;
    relations: number;
    documents: number;
  } | null>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const data = await kgApi.getStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const results = await kgApi.searchEntities(query, 50);
      setEntities(results);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className='max-w-6xl mx-auto'>
      <div className='mb-8'>
        <h1 className='text-3xl font-bold text-gray-900 mb-2'>
          Knowledge Graph
        </h1>
        <p className='text-gray-600'>Explore entities and relationships</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className='grid grid-cols-1 md:grid-cols-3 gap-6 mb-8'>
          <div className='card'>
            <div className='flex items-center gap-3'>
              <div className='w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center'>
                <Users className='w-6 h-6 text-blue-600' />
              </div>
              <div>
                <p className='text-2xl font-bold text-gray-900'>
                  {stats.entities.toLocaleString()}
                </p>
                <p className='text-sm text-gray-600'>Entities</p>
              </div>
            </div>
          </div>

          <div className='card'>
            <div className='flex items-center gap-3'>
              <div className='w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center'>
                <GitGraph className='w-6 h-6 text-green-600' />
              </div>
              <div>
                <p className='text-2xl font-bold text-gray-900'>
                  {stats.relations.toLocaleString()}
                </p>
                <p className='text-sm text-gray-600'>Relations</p>
              </div>
            </div>
          </div>

          <div className='card'>
            <div className='flex items-center gap-3'>
              <div className='w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center'>
                <FileText className='w-6 h-6 text-purple-600' />
              </div>
              <div>
                <p className='text-2xl font-bold text-gray-900'>
                  {stats.documents.toLocaleString()}
                </p>
                <p className='text-sm text-gray-600'>Documents</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Search */}
      <div className='card mb-8'>
        <form onSubmit={handleSearch} className='flex gap-2'>
          <input
            type='text'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search entities (e.g., 'neural network', 'machine learning')..."
            className='input flex-1'
          />
          <button
            type='submit'
            className='btn-primary flex items-center gap-2'
            disabled={loading}
          >
            {loading ? (
              <Loader2 className='w-5 h-5 animate-spin' />
            ) : (
              <Search className='w-5 h-5' />
            )}
            Search
          </button>
        </form>
      </div>

      {/* Results */}
      <div className='card'>
        <h2 className='text-xl font-bold text-gray-900 mb-4'>
          {entities.length > 0
            ? `Found ${entities.length} entities`
            : 'Search Results'}
        </h2>

        {loading ? (
          <div className='flex items-center justify-center py-12'>
            <Loader2 className='w-8 h-8 animate-spin text-primary-600' />
          </div>
        ) : entities.length === 0 ? (
          <div className='text-center py-12'>
            <Search className='w-12 h-12 text-gray-400 mx-auto mb-3' />
            <p className='text-gray-600'>
              {query
                ? 'No entities found'
                : 'Search for entities in the knowledge graph'}
            </p>
          </div>
        ) : (
          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
            {entities.map((entity) => (
              <div
                key={entity.id}
                className='p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors'
              >
                <div className='flex items-start justify-between mb-2'>
                  <h3 className='font-semibold text-gray-900 line-clamp-2'>
                    {entity.canonical_name}
                  </h3>
                  <span className='text-xs bg-primary-100 text-primary-700 px-2 py-1 rounded-full whitespace-nowrap ml-2'>
                    {entity.entity_type}
                  </span>
                </div>

                {entity.aliases && entity.aliases.length > 0 && (
                  <div className='text-sm text-gray-600 mt-2'>
                    <span className='font-medium'>Aliases:</span>{' '}
                    {entity.aliases.slice(0, 3).join(', ')}
                    {entity.aliases.length > 3 &&
                      ` +${entity.aliases.length - 3} more`}
                  </div>
                )}

                {entity.metadata && Object.keys(entity.metadata).length > 0 && (
                  <div className='mt-2 pt-2 border-t border-gray-200'>
                    {Object.entries(entity.metadata)
                      .slice(0, 2)
                      .map(([key, value]) => (
                        <div key={key} className='text-xs text-gray-500'>
                          <span className='font-medium'>{key}:</span>{' '}
                          {String(value)}
                        </div>
                      ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
