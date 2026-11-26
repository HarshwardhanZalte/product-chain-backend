import { lazy, Suspense } from 'react'
import { Navigate, Outlet, Route, Routes, useParams } from 'react-router-dom'
import { useAuth, roleHome } from './auth/AuthProvider'
import { PortalLayout } from './components/PortalLayout'
import { LoadingState } from './components/UI'
import type { Role } from './api/types'

const LoginPage = lazy(() => import('./pages/AuthPages').then((pages) => ({ default: pages.LoginPage })))
const RegisterPage = lazy(() => import('./pages/AuthPages').then((pages) => ({ default: pages.RegisterPage })))
const VerifyOtpPage = lazy(() => import('./pages/AuthPages').then((pages) => ({ default: pages.VerifyOtpPage })))
const ForgotPasswordPage = lazy(() => import('./pages/AuthPages').then((pages) => ({ default: pages.ForgotPasswordPage })))
const OnboardingPage = lazy(() => import('./pages/AuthPages').then((pages) => ({ default: pages.OnboardingPage })))
const PendingApprovalPage = lazy(() => import('./pages/AuthPages').then((pages) => ({ default: pages.PendingApprovalPage })))
const FarmerDashboardPage = lazy(() => import('./pages/FarmerPages').then((pages) => ({ default: pages.FarmerDashboardPage })))
const FarmerBatchesPage = lazy(() => import('./pages/FarmerPages').then((pages) => ({ default: pages.FarmerBatchesPage })))
const RegisterBatchPage = lazy(() => import('./pages/FarmerPages').then((pages) => ({ default: pages.RegisterBatchPage })))
const FarmerBatchDetailPage = lazy(() => import('./pages/FarmerPages').then((pages) => ({ default: pages.FarmerBatchDetailPage })))
const FarmerTransfersPage = lazy(() => import('./pages/FarmerPages').then((pages) => ({ default: pages.FarmerTransfersPage })))
const CollectorDashboardPage = lazy(() => import('./pages/CollectorPages').then((pages) => ({ default: pages.CollectorDashboardPage })))
const CollectorIncomingPage = lazy(() => import('./pages/CollectorPages').then((pages) => ({ default: pages.CollectorIncomingPage })))
const CollectorIncomingDetailPage = lazy(() => import('./pages/CollectorPages').then((pages) => ({ default: pages.CollectorIncomingDetailPage })))
const CollectorBatchesPage = lazy(() => import('./pages/CollectorPages').then((pages) => ({ default: pages.CollectorBatchesPage })))
const CollectorFactoryTransferPage = lazy(() => import('./pages/CollectorPages').then((pages) => ({ default: pages.CollectorFactoryTransferPage })))
const LabDashboardPage = lazy(() => import('./pages/LabPages').then((pages) => ({ default: pages.LabDashboardPage })))
const LabRequestsPage = lazy(() => import('./pages/LabPages').then((pages) => ({ default: pages.LabRequestsPage })))
const LabTestDetailPage = lazy(() => import('./pages/LabPages').then((pages) => ({ default: pages.LabTestDetailPage })))
const FactoryDashboardPage = lazy(() => import('./pages/FactoryPages').then((pages) => ({ default: pages.FactoryDashboardPage })))
const FactoryIncomingPage = lazy(() => import('./pages/FactoryPages').then((pages) => ({ default: pages.FactoryIncomingPage })))
const FactoryInventoryPage = lazy(() => import('./pages/FactoryPages').then((pages) => ({ default: pages.FactoryInventoryPage })))
const FactoryManufacturingPage = lazy(() => import('./pages/FactoryPages').then((pages) => ({ default: pages.FactoryManufacturingPage })))
const FactoryProductsPage = lazy(() => import('./pages/FactoryPages').then((pages) => ({ default: pages.FactoryProductsPage })))
const ProfilePage = lazy(() => import('./pages/ProfilePage').then((pages) => ({ default: pages.ProfilePage })))
const AdminEntryPage = lazy(() => import('./pages/ProfilePage').then((pages) => ({ default: pages.AdminEntryPage })))
const QrScannerPage = lazy(() => import('./pages/PublicPages').then((pages) => ({ default: pages.QrScannerPage })))
const ProductVerificationPage = lazy(() => import('./pages/PublicPages').then((pages) => ({ default: pages.ProductVerificationPage })))

