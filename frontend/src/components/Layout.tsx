import { Link, useLocation } from 'react-router-dom';
import {
  MessageSquare,
  FileText,
  GitGraph,
  Activity,
  Menu,
} from 'lucide-react';
import { useState } from 'react';
import clsx from 'clsx';

interface LayoutProps {
  children: React.ReactNode;
}

const navigation = [
  { name: 'Chat', href: '/chat', icon: MessageSquare },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Ingestion', href: '/ingestion', icon: Activity },
  { name: 'Knowledge Graph', href: '/knowledge-graph', icon: GitGraph },
];

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className='min-h-screen bg-gray-50'>
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className='fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden'
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 transform transition-transform duration-300 ease-in-out lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className='flex flex-col h-full'>
          {/* Logo */}
          <div className='flex items-center gap-3 px-6 py-6 border-b border-gray-200'>
            <div className='w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center'>
              <GitGraph className='w-6 h-6 text-white' />
            </div>
            <div>
              <h1 className='text-lg font-bold text-gray-900'>RAG System</h1>
              <p className='text-xs text-gray-500'>Knowledge Graph</p>
            </div>
          </div>

          {/* Navigation */}
          <nav className='flex-1 px-4 py-6 space-y-1'>
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={clsx(
                    'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-100',
                  )}
                >
                  <item.icon className='w-5 h-5' />
                  <span className='font-medium'>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Footer */}
          <div className='px-6 py-4 border-t border-gray-200'>
            <p className='text-xs text-gray-500'>Version 1.0.0</p>
            <p className='text-xs text-gray-400'>Production Ready</p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className='lg:pl-64'>
        {/* Mobile header */}
        <header className='sticky top-0 z-10 bg-white border-b border-gray-200 lg:hidden'>
          <div className='flex items-center justify-between px-4 py-4'>
            <button
              onClick={() => setSidebarOpen(true)}
              className='p-2 rounded-lg text-gray-500 hover:bg-gray-100'
            >
              <Menu className='w-6 h-6' />
            </button>
            <h1 className='text-lg font-bold text-gray-900'>RAG System</h1>
            <div className='w-10' /> {/* Spacer */}
          </div>
        </header>

        {/* Page content */}
        <main className='p-6 lg:p-8'>{children}</main>
      </div>
    </div>
  );
}
