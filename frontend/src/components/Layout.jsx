import { useEffect, useMemo, useRef, useState } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  Menu, X, LayoutDashboard, Users, UserCog, ShieldCheck,
  LogOut, ChevronLeft, Bell, Search, ArrowRight,
  Moon, Sun, KeyRound,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { isDentist, ROLE_LABELS } from '../utils/permissions';
import useDarkMode from '../hooks/useDarkMode';
import LogoMark from './LogoMark';
import SEO from './SEO';
import { authAPI, dashboardAPI, patientsAPI } from '../api';
import ChangePasswordModal from './ChangePasswordModal';
import { MOBILE_BREAKPOINT } from '../tokens';

const COLLAPSE_KEY = 'tw_sidebar_collapsed';

function initials(name = 'Staff') {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map(x => x[0]).join('').toUpperCase();
}

// One entry per staff route: document title, meta description and the
// breadcrumb trail shown in the top bar (the page itself owns the <h1>).
const WORKSPACE = { label: 'CodiSmile Clinic', to: '/dashboard' };
const PATIENTS = { label: 'Patients', to: '/dashboard/patients' };
const ROUTES = [
  { match: /^\/dashboard\/?$/, title: 'Dashboard | ToothWise', description: 'CodiSmile staff dashboard for patients, screenings, and clinic activity.', crumbs: [{ label: 'Overview' }] },
  { match: /^\/dashboard\/patients\/?$/, title: 'Patients | ToothWise', description: 'Manage authorized patient records and dental screening workflows.', crumbs: [{ label: 'Patients' }] },
  { match: /^\/dashboard\/patients\/[^/]+\/screening$/, title: 'Dental Screening | ToothWise', description: 'Run an AI-assisted dental screening for an authorized patient.', crumbs: [PATIENTS, { label: 'New screening' }] },
  { match: /^\/dashboard\/patients\/[^/]+$/, title: 'Patient Record | ToothWise', description: 'View an authorized patient record and clinical history.', crumbs: [PATIENTS, { label: 'Patient record' }] },
  { match: /^\/dashboard\/screenings\/[^/]+$/, title: 'Screening Result | ToothWise', description: 'Review an authorized ToothWise dental screening result.', crumbs: [PATIENTS, { label: 'Screening result' }] },
  { match: /^\/dashboard\/dentists\/?$/, title: 'Staff | ToothWise', description: 'Manage authorized CodiSmile clinic staff.', crumbs: [{ label: 'Staff' }] },
  { match: /^\/dashboard\/audit-log\/?$/, title: 'Audit Trail | ToothWise', description: 'Review authorized ToothWise audit activity.', crumbs: [{ label: 'Audit trail' }] },
];
const FALLBACK_ROUTE = { title: 'ToothWise Clinic Workspace', description: 'Secure CodiSmile clinic workspace.', crumbs: [{ label: 'ToothWise' }] };

