import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight, ArrowUpRight, Check, ChevronDown, ChevronLeft, ChevronRight, Clock3, MapPin, MessageCircle,
  Navigation, Phone, ScanSearch, Stethoscope, TrainFront, UsersRound,
} from 'lucide-react';
import SEO from '../components/SEO';
import ChatWidget from '../components/ChatWidget';
import Reveal from '../components/Reveal';

const CLINIC = {
  name: 'CodiSmile Dental Clinic',
  phone: '+63 956 196 5325',
  address: 'NW Phase LRT Central Terminal Arroceros St., Brgy. 659-A, Ermita, Manila City',
  mapQuery: 'CodiSmile Dental Clinic, NW Phase LRT Central Terminal Arroceros St., Ermita, Manila City',
};

// Service photos: Unsplash (free commercial licence), see
// public/codismile/services-stock/CREDITS.txt.
const SERVICES = [
  { name: 'Oral Prophylaxis', local: 'Cleaning', photo: 'cleaning', description: 'Professional cleaning that removes plaque, tartar, and surface stains to help keep gums and teeth healthy.' },
  { name: 'Tooth Restoration', local: 'Pasta', photo: 'restoration', description: 'Repairs teeth affected by cavities or damage using a filling that matches your tooth colour.' },
  { name: 'Tooth Extraction', local: 'Bunot', photo: 'extraction', description: 'Removes a tooth that cannot be safely restored or needs to be taken out for dental treatment.' },
  { name: 'Dentures', local: 'Pustiso', photo: 'dentures', description: 'Removable replacement teeth that help restore chewing, speaking, and the appearance of your smile.' },
  { name: 'Fixed Bridge and Crowns', photo: 'crowns', description: 'Restores missing or damaged teeth with fixed restorations designed to look and work naturally.' },
  { name: 'Veneers', photo: 'veneers', description: 'Thin coverings placed on the front of teeth to improve their shape, colour, and overall appearance.' },
  { name: 'Root Canal', photo: 'root-canal', description: 'Treats infection or inflammation inside a tooth so the natural tooth can be kept.' },
  { name: 'Orthodontics', local: 'Braces and retainers', photo: 'braces', description: 'Guides teeth into a healthier alignment and helps keep the result after treatment.' },
  { name: 'Oral Surgery', photo: 'surgery', description: 'Surgical dental care for conditions that need treatment beyond routine procedures.' },
  { name: 'Teeth Whitening', photo: 'whitening', description: 'Brightens natural teeth by reducing certain stains and discolouration.' },
];

const FAQS = [
  ['What is ToothWise?', 'ToothWise is CodiSmile’s digital workspace for patient access, AI screening of dental images, clinical workflows, and prevention guidance.'],
  ['Does the AI replace a dentist?', 'No. ToothWise is an assistive screening system. A qualified dental professional should review every AI finding and make clinical decisions.'],
  ['Can the chatbot see my patient record?', 'No. The public AI assistant is intentionally separated from individual patient records and screening results. Use the secure Patient Portal for information about your own account.'],
  ['How do I book a visit?', 'Call CodiSmile Dental Clinic directly to schedule a visit. The Patient Portal covers account access and screening history, not booking.'],
  ['What are the clinic hours?', 'CodiSmile is open Monday to Saturday, 9:00 AM to 5:00 PM, and Sunday, 9:00 AM to 2:00 PM.'],
];

const FACTS = [
  { value: '7 days', text: 'a week, Sundays included' },
  { value: '10', text: 'treatments under one roof' },
  { value: 'LRT', text: 'beside Central Terminal' },
  { value: '24/7', text: 'online access to your results' },
];

const BENEFITS = [
  { icon: UsersRound, title: 'Your own secure portal', text: 'Sign in to see your screenings and your dentist’s advice. No paperwork, no calling to ask.' },
  { icon: ScanSearch, title: 'AI that spots issues early', text: 'Dental images are screened by AI so possible problems are flagged for your dentist sooner.' },
  { icon: Stethoscope, title: 'A dentist makes every call', text: 'AI assists; a qualified dentist reviews every finding and decides your treatment.' },
];

