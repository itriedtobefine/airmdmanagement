import { Link } from 'react-router-dom';

export default function Dashboard() {
  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-800">MDM System</h1>
            </div>
            <div className="flex items-center space-x-4">
              <Link to="/admin/schemas" className="text-gray-600 hover:text-gray-900">
                Schema Builder
              </Link>
              <button onClick={handleLogout} className="text-red-500 hover:text-red-700">
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <h3 className="text-lg font-medium text-gray-900">Entities</h3>
                <p className="mt-1 text-sm text-gray-500">View and manage data entities</p>
              </div>
            </div>
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <h3 className="text-lg font-medium text-gray-900">Schema Builder</h3>
                <p className="mt-1 text-sm text-gray-500">Create and manage entity schemas</p>
                <Link to="/admin/schemas" className="mt-3 inline-block text-blue-500 hover:text-blue-700">
                  Go to Schema Builder →
                </Link>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
