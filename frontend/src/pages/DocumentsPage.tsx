import { useState, useEffect, useCallback } from 'react';
import {
  Upload,
  File,
  Trash2,
  Loader2,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { documentsApi, ingestionApi, Document } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string>('');
  const [dragActive, setDragActive] = useState(false);

  const fetchDocuments = useCallback(async () => {
    try {
      const docs = await documentsApi.list();
      console.log('Fetched documents:', docs);

      // Ensure docs is an array
      if (Array.isArray(docs)) {
        setDocuments(docs);
      } else {
        console.error('Documents data is not an array:', docs);
        setDocuments([]);
      }
    } catch (error) {
      console.error('Failed to fetch documents:', error);
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleUpload = async (file: File) => {
    if (!file.name.endsWith('.pdf')) {
      alert('Only PDF files are supported');
      return;
    }

    setUploading(true);
    setUploadProgress('Uploading file...');

    try {
      const doc = await documentsApi.upload(file);
      console.log('Document uploaded:', doc);

      if (!doc || !doc.id) {
        throw new Error('Invalid document response - missing ID');
      }

      setUploadProgress('Starting ingestion...');
      console.log('Starting ingestion for doc:', doc.id);

      const jobResponse = await ingestionApi.startJob(doc.id);
      console.log('Ingestion job started:', jobResponse);

      setUploadProgress('Ingestion started successfully!');

      // Refresh documents list
      await fetchDocuments();

      setTimeout(() => {
        setUploadProgress('');
        setUploading(false);
      }, 2000);
    } catch (error: any) {
      console.error('Upload/Ingestion error:', error);
      const errorMsg = error.response?.data?.detail || error.message;
      alert(`Failed: ${errorMsg}`);
      setUploadProgress('');
      setUploading(false);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUpload(file);
  };

  const handleDelete = async (docId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      await documentsApi.delete(docId);
      setDocuments((prev) => prev.filter((doc) => doc.id !== docId));
    } catch (error: any) {
      alert(`Delete failed: ${error.response?.data?.detail || error.message}`);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className='max-w-6xl mx-auto'>
      <div className='mb-8'>
        <h1 className='text-3xl font-bold text-gray-900 mb-2'>Documents</h1>
        <p className='text-gray-600'>Upload and manage your PDF documents</p>
      </div>

      {/* Upload area */}
      <div className='card mb-8'>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={clsx(
            'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
            dragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300',
            uploading && 'opacity-50 pointer-events-none',
          )}
        >
          <div className='flex flex-col items-center gap-4'>
            <div className='w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center'>
              {uploading ? (
                <Loader2 className='w-8 h-8 text-primary-600 animate-spin' />
              ) : (
                <Upload className='w-8 h-8 text-primary-600' />
              )}
            </div>

            <div>
              <p className='text-lg font-semibold text-gray-900 mb-1'>
                {uploading ? uploadProgress : 'Upload PDF Document'}
              </p>
              <p className='text-sm text-gray-600'>
                Drag and drop or click to browse
              </p>
            </div>

            <label className='btn-primary cursor-pointer'>
              <input
                type='file'
                accept='.pdf'
                onChange={handleFileInput}
                className='hidden'
                disabled={uploading}
              />
              Select File
            </label>
          </div>
        </div>
      </div>

      {/* Documents list */}
      <div className='card'>
        <h2 className='text-xl font-bold text-gray-900 mb-4'>
          Uploaded Documents
        </h2>

        {loading ? (
          <div className='flex items-center justify-center py-12'>
            <Loader2 className='w-8 h-8 animate-spin text-primary-600' />
          </div>
        ) : documents.length === 0 ? (
          <div className='text-center py-12'>
            <File className='w-12 h-12 text-gray-400 mx-auto mb-3' />
            <p className='text-gray-600'>No documents uploaded yet</p>
          </div>
        ) : (
          <div className='space-y-3'>
            {documents.map((doc) => (
              <div
                key={doc.id}
                className='flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors'
              >
                <div className='flex items-center gap-3 flex-1 min-w-0'>
                  <div className='w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0'>
                    <File className='w-5 h-5 text-red-600' />
                  </div>

                  <div className='flex-1 min-w-0'>
                    <p className='font-medium text-gray-900 truncate'>
                      {doc.filename}
                    </p>
                    <div className='flex items-center gap-3 text-sm text-gray-500'>
                      <span>{formatFileSize(doc.size_bytes)}</span>
                      <span>•</span>
                      <span>
                        {formatDistanceToNow(new Date(doc.created_at), {
                          addSuffix: true,
                        })}
                      </span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(doc.id)}
                  className='p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors'
                  title='Delete document'
                >
                  <Trash2 className='w-5 h-5' />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
