import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from 'react-router-dom';
import Layout from './components/Layout';
import DocumentsPage from './pages/DocumentsPage';
import ChatPage from './pages/ChatPage';
import KnowledgeGraphPage from './pages/KnowledgeGraphPage';
import IngestionPage from './pages/IngestionPage';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path='/' element={<Navigate to='/chat' replace />} />
          <Route path='/chat' element={<ChatPage />} />
          <Route path='/documents' element={<DocumentsPage />} />
          <Route path='/ingestion' element={<IngestionPage />} />
          <Route path='/knowledge-graph' element={<KnowledgeGraphPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
