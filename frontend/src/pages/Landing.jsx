import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight, ArrowUpRight, ChevronDown, ChevronLeft, ChevronRight, Clock3, MapPin, MessageCircle,
  Navigation, Phone, ScanSearch, ShieldCheck, Stethoscope, UsersRound,
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
  { name: 'Tooth Restoration', local: 'Pasta', photo: 'restoration', description: 'Repairs teeth affected by cavities or damage using a tooth-coloured filling material.' },
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
  ['What is ToothWise?', 'ToothWise is CodiSmile’s digital dental-care workspace for patient access, AI-assisted image screening, clinical workflows, and prevention guidance.'],
  ['Does the AI replace a dentist?', 'No. ToothWise is an assistive screening system. A qualified dental professional should review AI-assisted findings and make clinical decisions.'],
  ['Can the chatbot see my patient record?', 'No. The public AI assistant is intentionally separated from individual patient records and screening results. Use the secure Patient Portal for account-specific information.'],
  ['How do I book a visit?', 'Contact CodiSmile Dental Clinic directly by phone to schedule a visit — the Patient Portal covers account access and screening history, not booking.'],
  ['What are the clinic hours?', 'CodiSmile is open Monday–Saturday, 9:00 AM–5:00 PM, and Sunday, 9:00 AM–2:00 PM.'],
];

const FACTS = [
  { title: 'Open seven days', text: 'Mon–Sat 9 AM–5 PM, Sun 9 AM–2 PM' },
  { title: 'Beside the LRT', text: 'Central Terminal, Arroceros St., Ermita' },
  { title: 'Ten treatments', text: 'From cleaning to braces and dentures' },
  { title: 'Results online', text: 'Screenings and advice in your portal' },
];

