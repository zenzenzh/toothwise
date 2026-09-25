import { useEffect, useMemo, useState } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  Menu, X, LayoutDashboard, Users, UserCog, ShieldCheck,
  LogOut, ChevronLeft, Activity, Bell, Search, ArrowRight,
  Moon, Sun,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import useDarkMode from '../hooks/useDarkMode';
import LogoMark from './LogoMark';
import SEO from './SEO';
import { dashboardAPI, patientsAPI } from '../api';

const MOBILE_BREAKPOINT = 900;
const COLLAPSE_KEY = 'tw_sidebar_collapsed';

function initials(name = 'Staff') {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map(x => x[0]).join('').toUpperCase();
}

export default function Layout() {
  const { dentist, logout } = useAuth();
  const { isDark, toggle: toggleTheme } = useDarkMode();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === '1');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [notificationLoading, setNotificationLoading] = useState(false);
  const [notificationRead, setNotificationRead] = useState(() => localStorage.getItem('tw_notifications_read') === '1');

  useEffect(() => { setMobileOpen(false); }, [location.pathname]);
  useEffect(() => {
    const onResize = () => { if (window.innerWidth > MOBILE_BREAKPOINT) setMobileOpen(false); };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const navItems = useMemo(() => [
    { to: '/dashboard', label: 'Overview', icon: LayoutDashboard, exact: true },
    { to: '/dashboard/patients', label: 'Patients', icon: Users },
    ...(dentist?.role === 'admin' ? [
      { to: '/dashboard/dentists', label: 'Staff', icon: UserCog },
      { to: '/dashboard/audit-log', label: 'Audit trail', icon: ShieldCheck },
    ] : []),
  ], [dentist?.role]);

  const pageLabel = navItems.find(i => location.pathname === i.to || (i.to !== '/dashboard' && location.pathname.startsWith(i.to)))?.label || 'ToothWise';
  const routeMeta = location.pathname === '/dashboard'
    ? ['Dashboard | ToothWise', 'CodiSmile staff dashboard for patients, screenings, and clinic activity.', 'Dashboard']
    : location.pathname === '/dashboard/patients'
      ? ['Patients | ToothWise', 'Manage authorized patient records and dental screening workflows.', 'Patients']
      : /^\/dashboard\/patients\/[^/]+\/screening$/.test(location.pathname)
        ? ['Dental Screening | ToothWise', 'Review and run an authorized patient dental screening workflow.', 'Patients / Screening']
        : /^\/dashboard\/patients\/[^/]+$/.test(location.pathname)
          ? ['Patient Record | ToothWise', 'View an authorized patient record and clinical history.', 'Patients / Patient Record']
          : /^\/dashboard\/screenings\/[^/]+$/.test(location.pathname)
            ? ['Screening Result | ToothWise', 'Review an authorized ToothWise dental screening result.', 'Screening Result']
            : location.pathname === '/dashboard/dentists'
              ? ['Staff | ToothWise', 'Manage authorized CodiSmile clinic staff.', 'Staff']
              : location.pathname === '/dashboard/audit-log'
                ? ['Audit Trail | ToothWise', 'Review authorized ToothWise audit activity.', 'Audit Trail']
                : ['ToothWise Clinic Workspace', 'Secure CodiSmile clinic workspace.', pageLabel];
  const pageMeta = routeMeta;


  useEffect(() => {
    if (!searchOpen) return;
    const q = searchTerm.trim();
    if (!q) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(() => {
      setSearchLoading(true);
      patientsAPI.list(q)
        .then(r => setSearchResults(Array.isArray(r.data) ? r.data.slice(0, 8) : []))
        .catch(() => setSearchResults([]))
        .finally(() => setSearchLoading(false));
    }, 220);
    return () => clearTimeout(timer);
  }, [searchTerm, searchOpen]);

  useEffect(() => {
    if (!searchOpen && !notificationOpen) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') closePanels();
    };
    const onPointerDown = (event) => {
      if (!event.target.closest('.dashboard-popover') && !event.target.closest('.dashboard-icon-button')) {
        closePanels();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('pointerdown', onPointerDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('pointerdown', onPointerDown);
    };
  }, [searchOpen, notificationOpen]);

  useEffect(() => {
    if (!notificationOpen) return;
    setNotificationLoading(true);
    dashboardAPI.stats().catch(() => ({ data: null })).then((statsRes) => {
      const items = [];
      const stats = statsRes.data;
      if (stats?.high_risk_cases > 0) {
        items.push({
          id: 'high-risk',
          tone: 'danger',
          title: `${stats.high_risk_cases} high-risk screening${stats.high_risk_cases !== 1 ? 's' : ''}`,
          body: 'Review the affected screening records.',
          action: () => navigate('/dashboard/patients'),
        });
      }
      if (stats?.todays_screenings > 0) {
        items.push({
          id: 'today-screenings',
          tone: 'info',
          title: `${stats.todays_screenings} screening${stats.todays_screenings !== 1 ? 's' : ''} today`,
          body: 'Open Patients to review today’s activity.',
          action: () => navigate('/dashboard/patients'),
        });
      }
      if (!items.length) {
        items.push({
          id: 'all-clear',
          tone: 'neutral',
          title: 'All caught up',
          body: 'No new clinic alerts require your attention.',
          action: () => setNotificationOpen(false),
        });
      }
      setNotifications(items);
      setNotificationRead(false);
      localStorage.removeItem('tw_notifications_read');
    }).finally(() => setNotificationLoading(false));
  }, [notificationOpen, navigate]);

  function openSearch() {
    setNotificationOpen(false);
    setSearchOpen(v => !v);
  }

  function openNotifications() {
    setSearchOpen(false);
    setNotificationOpen(v => {
      const next = !v;
      if (next) {
        setNotificationRead(true);
        localStorage.setItem('tw_notifications_read', '1');
      }
      return next;
    });
  }

  function closePanels() {
    setSearchOpen(false);
    setNotificationOpen(false);
  }

  function toggleSidebar() {
    if (window.innerWidth <= MOBILE_BREAKPOINT) setMobileOpen(v => !v);
    else setCollapsed(v => { localStorage.setItem(COLLAPSE_KEY, v ? '0' : '1'); return !v; });
  }

  function handleLogout() {
    logout();
    window.location.replace('/login');
  }

  return (
    <div style={{ ...styles.shell, '--sidebar-w': collapsed ? '84px' : '260px' }}>
      <SEO title={pageMeta[0]} description={pageMeta[1]} noIndex />
      {mobileOpen && <div className="tw-backdrop" onClick={() => setMobileOpen(false)} aria-hidden="true" />}

      <aside
        className={`tw-sidebar${mobileOpen ? ' mobile-open' : ''}${collapsed ? ' collapsed' : ''}`}
        style={styles.sidebar}
        aria-label="Primary navigation"
      >
        <div>
          <div style={{ ...styles.brandRow, justifyContent: collapsed ? 'center' : 'flex-start' }}>
            <div style={styles.logo}><LogoMark size={38} alt="CodiSmile Dental Clinic" /></div>
            {!collapsed && <div>
              <div style={styles.brandName}>TOOTHWISE</div>
              <div style={styles.brandSub}>CODISMILE CLINIC</div>
            </div>}
          </div>

          {!collapsed && <div style={styles.clinicPill}><span style={styles.liveDot} /> Clinic workspace</div>}

          <nav style={{ ...styles.nav, marginTop: collapsed ? 22 : 18 }}>
            {navItems.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.exact}
                title={collapsed ? item.label : undefined}
                className="nav-link"
                style={({ isActive }) => ({
                  ...styles.navLink,
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  color: isActive ? '#FFFFFF' : '#C4B0BA',
                  background: isActive ? 'rgba(196,132,126,.18)' : 'transparent',
                  borderColor: isActive ? '#BA7976' : 'transparent',
                })}
              >
                <item.icon size={19} strokeWidth={2} />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            ))}
          </nav>
        </div>

        <div style={styles.sidebarBottom}>
          <button className="nav-link" onClick={toggleSidebar} style={{ ...styles.collapseButton, justifyContent: collapsed ? 'center' : 'flex-start' }}>
            <ChevronLeft size={18} style={{ transform: collapsed ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }} />
            {!collapsed && <span>Collapse menu</span>}
          </button>
          <div style={styles.userCard}>
            <div style={styles.avatar}>{initials(dentist?.full_name)}</div>
            {!collapsed && <div style={{ minWidth: 0 }}>
              <div style={styles.userName}>{dentist?.full_name || 'Clinic staff'}</div>
              <div style={styles.userRole}>{dentist?.role || 'staff'}</div>
            </div>}
          </div>
          <button onClick={handleLogout} style={{ ...styles.logout, justifyContent: collapsed ? 'center' : 'flex-start' }}>
            <LogOut size={17} />
            {!collapsed && <span>Sign out</span>}
          </button>
        </div>
      </aside>

      <main className={`tw-main${collapsed ? ' collapsed' : ''}`} style={styles.main}>
        <header className="tw-topbar" style={styles.topbar}>
          <div className="tw-top-left" style={styles.topLeft}>
            <button className="tw-hamburger" onClick={toggleSidebar} aria-label="Toggle navigation" aria-expanded={mobileOpen}>
              {mobileOpen ? <X size={19} /> : <Menu size={19} />}
            </button>
            <div className="tw-top-heading">
              <h1 className="tw-page-title" style={styles.pageTitle}>{pageLabel}</h1>
            </div>
          </div>
          <div className="tw-top-right" style={{ ...styles.topRight, position: 'relative' }}>
            <button className="dashboard-icon-button tw-icon-button" style={styles.iconButton} title="Notifications" aria-label="Notifications"
              onClick={openNotifications}>
              <Bell size={17} />
              {!notificationRead && <span className="dashboard-notification-dot" />}
            </button>
            <button className="dashboard-icon-button tw-icon-button" style={styles.iconButton} title="Search patients" aria-label="Search patients"
              onClick={openSearch}>
              <Search size={17} />
            </button>
            <button
              className="dashboard-icon-button tw-icon-button"
              style={styles.iconButton}
              onClick={toggleTheme}
              title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDark ? <Sun size={17} /> : <Moon size={17} />}
            </button>

            {searchOpen && (
              <div className="dashboard-popover search-popover">
                <div className="popover-heading"><div><strong>Search patients</strong><span>Find an authorized patient record</span></div><button onClick={closePanels} aria-label="Close search">×</button></div>
                <div className="global-search-box">
                  <Search size={17} />
                  <input autoFocus value={searchTerm} onChange={e => setSearchTerm(e.target.value)} placeholder="Name, patient ID, email..." />
                  {searchTerm && <button onClick={() => setSearchTerm('')} aria-label="Clear search">×</button>}
                </div>
                <div className="popover-results">
                  {searchLoading ? <div className="popover-empty">Searching patients…</div> :
                    searchTerm.trim() && !searchResults.length ? <div className="popover-empty">No matching patient records.</div> :
                    !searchTerm.trim() ? <div className="popover-empty">Start typing to search the patient directory.</div> :
                    searchResults.map(p => (
                      <button key={p.id} className="popover-result" onClick={() => { closePanels(); navigate(`/dashboard/patients/${p.id}`); }}>
                        <span className="result-avatar">{(p.full_name || '?').charAt(0).toUpperCase()}</span>
                        <span><strong>{p.full_name}</strong><small>Patient #{p.id} · {p.contact_number || p.email || 'No contact on file'}</small></span>
                        <ArrowRight size={15} />
                      </button>
                    ))
                  }
                </div>
                <button className="popover-footer-action" onClick={() => { closePanels(); navigate('/dashboard/patients'); }}>Open patient directory <ArrowRight size={14} /></button>
              </div>
            )}

            {notificationOpen && (
              <div className="dashboard-popover notification-popover">
                <div className="popover-heading"><div><strong>Clinic notifications</strong><span>Actionable activity from your workspace</span></div><button onClick={closePanels} aria-label="Close notifications">×</button></div>
                <div className="popover-results">
                  {notificationLoading ? <div className="popover-empty">Checking clinic activity…</div> :
                    notifications.map(n => (
                      <button key={n.id} className={`popover-result notification-result ${n.tone}`} onClick={n.action}>
                        <span className="notification-icon"><Bell size={15} /></span>
                        <span><strong>{n.title}</strong><small>{n.body}</small></span>
                        <ArrowRight size={15} />
                      </button>
                    ))
                  }
                </div>
                <button className="popover-footer-action" onClick={() => { closePanels(); navigate('/dashboard/patients'); }}>Open patient directory <ArrowRight size={14} /></button>
              </div>
            )}
          </div>
        </header>

        <div className="tw-content" style={styles.content}>
          <nav className="app-breadcrumbs" aria-label="Breadcrumb">
            <span>ToothWise</span><span>/</span><strong>{routeMeta[2]}</strong>
          </nav>
          <div key={location.pathname} className="page-enter">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}

