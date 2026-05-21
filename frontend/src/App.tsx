import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Equipment from './pages/Equipment';
import PlantBuilder from './pages/PlantBuilder';
import Environment from './pages/Environment';
import Simulation from './pages/Simulation';
import Strategies from './pages/Strategies';
import Reports from './pages/Reports';
import Alerts from './pages/Alerts';
import ManualOverride from './pages/ManualOverride';
import Settings from './pages/Settings';
import Profile from './pages/Profile';
import EdgeDevices from './pages/EdgeDevices';
import WorkOrders from './pages/WorkOrders';
import Maintenance from './pages/Maintenance';
import CarbonTrading from './pages/CarbonTrading';

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/equipment" element={<Equipment />} />
            <Route path="/plant" element={<PlantBuilder />} />
            <Route path="/plant/:id" element={<PlantBuilder />} />
            <Route path="/environment" element={<Environment />} />
            <Route path="/simulation" element={<Simulation />} />
            <Route path="/strategies" element={<Strategies />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/override" element={<ManualOverride />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/edges" element={<EdgeDevices />} />
            <Route path="/workorders" element={<WorkOrders />} />
            <Route path="/maintenance" element={<Maintenance />} />
            <Route path="/carbon" element={<CarbonTrading />} />
            <Route path="*" element={
              <div className="flex flex-col items-center justify-center min-h-[60vh] text-slate-400">
                <h2 className="text-4xl font-bold text-slate-500 mb-2">404</h2>
                <p>Page not found</p>
              </div>
            } />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
