import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import EntityViewer from './pages/EntityViewer';
import SchemaBuilder from './components/SchemaBuilder';

const queryClient = new QueryClient();

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route 
            path="/login" 
            element={<Login onLogin={() => setIsAuthenticated(true)} />} 
          />
          <Route 
            path="/" 
            element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/entity/:entityCode" 
            element={isAuthenticated ? <EntityViewer /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/admin/schemas" 
            element={isAuthenticated ? <SchemaBuilder /> : <Navigate to="/login" />} 
          />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