const STEPS = [
  { title: 'Visit the clinic', text: 'Call to book, then come in for your checkup beside LRT Central.' },
  { title: 'Get screened', text: 'ToothWise’s AI screens your dental images.' },
  { title: 'Follow your plan', text: 'Your dentist’s findings and prevention tips wait for you in the portal.' },
];

// Clinic hours in Manila time: Mon–Sat 9–17, Sun 9–14.
function clinicStatus(now = new Date()) {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Manila', weekday: 'short', hour: 'numeric', hourCycle: 'h23' }).formatToParts(now);
  const day = parts.find((p) => p.type === 'weekday')?.value;
  const hour = Number(parts.find((p) => p.type === 'hour')?.value);
  const close = day === 'Sun' ? 14 : 17;
  const closeLabel = day === 'Sun' ? '2 PM' : '5 PM';
  if (hour >= 9 && hour < close) return { open: true, label: `Open now · until ${closeLabel}` };
  return { open: false, label: hour < 9 ? 'Opens today at 9 AM' : 'Opens tomorrow at 9 AM' };
}

// Instagram-style carousel: swipe (touch / trackpad), drag with a mouse,
// arrow buttons, arrow keys or the dots. Native scroll-snap does the
// snapping, so it still scrolls without JS; nothing auto-advances.
function ServiceCarousel({ services, phoneHref }) {
  const trackRef = useRef(null);
  const drag = useRef(null);
  const [index, setIndex] = useState(0);
  const [atEnd, setAtEnd] = useState(false);
  const total = services.length;

  function cardStep() {
    const track = trackRef.current;
    const card = track?.children[0];
    if (!card) return 1;
    const gap = parseFloat(getComputedStyle(track).columnGap) || 0;
    return card.getBoundingClientRect().width + gap;
  }

  function goTo(i) {
    const track = trackRef.current;
    if (!track) return;
    const next = Math.max(0, Math.min(total - 1, i));
    const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    track.scrollTo({ left: next * cardStep(), behavior: smooth ? 'smooth' : 'auto' });
  }

  function onScroll() {
    const track = trackRef.current;
    if (!track) return;
    setIndex(Math.min(total - 1, Math.round(track.scrollLeft / cardStep())));
    setAtEnd(track.scrollLeft + track.clientWidth >= track.scrollWidth - 4);
  }

  function onKeyDown(event) {
    if (event.key === 'ArrowRight') { event.preventDefault(); goTo(index + 1); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); goTo(index - 1); }
  }

  // Mouse drag; touch and trackpads already swipe natively.
  function onPointerDown(event) {
    if (event.pointerType !== 'mouse' || event.button !== 0) return;
    drag.current = { x: event.clientX, left: trackRef.current.scrollLeft };
    trackRef.current.classList.add('is-dragging');
  }
  function onPointerMove(event) {
    if (!drag.current) return;
    trackRef.current.scrollLeft = drag.current.left - (event.clientX - drag.current.x);
  }
  function endDrag() {
    if (!drag.current) return;
    const track = trackRef.current;
    track.classList.remove('is-dragging');
    drag.current = null;
    goTo(Math.round(track.scrollLeft / cardStep()));
  }

  return (
    <div className="tw6-ig" role="region" aria-roledescription="carousel" aria-label="Dental services">
      <ul
        className="tw6-ig-track"
        ref={trackRef}
        tabIndex={0}
        aria-label="Swipe, drag or use the arrow keys to see more services"
        onScroll={onScroll}
        onKeyDown={onKeyDown}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerLeave={endDrag}
        onDragStart={(event) => event.preventDefault()}
      >
        {services.map((service, i) => (
          <li key={service.name} className="tw6-ig-card" aria-roledescription="slide" aria-label={`${i + 1} of ${total}: ${service.name}`}>
            <div className="tw6-ig-media">
              <picture>
                <source
                  type="image/webp"
                  srcSet={`/codismile/services-stock/${service.photo}-600.webp 600w, /codismile/services-stock/${service.photo}.webp 1200w`}
                  sizes="(max-width: 768px) 84vw, 400px"
                />
                <img
                  src={`/codismile/services-stock/${service.photo}.jpg`}
                  width="1200"
                  height="900"
                  loading={i < 3 ? 'eager' : 'lazy'}
                  decoding="async"
                  alt=""
                />
              </picture>
              <span className="tw6-ig-count" aria-hidden="true">{i + 1}/{total}</span>
            </div>
            <div className="tw6-ig-body">
              <h3>{service.name}</h3>
              {service.local && <p className="tw6-ig-local">{service.local}</p>}
              <p>{service.description}</p>
              <a className="tw6-ig-ask" href={phoneHref}><Phone size={15} aria-hidden="true" /> Ask about this<span className="sr-only">: {service.name}</span></a>
            </div>
          </li>
        ))}
      </ul>
      <button type="button" className="tw6-ig-nav tw6-ig-prev" onClick={() => goTo(index - 1)} disabled={index === 0} aria-label="Previous service"><ChevronLeft size={22} /></button>
      <button type="button" className="tw6-ig-nav tw6-ig-next" onClick={() => goTo(index + 1)} disabled={atEnd} aria-label="Next service"><ChevronRight size={22} /></button>
      <div className="tw6-ig-dots">
        {services.map((service, i) => (
          <button key={service.name} type="button" className={i === index ? 'is-active' : ''} aria-label={`Show ${service.name}`} aria-current={i === index ? 'true' : undefined} onClick={() => goTo(i)} />
        ))}
      </div>
      <p className="sr-only" aria-live="polite">Showing {services[index]?.name}, {index + 1} of {total}</p>
    </div>
  );
}