export default function Layout() {
  const { dentist, logout } = useAuth();
  const { isDark, toggle: toggleTheme } = useDarkMode();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === '1');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
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
  // The open mobile drawer is a full-screen overlay, so it must never render in the
  // collapsed rail state (mobileOpen can only be true while below MOBILE_BREAKPOINT).
  const railCollapsed = collapsed && !mobileOpen;
  const sidebarRef = useRef(null);
  const hamburgerRef = useRef(null);
  useEffect(() => {
    if (!mobileOpen) return undefined;
    // Drawer open: move focus into it, keep Tab inside, Esc closes and
    // returns focus to the menu button.
    const sidebar = sidebarRef.current;
    sidebar?.querySelector('a, button')?.focus();
    const onKey = e => {
      if (e.key === 'Escape') { setMobileOpen(false); return; }
      if (e.key !== 'Tab' || !sidebar) return;
      const items = [...sidebar.querySelectorAll('a, button')];
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const hamburger = hamburgerRef.current;
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
      if (hamburger && hamburger.offsetParent !== null) hamburger.focus();
    };
  }, [mobileOpen]);

  const navItems = useMemo(() => [
    { to: '/dashboard', label: 'Overview', icon: LayoutDashboard, exact: true },
    { to: '/dashboard/patients', label: 'Patients', icon: Users },
    ...(isDentist(dentist?.role) ? [
      { to: '/dashboard/dentists', label: 'Staff', icon: UserCog },
      { to: '/dashboard/audit-log', label: 'Audit trail', icon: ShieldCheck },
    ] : []),
  ], [dentist?.role]);

  const route = ROUTES.find(r => r.match.test(location.pathname)) || FALLBACK_ROUTE;
  const trail = [WORKSPACE, ...route.crumbs.slice(0, -1)];


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
    <div className="tw-shell" style={{ '--sidebar-w': railCollapsed ? '84px' : '260px' }}>
      <SEO title={route.title} description={route.description} noIndex />
      {mobileOpen && <div className="tw-backdrop" onClick={() => setMobileOpen(false)} aria-hidden="true" />}

      <aside
        ref={sidebarRef}
        className={`tw-sidebar${mobileOpen ? ' mobile-open' : ''}${railCollapsed ? ' collapsed' : ''}`}
        aria-label="Primary navigation"
      >
        <div>
          <div className="tw-sb-brand">
            <div className="tw-sb-logo"><LogoMark size={38} alt="CodiSmile Dental Clinic" /></div>
            {!railCollapsed && <div>
              <div className="tw-sb-brand-name">ToothWise</div>
              <div className="tw-sb-brand-sub">CodiSmile Clinic</div>
            </div>}
          </div>

          <nav className="tw-sb-nav">
            {navItems.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.exact}
                title={railCollapsed ? item.label : undefined}
                className="nav-link tw-sb-link"
              >
                <item.icon size={19} strokeWidth={2} />
                {!railCollapsed && <span>{item.label}</span>}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="tw-sb-bottom">
          <button className="nav-link tw-sb-collapse" onClick={toggleSidebar}>
            <ChevronLeft size={18} className="tw-sb-collapse-icon" />
            {mobileOpen ? <span>Close menu</span> : !railCollapsed && <span>Collapse menu</span>}
          </button>
          <div className="tw-sb-user">
            <div className="tw-sb-avatar">{initials(dentist?.full_name)}</div>
            {!railCollapsed && <div className="tw-sb-user-text">
              <div className="tw-sb-user-name">{dentist?.full_name || 'Clinic staff'}</div>
              <div className="tw-sb-user-role">{ROLE_LABELS[dentist?.role] || dentist?.role || 'Staff'}</div>
            </div>}
          </div>
          <button className="tw-sb-logout" onClick={() => setPasswordOpen(true)} title={railCollapsed ? 'Change password' : undefined} aria-label={railCollapsed ? 'Change password' : undefined}>
            <KeyRound size={17} />
            {!railCollapsed && <span>Change password</span>}
          </button>
          <button className="tw-sb-logout" onClick={handleLogout}>
            <LogOut size={17} />
            {!railCollapsed && <span>Sign out</span>}
          </button>
        </div>
      </aside>

      <main className={`tw-main${railCollapsed ? ' collapsed' : ''}`}>
        <header className="tw-topbar">
          <div className="tw-top-left">
            <button ref={hamburgerRef} className="tw-hamburger" onClick={toggleSidebar} aria-label="Toggle navigation" aria-expanded={mobileOpen}>
              {mobileOpen ? <X size={19} /> : <Menu size={19} />}
            </button>
            {/* The trail *to* this page; the page's own <h1> names it. */}
            <nav className="tw-top-heading tw-crumbs" aria-label="Breadcrumb">
              <ol>
                {trail.map((c, i) => (
                  <li key={c.label} className={i === trail.length - 1 ? 'is-end' : undefined}>
                    {c.to && location.pathname !== c.to
                      ? <NavLink to={c.to} end>{i === trail.length - 1 && trail.length > 1 && <ChevronLeft size={15} className="tw-crumbs-back" aria-hidden="true" />}{c.label}</NavLink>
                      : <span>{c.label}</span>}
                  </li>
                ))}
              </ol>
            </nav>
          </div>
          <div className="tw-top-right">
            <button className="dashboard-icon-button tw-icon-button" title="Notifications" aria-label="Notifications"
              onClick={openNotifications}>
              <Bell size={17} />
              {!notificationRead && <span className="dashboard-notification-dot" />}
            </button>
            <button className="dashboard-icon-button tw-icon-button" title="Search patients" aria-label="Search patients"
              onClick={openSearch}>
              <Search size={17} />
            </button>
            <button
              className="dashboard-icon-button tw-icon-button"
             
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

        <div className="tw-content">
          <div key={location.pathname} className="page-enter">
            <Outlet />
          </div>
        </div>
      </main>
      <ChangePasswordModal isOpen={passwordOpen} onClose={() => setPasswordOpen(false)} changePassword={authAPI.changePassword} />
    </div>
  );
}