const STEPS = [
  { icon: ShieldCheck, title: 'Access', text: 'Patients and staff enter separate role-based workspaces.' },
  { icon: ScanSearch, title: 'Screen', text: 'Dental images can be processed through the AI-assisted screening workflow.' },
  { icon: Stethoscope, title: 'Review', text: 'A dental professional interprets findings and guides the next step.' },
];

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
  const navRef = useRef(null);

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

  return (
    <div className="tw6">
      <SEO
        title="CodiSmile Dental Clinic | ToothWise"
        description="CodiSmile Dental Clinic and ToothWise: patient access, AI-assisted dental screening, prevention guidance, and clinic information."
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
            <button type="button" className={activeSection === 'toothwise' ? 'is-active' : ''} onClick={(event) => scrollToSection(event, 'toothwise')}>ToothWise</button>
            <button type="button" className={activeSection === 'services' ? 'is-active' : ''} onClick={(event) => scrollToSection(event, 'services')}>Services</button>
            <button type="button" className={activeSection === 'faq' ? 'is-active' : ''} onClick={(event) => scrollToSection(event, 'faq')}>FAQ</button>
            <button type="button" className={activeSection === 'find-us' ? 'is-active' : ''} onClick={(event) => scrollToSection(event, 'find-us')}>Find us</button>
            <button className="tw6-nav-cta" onClick={() => { setMobileNavOpen(false); navigate('/patient-portal'); }}>Patient Portal <ArrowRight size={15} /></button>
          </nav>
        </div>
      </header>

      <main id="top" className="tw6-main">
        <section className="tw6-hero">
          <div className="tw6-hero-copy">
            <h1>Dental care in Ermita, Manila.</h1>
            <p>CodiSmile Dental Clinic sits beside LRT Central Terminal. Through ToothWise, our patient portal, you can see your AI-assisted screenings and your dentist’s advice between visits.</p>
            <div className="tw6-actions">
              <button className="tw6-btn tw6-btn-primary" onClick={() => navigate('/patient-portal')}>Open Patient Portal <ArrowRight size={17} /></button>
              <a className="tw6-btn tw6-btn-ghost" href={phoneHref}><Phone size={16} /> Call the clinic</a>
            </div>
            <p className="tw6-hours"><Clock3 size={16} aria-hidden="true" /> <span>Open every day</span> <span>Mon–Sat 9 AM–5 PM</span> <span>Sun 9 AM–2 PM</span></p>
          </div>
          <figure className="tw6-hero-media">
            <picture>
              <source type="image/webp" srcSet="/codismile/codismile-logo-hero.webp" />
              <img className="tw6-hero-logo" src="/codismile/codismile-logo-transparent.png" width="734" height="767" fetchpriority="high" alt="CodiSmile Dental Clinic logo" />
            </picture>
          </figure>
        </section>

        <section className="tw6-highlights" aria-label="Clinic at a glance">
          <ul className="tw6-highlights-inner">
            {FACTS.map(({ title, text }) => (
              <li key={title} className="tw6-highlight">
                <strong>{title}</strong>
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </section>

        <Reveal as="section" className="tw6-story" id="toothwise">
          <div className="tw6-story-copy">
            <h2>One portal for every visit.</h2>
            <p>ToothWise connects patient access with the clinic’s own workflow, so the path from screening to professional review and prevention advice is easy to follow.</p>
            <ul className="tw6-checks">
              <li><UsersRound size={20} /><span><strong>Patient-first access</strong><small>Patients get their own secure portal rather than sharing the staff workspace.</small></span></li>
              <li><ScanSearch size={20} /><span><strong>AI-assisted screening</strong><small>Dental image findings support a professional review, never replace it.</small></span></li>
              <li><Stethoscope size={20} /><span><strong>Professional judgment</strong><small>A qualified dentist makes every clinical decision.</small></span></li>
            </ul>
            <button className="tw6-btn tw6-btn-primary" onClick={() => navigate('/patient-portal')}>Explore ToothWise <ArrowRight size={16} /></button>
          </div>
          <ol className="tw6-steps" aria-label="How ToothWise works">
            {STEPS.map(({ icon: Icon, title, text }) => (
              <li key={title}>
                <Icon size={22} aria-hidden="true" />
                <h3>{title}</h3>
                <p>{text}</p>
              </li>
            ))}
          </ol>
        </Reveal>

        <Reveal as="section" className="tw6-services" id="services">
          <div className="tw6-section-head">
            <h2>Ten treatments under one roof.</h2>
            <p>Swipe through them, then call the clinic to ask which one suits you.</p>
          </div>
          <ServiceCarousel services={SERVICES} phoneHref={phoneHref} />
          <a className="tw6-btn tw6-btn-ghost tw6-services-call" href={phoneHref}><Phone size={16} /> Ask about a treatment</a>
        </Reveal>

        <Reveal as="section" className="tw6-prevention">
          <div className="tw6-prevention-inner">
            <h2>See your results from home.</h2>
            <p>Your screenings and your dentist’s recommendations stay in the Patient Portal, while prevention and treatment remain guided by the clinic.</p>
            <button className="tw6-btn tw6-btn-light" onClick={() => navigate('/patient-portal')}>Open Patient Portal <ArrowRight size={17} /></button>
          </div>
        </Reveal>

        <Reveal as="section" className="tw6-faq-wrap" id="faq">
          <div className="tw6-faq-head">
            <h2>Questions before your visit.</h2>
            <p>For general questions, the AI assistant is in the corner of the page. Patient-specific information stays inside the secure portal.</p>
            <button className="tw6-btn tw6-btn-ghost" onClick={() => document.querySelector('.chat-fab')?.click()}><MessageCircle size={16} /> Ask the assistant</button>
          </div>
          <div className="tw6-faq-list">{FAQS.map(([question, answer]) => <FAQItem key={question} question={question} answer={answer} />)}</div>
        </Reveal>

        <Reveal as="section" className="tw6-find" id="find-us">
          <div className="tw6-find-copy">
            <h2>Find us at Central Terminal.</h2>
            <p>Visit the clinic in Ermita, Manila, or call the team for appointments and service information.</p>
            <ul className="tw6-contact-list">
              <li><MapPin size={18} /><span>{CLINIC.address}</span></li>
              <li><Phone size={18} /><a href={phoneHref}>{CLINIC.phone}</a></li>
              <li><Clock3 size={18} /><span>Mon–Sat 9:00 AM–5:00 PM · Sun 9:00 AM–2:00 PM</span></li>
            </ul>
            <div className="tw6-actions">
              <a className="tw6-btn tw6-btn-primary" target="_blank" rel="noreferrer" href={directionsUrl}><Navigation size={16} /> Get directions</a>
              <a className="tw6-btn tw6-btn-ghost" href={phoneHref}><Phone size={16} /> Call clinic</a>
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
          <p className="tw6-footer-name">CodiSmile Dental Clinic</p>
          <button type="button" className="tw6-footer-cta" onClick={() => navigate('/patient-portal')}>
            Open Patient Portal <ArrowRight size={16} />
          </button>
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
            <p>Mon–Sat 9:00 AM–5:00 PM<br />Sun 9:00 AM–2:00 PM</p>
          </div>
          <div className="tw6-footer-col tw6-footer-nav">
            <h2>ToothWise</h2>
            <p>AI-assisted dental screening and patient workflow for {CLINIC.name}.</p>
            <button type="button" onClick={(event) => scrollToSection(event, 'faq')}>Read the FAQ</button>
          </div>
        </div>

        <div className="tw6-footer-bottom">
          <span>© {new Date().getFullYear()} {CLINIC.name}</span>
          <div className="tw6-footer-links"><Link to="/privacy">Privacy</Link><Link to="/thank-you">Thank You</Link><button onClick={() => navigate('/login')}>Staff Login</button></div>
        </div>
      </footer>

      <ChatWidget />
    </div>
  );
}