function HomeRedirect() {
  const { user, ready } = useAuth()
  if (!ready) return <LoadingState />
  return <Navigate replace to={user ? roleHome(user.role) : '/login'} />
}

function RequireAuth() {
  const { user, ready } = useAuth()
  if (!ready) return <LoadingState />
  return user ? <Outlet /> : <Navigate replace to="/login" />
}

function RequireGuest() {
  const { user, ready } = useAuth()
  if (!ready) return <LoadingState />
  return user ? <Navigate replace to={roleHome(user.role)} /> : <Outlet />
}

function RequireRole({ roles }: { roles: Role[] }) {
  const { user } = useAuth()
  return user && roles.includes(user.role) ? <Outlet /> : <Navigate replace to={user ? roleHome(user.role) : '/login'} />
}

function VerificationRoute() {
  const { reference = '' } = useParams()
  return <ProductVerificationPage reference={reference} />
}

export default function App() {
  return (
    <div className="app-shell">
      <Suspense fallback={<LoadingState />}>
        <Routes>
        <Route element={<RequireGuest />}>
          <Route element={<HomeRedirect />} path="/" />
          <Route element={<LoginPage />} path="/login" />
          <Route element={<RegisterPage />} path="/register" />
          <Route element={<VerifyOtpPage />} path="/verify" />
          <Route element={<ForgotPasswordPage />} path="/forgot-password" />
        </Route>
        <Route element={<RequireAuth />}>
          <Route element={<OnboardingPage />} path="/onboarding" />
          <Route element={<PendingApprovalPage />} path="/pending" />
          <Route element={<ProfilePage />} path="/profile" />
          <Route element={<RequireRole roles={['ADMIN']} />}>
            <Route element={<AdminEntryPage />} path="/admin" />
          </Route>
          <Route element={<RequireRole roles={['FARMER']} />}>
            <Route element={<PortalLayout />} path="/farmer">
              <Route element={<FarmerDashboardPage />} index />
              <Route element={<FarmerBatchesPage />} path="batches" />
              <Route element={<RegisterBatchPage />} path="batches/new" />
              <Route element={<FarmerBatchDetailPage />} path="batches/:batchId" />
              <Route element={<FarmerTransfersPage />} path="transfers" />
            </Route>
          </Route>
          <Route element={<RequireRole roles={['COLLECTOR']} />}>
            <Route element={<PortalLayout />} path="/collector">
              <Route element={<CollectorDashboardPage />} index />
              <Route element={<CollectorIncomingPage />} path="incoming" />
              <Route element={<CollectorIncomingDetailPage />} path="incoming/:eventId" />
              <Route element={<CollectorBatchesPage />} path="batches" />
              <Route element={<CollectorFactoryTransferPage />} path="factory-transfers" />
            </Route>
          </Route>
          <Route element={<RequireRole roles={['LAB']} />}>
            <Route element={<PortalLayout />} path="/lab">
              <Route element={<LabDashboardPage />} index />
              <Route element={<LabRequestsPage />} path="requests" />
              <Route element={<LabRequestsPage history />} path="history" />
              <Route element={<LabTestDetailPage />} path="tests/:testId" />
            </Route>
          </Route>
          <Route element={<RequireRole roles={['FACTORY']} />}>
            <Route element={<PortalLayout />} path="/factory">
              <Route element={<FactoryDashboardPage />} index />
              <Route element={<FactoryIncomingPage />} path="incoming" />
              <Route element={<FactoryInventoryPage />} path="inventory" />
              <Route element={<FactoryManufacturingPage />} path="manufacturing" />
              <Route element={<FactoryProductsPage />} path="products" />
            </Route>
          </Route>
        </Route>
        <Route element={<QrScannerPage />} path="/scan" />
        <Route element={<VerificationRoute />} path="/verify/:reference" />
        <Route element={<Navigate replace to="/" />} path="*" />
        </Routes>
      </Suspense>
    </div>
  )
}
