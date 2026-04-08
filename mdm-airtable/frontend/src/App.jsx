import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import TableView from './pages/TableView';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/table/:tableId" element={<TableView />} />
      </Routes>
    </Router>
  );
}

export default App;
