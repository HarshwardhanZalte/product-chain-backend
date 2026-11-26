import {
  Activity,
  Beaker,
  Boxes,
  ChevronRight,
  ClipboardList,
  Factory,
  FlaskConical,
  Grid2X2,
  Leaf,
  LogOut,
  PackageCheck,
  PackageSearch,
  QrCode,
  Settings,
  Truck,
  UserRound,
} from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth, roleHome } from '../auth/AuthProvider'
import { Button } from './UI'

interface NavItem {
  label: string
  to: string
  icon: typeof Grid2X2
}

const navigation: Record<string, NavItem[]> = {
  FARMER: [
    { label: 'Dashboard', to: '/farmer', icon: Grid2X2 },
    { label: 'My Batches', to: '/farmer/batches', icon: Boxes },
    { label: 'Batch Transfers', to: '/farmer/transfers', icon: Truck },
    { label: 'Account Profile', to: '/profile', icon: UserRound },
  ],
  COLLECTOR: [
    { label: 'Dashboard', to: '/collector', icon: Grid2X2 },
    { label: 'Incoming Transfers', to: '/collector/incoming', icon: ClipboardList },
    { label: 'Available Batches', to: '/collector/batches', icon: Boxes },
    { label: 'Factory Transfers', to: '/collector/factory-transfers', icon: Truck },
    { label: 'Account Profile', to: '/profile', icon: UserRound },
  ],
  LAB: [
    { label: 'Dashboard', to: '/lab', icon: Grid2X2 },
    { label: 'Assigned Tests', to: '/lab/requests', icon: FlaskConical },
    { label: 'Test History', to: '/lab/history', icon: Activity },
    { label: 'Account Profile', to: '/profile', icon: UserRound },
  ],
  FACTORY: [
    { label: 'Dashboard', to: '/factory', icon: Grid2X2 },
    { label: 'Incoming Batches', to: '/factory/incoming', icon: PackageSearch },
    { label: 'Input Inventory', to: '/factory/inventory', icon: Boxes },
    { label: 'Manufacturing', to: '/factory/manufacturing', icon: Factory },
    { label: 'Products & QR Codes', to: '/factory/products', icon: QrCode },
    { label: 'Account Profile', to: '/profile', icon: UserRound },
  ],
}

const roleTitles: Record<string, string> = {
  FARMER: 'Farmer Portal',
  COLLECTOR: 'Collector Portal',
  LAB: 'Quality Testing Lab',
  FACTORY: 'Factory Portal',
}

export function PortalLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  if (!user) return null
  const items = navigation[user.role] ?? []
  const shortName = user.name
    .split(/\s+/)
    .map((part) => part[0] ?? '')
    .slice(0, 2)
    .join('')
    .toUpperCase()

  const signOut = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="portal-layout">
      <aside className="sidebar">
        <NavLink className="sidebar-brand" to={roleHome(user.role)}>
          <span className="brand-mark"><Leaf size={21} /></span>
          <span>
            <strong>Product Chain</strong>
            <small>Botanical Traceability</small>
          </span>
        </NavLink>
        <div className="side-section">Workspace</div>
        <nav className="side-nav" aria-label="Main navigation">
          {items.map(({ label, to, icon: Icon }) => (
            <NavLink
              className={({ isActive }) => `side-link ${isActive ? 'active' : ''}`}
              end={to === roleHome(user.role)}
              key={to}
              to={to}
            >
              <Icon size={16} strokeWidth={1.8} />
              <span>{label}</span>
              {label === 'Incoming Transfers' && <ChevronRight size={13} style={{ marginLeft: 'auto' }} />}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <strong>Traceability workspace</strong>
            <span>Records shown here come from your connected Product Chain account.</span>
          </div>
          <Button className="button-full" onClick={signOut} variant="quiet">
            <LogOut size={15} /> Sign out
          </Button>
        </div>
      </aside>

      <main className="portal-main">
        <header className="topbar">
          <div className="topbar-user">
            <span className="brand-mark"><Leaf size={18} /></span>
            <div>
              <strong style={{ color: 'var(--forest)', fontSize: 12 }}>{roleTitles[user.role]}</strong>
              <span style={{ display: 'block', marginTop: 3, color: 'var(--muted)', fontSize: 9 }}>
                Verified supply-chain workspace
              </span>
            </div>
          </div>
          <div className="topbar-user">
            <div className="topbar-user-copy">
              <strong>{user.name}</strong>
              <span>{user.role}</span>
            </div>
            <span className="user-avatar" aria-label={`Signed in as ${user.name}`}>{shortName}</span>
          </div>
        </header>
        <Outlet />
        <nav className="mobile-nav" aria-label="Mobile navigation">
          {items.slice(0, 4).map(({ label, to, icon: Icon }) => (
            <NavLink
              className={({ isActive }) => (isActive ? 'active' : '')}
              end={to === roleHome(user.role)}
              key={to}
              to={to}
            >
              <Icon strokeWidth={1.8} />
              <span>{label.replace('Account Profile', 'Profile').replace('Incoming Transfers', 'Incoming')}</span>
            </NavLink>
          ))}
        </nav>
      </main>
    </div>
  )
}

export const ProfileIcon = Settings
export const LabIcon = Beaker
export const FactoryIcon = Factory
export const ProductIcon = PackageCheck