function FAQItem({ question, answer }) {
  return (
    <details className="tw6-faq-item">
      <summary>{question}<ChevronDown size={18} /></summary>
      <p>{answer}</p>
    </details>
  );
}

export default function Landing() {
  const navigate = useNavigate();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('');
  const [showStickyCta, setShowStickyCta] = useState(false);
  const [status] = useState(() => clinicStatus());
  const navRef = useRef(null);
  const heroRef = useRef(null);

  function scrollToSection(event, id) {
    if (event) event.preventDefault();
    setMobileNavOpen(false);

    const target = document.getElementById(id);
    if (!target) return;

    const offset = (navRef.current?.getBoundingClientRect().height || 68) + 16;
    const top = target.getBoundingClientRect().top + window.scrollY - offset;

    window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });

    const hash = id === 'top' ? '' : `#${id}`;
    window.history.replaceState(null, '', `${window.location.pathname}${hash}`);
  }

  useEffect(() => {
    const scrollFromHash = () => {
      const hash = window.location.hash.replace('#', '');
      if (!hash) return;
      window.setTimeout(() => scrollToSection(null, hash), 60);
    };

    scrollFromHash();
    window.addEventListener('hashchange', scrollFromHash);
    return () => window.removeEventListener('hashchange', scrollFromHash);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const ids = ['toothwise', 'services', 'faq', 'find-us'];
    const sections = ids.map((id) => document.getElementById(id)).filter(Boolean);
    if (!sections.length) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActiveSection(entry.target.id);
        });
      },
      { rootMargin: '-42% 0px -50% 0px', threshold: 0 }
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  // Mobile call bar appears once the hero's own buttons scroll out of view.
  useEffect(() => {
    const hero = heroRef.current;
    if (!hero || typeof IntersectionObserver === 'undefined') return undefined;
    const observer = new IntersectionObserver(([entry]) => setShowStickyCta(!entry.isIntersecting), { threshold: 0 });
    observer.observe(hero);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const old = document.getElementById('tw-local-business-schema');
    if (old) old.remove();
    const script = document.createElement('script');
    script.id = 'tw-local-business-schema';
    script.type = 'application/ld+json';
    script.textContent = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'Dentist',
      name: CLINIC.name,
      telephone: CLINIC.phone,
      address: { '@type': 'PostalAddress', streetAddress: CLINIC.address, addressLocality: 'Manila', addressCountry: 'PH' },
      areaServed: 'Manila, Philippines',
      url: window.location.origin,
    });
    document.head.appendChild(script);
    return () => script.remove();
  }, []);

  const directionsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(CLINIC.mapQuery)}`;
  const phoneHref = `tel:${CLINIC.phone.replace(/\s/g, '')}`;
  const mapEmbed = `https://www.google.com/maps?q=${encodeURIComponent(CLINIC.mapQuery)}&output=embed`;

  const openPortal = () => { setMobileNavOpen(false); navigate('/patient-portal'); };

  return (
    <div className="tw6">
      <SEO
        title="CodiSmile Dental Clinic | ToothWise"
        description="Dental care beside LRT Central Terminal, Ermita, Manila. Ten treatments, open seven days, with AI screening and your results online through ToothWise."
        structuredData={{ '@context': 'https://schema.org', '@type': 'WebSite', name: 'ToothWise', url: window.location.origin }}
      />

      <header ref={navRef} className={`tw6-nav${mobileNavOpen ? ' is-open' : ''}`}>
        <div className="tw6-nav-inner">
          <a href="#top" className="tw6-brand" aria-label="CodiSmile Dental Clinic" onClick={(event) => scrollToSection(event, 'top')}>
            <picture><source type="image/webp" srcSet="/codismile/codismile-logo-96.webp 1x, /codismile/codismile-logo-192.webp 2x" /><img src="/codismile/codismile-logo-96.png" srcSet="/codismile/codismile-logo-96.png 1x, /codismile/codismile-logo-192.png 2x" width="42" height="42" alt="" /></picture>
            <span><strong>CodiSmile</strong>{' '}<small>Dental Clinic</small></span>
          </a>
          <button
            type="button"
            className={`tw6-nav-toggle ${mobileNavOpen ? 'is-open' : ''}`}
            aria-expanded={mobileNavOpen}
            aria-controls="tw6-public-nav"
            aria-label={mobileNavOpen ? 'Close navigation menu' : 'Open navigation menu'}
            onClick={() => setMobileNavOpen((open) => !open)}
          >
            <span className="tw6-hamburger" aria-hidden="true"><i /><i /><i /></span>
          </button>
          <nav id="tw6-public-nav" className={mobileNavOpen ? 'is-open' : ''} aria-label="Public navigation">
            <button type="button" className={activeSection === 'services' ? 'is-active' : ''} onClick={(event) => scrollToSection(event, 'services')}>Services</button>
            <button type="button" className={activeSection === 'toothwise' ? 'is-active' : ''} onClick={(event) => scrollToSection(event, 'toothwise')}>ToothWise</button>
            <button type="button" className={activeSection === 'faq' ? 'is-active' : ''} onClick={(event) => scrollToSection(event, 'faq')}>FAQ</button>
            <button type="button" className={activeSection === 'find-us' ? 'is-active' : ''} onClick={(event) => scrollToSection(event, 'find-us')}>Find us</button>
            <a className="tw6-nav-phone" href={phoneHref}><Phone size={15} aria-hidden="true" /> {CLINIC.phone}</a>
            <button type="button" className="tw6-nav-cta" onClick={openPortal}>Patient Portal <ArrowRight size={15} /></button>
          </nav>
        </div>
      </header>

      <main id="top" className="tw6-main">
        <section className="tw6-hero" ref={heroRef}>
          <div className="tw6-hero-copy">
            <p className={`tw6-status${status.open ? ' is-open' : ''}`}><span className="tw6-status-dot" aria-hidden="true" />{status.label}<span className="tw6-status-sep" aria-hidden="true">·</span>Ermita, Manila</p>
            <h1>A healthier smile, right beside the LRT.</h1>
            <p className="tw6-lede">Ten dental treatments, seven days a week, at LRT Central Terminal. And with ToothWise, your screenings and your dentist’s advice follow you home.</p>
            <div className="tw6-actions">
              <a className="tw6-btn tw6-btn-primary tw6-btn-lg" href={phoneHref}><Phone size={18} aria-hidden="true" /> Call to book a visit</a>
              <button type="button" className="tw6-btn tw6-btn-ghost tw6-btn-lg" onClick={openPortal}>Open Patient Portal <ArrowRight size={17} /></button>
            </div>
            <ul className="tw6-trust">
              <li><Check size={16} aria-hidden="true" /> Open Sundays</li>
              <li><Check size={16} aria-hidden="true" /> Cleanings to braces</li>
              <li><Check size={16} aria-hidden="true" /> AI screening reviewed by dentists</li>
            </ul>
          </div>
          <figure className="tw6-hero-media">
            <div className="tw6-hero-disc">
              <picture>
                <source type="image/webp" srcSet="/codismile/codismile-logo-hero.webp" />
                <img className="tw6-hero-logo" src="/codismile/codismile-logo-transparent.png" width="734" height="767" fetchpriority="high" alt="CodiSmile Dental Clinic logo" />
              </picture>
            </div>
            <div className="tw6-float tw6-float-a" aria-hidden="true">
              <span className="tw6-float-icon"><TrainFront size={18} /></span>
              <span><strong>Beside LRT Central</strong><small>Arroceros St., Ermita</small></span>
            </div>
            <div className="tw6-float tw6-float-b" aria-hidden="true">
              <span className="tw6-float-icon"><ScanSearch size={18} /></span>
              <span><strong>Results online</strong><small>Reviewed by your dentist</small></span>
            </div>
          </figure>
        </section>

        <section className="tw6-highlights" aria-label="Clinic at a glance">
          <ul className="tw6-highlights-inner">
            {FACTS.map(({ value, text }) => (
              <li key={value} className="tw6-highlight">
                <strong>{value}</strong>
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </section>

        <Reveal as="section" className="tw6-services" id="services">
          <div className="tw6-section-head">
            <p className="tw6-eyebrow">Services</p>
            <h2>Everything your smile needs, under one roof.</h2>
            <p>From a routine cleaning to braces, crowns and whitening. No referrals across the city, no second clinic.</p>
          </div>
          <ServiceCarousel services={SERVICES} phoneHref={phoneHref} />
          <div className="tw6-services-cta">
            <p><strong>Not sure what you need?</strong> Call us and we’ll point you to the right treatment.</p>
            <a className="tw6-btn tw6-btn-primary" href={phoneHref}><Phone size={16} aria-hidden="true" /> Call {CLINIC.phone}</a>
          </div>
        </Reveal>

        <Reveal as="section" className="tw6-story" id="toothwise">
          <div className="tw6-section-head tw6-section-head-center">
            <p className="tw6-eyebrow">ToothWise patient portal</p>
            <h2>Your dental care doesn’t stop at the door.</h2>
            <p>ToothWise is CodiSmile’s own portal. See what your dentist found, what to do next, and how to prevent problems. Anytime, from your phone.</p>
          </div>
          <ul className="tw6-benefits">
            {BENEFITS.map(({ icon: Icon, title, text }) => (
              <li key={title}>
                <span className="tw6-benefit-icon"><Icon size={22} aria-hidden="true" /></span>
                <h3>{title}</h3>
                <p>{text}</p>
              </li>
            ))}
          </ul>
          <div className="tw6-how">
            <h3 className="tw6-how-title">How it works</h3>
            <ol className="tw6-steps">
              {STEPS.map(({ title, text }, i) => (
                <li key={title}>
                  <span className="tw6-step-num" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
                  <h4>{title}</h4>
                  <p>{text}</p>
                </li>
              ))}
            </ol>
            <button type="button" className="tw6-btn tw6-btn-primary" onClick={openPortal}>Explore ToothWise <ArrowRight size={16} /></button>
          </div>
        </Reveal>

        <Reveal as="section" className="tw6-prevention">
          <div className="tw6-prevention-inner">
            <h2>Your next checkup is one call away.</h2>
            <p>Open every day beside LRT Central Terminal. Call the clinic to book, then follow your results online.</p>
            <div className="tw6-actions tw6-actions-center">
              <a className="tw6-btn tw6-btn-light tw6-btn-lg" href={phoneHref}><Phone size={18} aria-hidden="true" /> Call {CLINIC.phone}</a>
              <button type="button" className="tw6-btn tw6-btn-outline-light tw6-btn-lg" onClick={openPortal}>Open Patient Portal <ArrowRight size={17} /></button>
            </div>
          </div>
        </Reveal>

        <Reveal as="section" className="tw6-faq-wrap" id="faq">
          <div className="tw6-faq-head">
            <p className="tw6-eyebrow">FAQ</p>
            <h2>Answers before you visit.</h2>
            <p>Have a general question? Our AI assistant can help any time. Anything about your own records stays in the secure portal.</p>
            <button type="button" className="tw6-btn tw6-btn-ghost" onClick={() => document.querySelector('.chat-fab')?.click()}><MessageCircle size={16} /> Ask the assistant</button>
          </div>
          <div className="tw6-faq-list">{FAQS.map(([question, answer]) => <FAQItem key={question} question={question} answer={answer} />)}</div>
        </Reveal>

        <Reveal as="section" className="tw6-find" id="find-us">
          <div className="tw6-find-copy">
            <p className="tw6-eyebrow">Find us</p>
            <h2>Steps from LRT Central Terminal.</h2>
            <p>Hop off the train and you’re here. Call ahead to book your slot, or tap below for directions.</p>
            <ul className="tw6-contact-list">
              <li><MapPin size={18} /><span>{CLINIC.address}</span></li>
              <li><Phone size={18} /><a href={phoneHref}>{CLINIC.phone}</a></li>
              <li><Clock3 size={18} /><span>Mon to Sat 9:00 AM to 5:00 PM · Sun 9:00 AM to 2:00 PM</span></li>
            </ul>
            <div className="tw6-actions">
              <a className="tw6-btn tw6-btn-primary" target="_blank" rel="noreferrer" href={directionsUrl}><Navigation size={16} /> Get directions</a>
              <a className="tw6-btn tw6-btn-light" href={phoneHref}><Phone size={16} /> Call clinic</a>
            </div>
          </div>
          <div className="tw6-map-card">
            <div className="tw6-map-frame">
              <iframe title="CodiSmile Dental Clinic map" src={mapEmbed} loading="lazy" referrerPolicy="no-referrer-when-downgrade" />
            </div>
            <a className="tw6-map-open" href={directionsUrl} target="_blank" rel="noreferrer">Open in Google Maps <ArrowUpRight size={16} /></a>
          </div>
        </Reveal>
      </main>

      <footer className="tw6-footer">
        <div className="tw6-footer-top">
          <p className="tw6-footer-name">Smile brighter with CodiSmile.</p>
          <div className="tw6-footer-actions">
            <a className="tw6-footer-cta" href={phoneHref}><Phone size={16} aria-hidden="true" /> Call to book</a>
            <button type="button" className="tw6-footer-cta tw6-footer-cta-alt" onClick={openPortal}>
              Patient Portal <ArrowRight size={16} />
            </button>
          </div>
        </div>

        <div className="tw6-footer-grid">
          <div className="tw6-footer-col">
            <h2>Visit</h2>
            <p>{CLINIC.address}</p>
            <a target="_blank" rel="noreferrer" href={directionsUrl}>Get directions <ArrowUpRight size={14} /></a>
          </div>
          <div className="tw6-footer-col">
            <h2>Contact</h2>
            <a href={phoneHref}>{CLINIC.phone}</a>
            <p>Mon to Sat 9:00 AM to 5:00 PM<br />Sun 9:00 AM to 2:00 PM</p>
          </div>
          <div className="tw6-footer-col tw6-footer-nav">
            <h2>ToothWise</h2>
            <p>AI dental screening and patient workflow for {CLINIC.name}.</p>
            <button type="button" onClick={(event) => scrollToSection(event, 'faq')}>Read the FAQ</button>
          </div>
        </div>

        <div className="tw6-footer-bottom">
          <span>© {new Date().getFullYear()} {CLINIC.name}</span>
          <div className="tw6-footer-links"><Link to="/privacy">Privacy</Link><Link to="/thank-you">Thank You</Link><button type="button" onClick={() => navigate('/login')}>Staff Login</button></div>
        </div>
      </footer>

      <div className={`tw6-sticky-cta${showStickyCta ? ' is-visible' : ''}`} aria-hidden={!showStickyCta}>
        <a className="tw6-btn tw6-btn-primary" href={phoneHref} tabIndex={showStickyCta ? 0 : -1}><Phone size={16} aria-hidden="true" /> Call to book</a>
        <button type="button" className="tw6-btn tw6-btn-ghost" onClick={openPortal} tabIndex={showStickyCta ? 0 : -1}>Portal</button>
      </div>

      <ChatWidget />
    </div>
  );
}
