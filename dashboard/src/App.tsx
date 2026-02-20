import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Calls from './pages/Calls';
import Patients from './pages/Patients';
import Alerts from './pages/Alerts';

function App() {
  const [authed, setAuthed] = useState<boolean>(
    () => sessionStorage.getItem('matrai_auth') === 'true'
  );

  const handleLogin = () => setAuthed(true);
  const handleLogout = () => {
    sessionStorage.removeItem('matrai_auth');
    setAuthed(false);
  };

  if (!authed) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout onLogout={handleLogout} />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/calls" element={<Calls />} />
          <Route path="/patients" element={<Patients />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
