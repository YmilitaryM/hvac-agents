import './i18n';
import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider } from './contexts/AuthContext';

const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Equipment = lazy(() => import('./pages/Equipment'));
const PlantBuilder = lazy(() => import('./pages/PlantBuilder'));
const Environment = lazy(() => import('./pages/Environment'));
const Simulation = lazy(() => import('./pages/Simulation'));
const Strategies = lazy(() => import('./pages/Strategies'));
const Reports = lazy(() => import('./pages/Reports'));
const Alerts = lazy(() => import('./pages/Alerts'));
const ManualOverride = lazy(() => import('./pages/ManualOverride'));
const Settings = lazy(() => import('./pages/Settings'));
const Profile = lazy(() => import('./pages/Profile'));
const EdgeDevices = lazy(() => import('./pages/EdgeDevices'));
const WorkOrders = lazy(() => import('./pages/WorkOrders'));
const Maintenance = lazy(() => import('./pages/Maintenance'));
const CarbonTrading = lazy(() => import('./pages/CarbonTrading'));
const EnergyDashboard = lazy(() => import('./pages/energy/EnergyDashboard'));
const EnergyScheduling = lazy(() => import('./pages/energy/EnergyScheduling'));
const EnergyDemand = lazy(() => import('./pages/energy/EnergyDemand'));
const EnergyReports = lazy(() => import('./pages/energy/EnergyReports'));
const EnergyMV = lazy(() => import('./pages/energy/EnergyMV'));
const EnergyComparison = lazy(() => import('./pages/energy/EnergyComparison'));
const HealthDashboard = lazy(() => import('./pages/health/HealthDashboard'));
const RULPrediction = lazy(() => import('./pages/health/RULPrediction'));
const FaultDiagnosis = lazy(() => import('./pages/health/FaultDiagnosis'));
const FMEAKB = lazy(() => import('./pages/health/FMEAKB'));
const SpectrumAnalysis = lazy(() => import('./pages/health/SpectrumAnalysis'));

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Suspense fallback={
            <div className="flex items-center justify-center min-h-screen bg-slate-900">
              <div className="text-slate-400 text-lg">加载中...</div>
            </div>
          }>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              element={
                <ErrorBoundary>
                  <ProtectedRoute>
                    <Layout />
                  </ProtectedRoute>
                </ErrorBoundary>
              }
            >
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
              <Route path="/energy/dashboard" element={<EnergyDashboard />} />
              <Route path="/energy/scheduling" element={<EnergyScheduling />} />
              <Route path="/energy/demand" element={<EnergyDemand />} />
              <Route path="/energy/reports" element={<EnergyReports />} />
              <Route path="/energy/mv" element={<EnergyMV />} />
              <Route path="/energy/comparison" element={<EnergyComparison />} />
              <Route path="/health/dashboard" element={<HealthDashboard />} />
              <Route path="/health/rul" element={<RULPrediction />} />
              <Route path="/health/diagnosis" element={<FaultDiagnosis />} />
              <Route path="/health/fmea" element={<FMEAKB />} />
              <Route path="/health/spectrum" element={<SpectrumAnalysis />} />
              <Route path="*" element={
                <div className="flex flex-col items-center justify-center min-h-[60vh] text-slate-400">
                  <h2 className="text-4xl font-bold text-slate-500 mb-2">404</h2>
                  <p>Page not found</p>
                </div>
              } />
            </Route>
          </Routes>
          </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