const styles = {
  shell: { minHeight: '100vh', background: 'var(--tw-bg)', color: 'var(--tw-text)' },
  sidebar: {
    position: 'fixed', inset: '0 auto 0 0', zIndex: 200, display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    background: '#352126', color: '#fff', padding: '20px 12px', overflow: 'hidden',
    boxShadow: '12px 0 35px rgba(58,36,48,.08)', width: 'var(--sidebar-w, 260px)',
  },
  brandRow: { display: 'flex', alignItems: 'center', gap: 12, minHeight: 52, padding: '2px 10px' },
  logo: { width: 44, height: 44, borderRadius: 14, display: 'grid', placeItems: 'center', background: '#FFFFFF', boxShadow: 'none', flexShrink: 0 },
  brandName: { color: '#fff', fontWeight: 900, letterSpacing: '.12em', fontSize: 14 },
  brandSub: { color: '#C78C8A', fontSize: 9, marginTop: 3, letterSpacing: '.1em', fontWeight: 800 },
  clinicPill: { margin: '17px 8px 0', padding: '8px 10px', borderRadius: 10, background: 'rgba(255,255,255,.05)', color: '#C4B0BA', fontSize: 11, display: 'flex', alignItems: 'center', gap: 7 },
  liveDot: { width: 7, height: 7, borderRadius: '50%', background: '#2CCB91', boxShadow: '0 0 0 4px rgba(44,203,145,.12)' },
  nav: { display: 'flex', flexDirection: 'column', gap: 6, padding: '0 4px' },
  navLink: { display: 'flex', alignItems: 'center', gap: 12, borderRadius: 12, padding: '12px 13px', textDecoration: 'none', fontSize: 13, fontWeight: 700, transition: 'background .16s, color .16s' },
  sidebarBottom: { display: 'flex', flexDirection: 'column', gap: 9 },
  collapseButton: { width: '100%', border: 0, background: 'transparent', color: '#C4B0BA', padding: '10px 13px', borderRadius: 10, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12, fontSize: 11, fontWeight: 700 },
  userCard: { display: 'flex', alignItems: 'center', gap: 10, padding: '12px 8px', borderTop: '1px solid rgba(255,255,255,.08)' },
  avatar: { width: 38, height: 38, borderRadius: 12, background: 'rgba(196,132,126,.18)', color: '#C4B0BA', display: 'grid', placeItems: 'center', fontSize: 13, fontWeight: 900, flexShrink: 0 },
  userName: { color: '#FBF6F4', fontWeight: 800, fontSize: 12, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 160 },
  userRole: { color: '#C4B0BA', textTransform: 'capitalize', fontSize: 10, marginTop: 2 },
  logout: { border: '1px solid rgba(255,255,255,.1)', background: 'rgba(255,255,255,.04)', color: '#AFC3C9', borderRadius: 11, padding: '10px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 11, fontSize: 12, fontWeight: 700 },
  main: { minHeight: '100vh', display: 'flex', flexDirection: 'column', marginLeft: 'var(--sidebar-w, 260px)' },
  topbar: { height: 78, background: 'color-mix(in srgb, var(--tw-surface) 92%, transparent)', backdropFilter: 'blur(14px)', borderBottom: '1px solid var(--tw-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 30px', position: 'sticky', top: 0, zIndex: 100 },
  topLeft: { display: 'flex', alignItems: 'center', gap: 14 },
  eyebrow: { color: 'var(--tw-muted)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '.12em', fontWeight: 800 },
  pageTitle: { margin: '3px 0 0', color: 'var(--tw-text)', fontSize: 21, lineHeight: 1.1, letterSpacing: '-.02em' },
  topRight: { display: 'flex', alignItems: 'center', gap: 8 },
  system: { display: 'flex', alignItems: 'center', gap: 7, marginRight: 4, padding: '9px 11px', borderRadius: 11, background: '#0D2818', color: '#4ADE80', fontSize: 11, fontWeight: 800 },
  iconButton: { width: 38, height: 38, border: '1px solid var(--tw-border)', borderRadius: 11, background: 'var(--tw-surface)', color: 'var(--tw-muted)', display: 'grid', placeItems: 'center', cursor: 'pointer' },
  content: { flex: 1, padding: '28px 30px 36px', minWidth: 0 },
};
