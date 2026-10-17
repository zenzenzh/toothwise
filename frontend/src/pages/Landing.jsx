import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight, ArrowUpRight, CheckCircle2, ChevronDown, Clock3,
  HeartPulse, MapPin, Navigation, Phone, ScanSearch, ShieldCheck,
  Sparkles, Stethoscope, UsersRound, Activity, MessageCircle, LocateFixed
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

const SERVICES = [
  { name: 'Oral Prophylaxis (Cleaning)', description: 'Professional cleaning that removes plaque, tartar, and surface stains to help keep gums and teeth healthy.', image: '/codismile/services/preventive-cleaning.jpg' },
  { name: 'Tooth Restoration (Pasta)', description: 'Repairs teeth affected by cavities or damage using a tooth-colored filling material.', image: '/codismile/services/tooth-restoration.jpg' },
  { name: 'Tooth Extraction (Bunot)', description: 'Removes a tooth that cannot be safely restored or needs to be taken out for dental treatment.', image: '/codismile/services/surgical-extraction.jpg' },
  { name: 'Dentures (Pustiso)', description: 'Removable replacement teeth that help restore chewing, speaking, and the appearance of your smile.', image: '/codismile/services/dentures.jpg' },
  { name: 'Fixed Bridge and Crowns', description: 'Restores missing or damaged teeth with fixed dental restorations designed to look and function naturally.', image: '/codismile/services/crowns-bridge.jpg' },
  { name: 'Veneers', description: 'Thin coverings placed on the front of teeth to improve their shape, color, and overall appearance.', image: '/codismile/services/veneers.jpg' },
  { name: 'Root Canal', description: 'Treats infection or inflammation inside a tooth so the natural tooth can be preserved.', image: '/codismile/services/root-canal.jpg' },
  { name: 'Orthodontics (Braces & Retainers)', description: 'Guides teeth into a healthier alignment and helps maintain the result after orthodontic treatment.', image: '/codismile/services/orthodontics-braces.jpg' },
  { name: 'Oral Surgery', description: 'Provides surgical dental care for conditions that need treatment beyond routine procedures.', image: '/codismile/services/surgical-extraction.jpg' },
  { name: 'Teeth Whitening', description: 'Brightens natural teeth by reducing certain stains and discoloration for a lighter smile.', image: '/codismile/services/cosmetic-whitening.jpg' },
];

const FAQS = [
  ['What is ToothWise?', 'ToothWise is CodiSmile’s digital dental-care workspace for patient access, AI-assisted image screening, clinical workflows, and prevention guidance.'],
  ['Does the AI replace a dentist?', 'No. ToothWise is an assistive screening system. A qualified dental professional should review AI-assisted findings and make clinical decisions.'],
  ['Can the chatbot see my patient record?', 'No. The public AI assistant is intentionally separated from individual patient records and screening results. Use the secure Patient Portal for account-specific information.'],
  ['How do I book a visit?', 'Contact CodiSmile Dental Clinic directly by phone to schedule a visit — the Patient Portal covers account access and screening history, not booking.'],
  ['What are the clinic hours?', 'CodiSmile is open Monday–Saturday, 9:00 AM–5:00 PM, and Sunday, 9:00 AM–2:00 PM.'],
];

const HIGHLIGHTS = [
  { icon: Activity, title: 'One workspace', text: 'Clinic operations and patient access in one system.' },
  { icon: ScanSearch, title: 'Assistive AI', text: 'Screening findings are for professional review.' },
  { icon: ShieldCheck, title: 'Role-based access', text: 'Patient and staff workspaces remain separated.' },
  { icon: MessageCircle, title: 'AI assistant', text: 'General clinic and dental-care guidance.' },
];

const STEPS = [
  { icon: ShieldCheck, title: 'Access', text: 'Patients and staff enter separate role-based workspaces.' },
  { icon: ScanSearch, title: 'Screen', text: 'Dental images can be processed through the AI-assisted screening workflow.' },
  { icon: Stethoscope, title: 'Review', text: 'A dental professional interprets findings and guides the next step.' },
];

function FAQItem({ question, answer }) {
  return (
    <details className="tw6-faq-item">
      <summary>{question}<ChevronDown size={18} /></summary>
      <p>{answer}</p>
    </details>
  );
}

function ServiceCarousel({ services, onAskAbout }) {
  const trackRef = useRef(null);
  const timerRef = useRef(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const total = services.length;

  function scrollToIndex(index) {
    const track = trackRef.current;
    if (!track) return;
    const card = track.children[index];
    if (!card) return;
    const offset = card.getBoundingClientRect().left - track.getBoundingClientRect().left + track.scrollLeft;
    track.scrollTo({ left: offset, behavior: 'smooth' });
    setActiveIndex(index);
  }

  useEffect(() => {
    timerRef.current = window.setInterval(() => {
      setActiveIndex((current) => {
        const next = (current + 1) % total;
        const track = trackRef.current;
        const card = track?.children[next];
        if (track && card) {
          const offset = card.getBoundingClientRect().left - track.getBoundingClientRect().left + track.scrollLeft;
          track.scrollTo({ left: offset, behavior: 'smooth' });
        }
        return next;
      });
    }, 4000);
    return () => window.clearInterval(timerRef.current);
  }, [total]);

  function pauseAutoplay() {
    window.clearInterval(timerRef.current);
  }

  // Keep the dots in sync when the person swipes the track manually
  // (rather than only updating on button/dot-driven scrolls).
  function handleTrackScroll() {
    const track = trackRef.current;
    if (!track) return;
    window.clearTimeout(track.__snapTimer);
    track.__snapTimer = window.setTimeout(() => {
      const trackRect = track.getBoundingClientRect();
      let closest = 0;
      let closestDist = Infinity;
      Array.from(track.children).forEach((card, index) => {
        const dist = Math.abs(card.getBoundingClientRect().left - trackRect.left);
        if (dist < closestDist) { closestDist = dist; closest = index; }
      });
      setActiveIndex(closest);
    }, 80);
  }

  return (
    <div
      className="tw6-carousel"
      aria-label="Dental services"
      onMouseEnter={pauseAutoplay}
      onTouchStart={pauseAutoplay}
    >
      <div className="tw6-carousel-track" ref={trackRef} onScroll={handleTrackScroll}>
        {services.map((service, index) => (
          <div key={service.name} className={`tw6-carousel-card${index === activeIndex ? ' is-active' : ''}`}>
            <div className="tw6-carousel-card-image">
              <picture>
                <source
                  type="image/webp"
                  srcSet={`${service.image.replace('.jpg', '-480.webp')} 480w, ${service.image.replace('.jpg', '.webp')} 720w`}
                  sizes="(max-width: 760px) 82vw, 360px"
                />
                <img
                  src={service.image}
                  srcSet={`${service.image.replace('.jpg', '-480.jpg')} 480w, ${service.image} 720w`}
                  sizes="(max-width: 760px) 82vw, 360px"
                  loading="lazy"
                  alt={`${service.name} - CodiSmile Dental Clinic`}
                />
              </picture>
            </div>
            <div className="tw6-carousel-card-body">
              <strong>{service.name}</strong>
              <p>{service.description}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="tw6-carousel-dots" role="tablist" aria-label="Service slides">
        {services.map((service, index) => (
          <button
            key={service.name}
            type="button"
            role="tab"
            aria-selected={index === activeIndex}
            className={index === activeIndex ? 'is-active' : ''}
            aria-label={`Go to ${service.name}`}
            onClick={() => { pauseAutoplay(); scrollToIndex(index); }}
          />
        ))}
      </div>
      <button type="button" className="tw6-carousel-cta" onClick={onAskAbout}>
        Ask about any service <ArrowUpRight size={14} />
      </button>
    </div>
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

    const target = id === 'top'
      ? document.getElementById('top')
      : document.getElementById(id);

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
            <span><strong>CodiSmile</strong>{' '}<small>DENTAL CLINIC</small></span>
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
            <h1>A calmer way to stay on top of your dental care.</h1>
            <p>One connected space for patient access, AI-assisted screening, and prevention guidance — designed to support the clinic, not replace the dentist.</p>
            <div className="tw6-actions">
              <button className="tw6-btn tw6-btn-primary" onClick={() => navigate('/patient-portal')}>Open Patient Portal <ArrowRight size={17} /></button>
              <a className="tw6-btn tw6-btn-ghost" href={phoneHref}><Phone size={16} /> Call the clinic</a>
            </div>
            <div className="tw6-proof"><CheckCircle2 size={15} /> Secure role-based access <span /> <HeartPulse size={15} /> AI stays assistive</div>
          </div>
          <figure className="tw6-hero-media">
            <picture>
              <source
                type="image/webp"
                srcSet="/codismile/hero-720.webp 720w, /codismile/hero.webp 1080w"
                sizes="(max-width: 1024px) 100vw, 50vw"
              />
              {/* The hero photo is the LCP element: fetch it first. */}
              <img
                src="/codismile/hero.jpg"
                srcSet="/codismile/hero-720.jpg 720w, /codismile/hero.jpg 1080w"
                sizes="(max-width: 1024px) 100vw, 50vw"
                width="1080"
                height="1080"
                fetchpriority="high"
                alt="CodiSmile Dental Clinic treatment room"
              />
            </picture>
            <figcaption className="tw6-hero-chip">
              <span className="tw6-chip-icon"><Activity size={16} /></span>
              <span><strong>From screening to recommendation</strong><small>Organized around the clinic workflow.</small></span>
            </figcaption>
          </figure>
        </section>

        <section className="tw6-highlights" aria-label="ToothWise highlights">
          <div className="tw6-highlights-inner">
            {HIGHLIGHTS.map(({ icon: Icon, title, text }) => (
              <div key={title} className="tw6-highlight">
                <Icon size={19} />
                <strong>{title}</strong>
                <span>{text}</span>
              </div>
            ))}
          </div>
        </section>

        <Reveal as="section" className="tw6-story" id="toothwise">
          <div className="tw6-story-media">
            <picture>
              <source
                type="image/webp"
                srcSet="/codismile/location-720.webp 720w, /codismile/location.webp 1080w"
                sizes="(max-width: 1024px) 100vw, 50vw"
              />
              <img
                src="/codismile/location.jpg"
                srcSet="/codismile/location-720.jpg 720w, /codismile/location.jpg 1080w"
                sizes="(max-width: 1024px) 100vw, 50vw"
                width="1080"
                height="1080"
                loading="lazy"
                decoding="async"
                alt="CodiSmile Dental Clinic storefront"
              />
            </picture>
            <div className="tw6-photo-note"><MapPin size={14} /><span>Ermita, Manila City</span></div>
          </div>
          <div className="tw6-story-copy">
            <h2>Digital tools should make care feel more connected.</h2>
            <p>ToothWise connects patient access with the clinic’s operational workflow. The result is a clearer path from scheduling and screening to professional review and prevention guidance.</p>
            <ul className="tw6-checks">
              <li><UsersRound size={18} /><span><strong>Patient-first access</strong><small>Patients get their own secure portal rather than sharing the staff workspace.</small></span></li>
              <li><ScanSearch size={18} /><span><strong>AI-assisted screening</strong><small>Dental image findings can support a professional review workflow.</small></span></li>
              <li><Stethoscope size={18} /><span><strong>Professional judgment</strong><small>The system does not replace a qualified dental professional.</small></span></li>
            </ul>
            <button className="tw6-btn tw6-btn-primary" onClick={() => navigate('/patient-portal')}>Explore ToothWise <ArrowRight size={16} /></button>
          </div>
        </Reveal>

        <Reveal as="section" className="tw6-flow">
          <div className="tw6-section-head">
            <h2>A clear path from your first visit to the next step.</h2>
            <p>ToothWise keeps the digital side of care organized so patients can focus on the visit and the clinic can focus on care.</p>
          </div>
          <ol className="tw6-steps">
            {STEPS.map(({ icon: Icon, title, text }) => (
              <li key={title}>
                <span className="tw6-step-dot"><Icon size={17} /></span>
                <h3>{title}</h3>
                <p>{text}</p>
              </li>
            ))}
          </ol>
        </Reveal>

        <Reveal as="section" className="tw6-services" id="services">
          <div className="tw6-section-head tw6-section-head-center">
            <h2>A broad range of dental services, clearly presented.</h2>
            <p>Swipe or tap through the services below, and contact the clinic when you are ready.</p>
          </div>
          <div className="tw6-services-layout">
            <ServiceCarousel services={SERVICES} onAskAbout={(event) => scrollToSection(event, 'find-us')} />
          </div>
        </Reveal>

        <Reveal as="section" className="tw6-prevention">
          <div className="tw6-prevention-inner">
            <span className="tw6-prevention-mark"><Sparkles size={22} /></span>
            <h2>Keep your next dental-care step easy to find.</h2>
            <p>Use ToothWise for patient access and screening support, while routine prevention and treatment remain guided by dental professionals.</p>
            <button className="tw6-btn tw6-btn-light" onClick={() => navigate('/patient-portal')}>Get started <ArrowRight size={17} /></button>
          </div>
        </Reveal>

        <Reveal as="section" className="tw6-faq-wrap" id="faq">
          <div className="tw6-faq-head">
            <h2>Know what to expect before using ToothWise.</h2>
            <p>For general questions, the AI assistant is available from the corner of the page. Patient-specific information stays inside the secure portal.</p>
            <button className="tw6-btn tw6-btn-ghost" onClick={() => document.querySelector('.chat-fab')?.click()}><MessageCircle size={16} /> Ask the assistant</button>
          </div>
          <div className="tw6-faq-list">{FAQS.map(([question, answer]) => <FAQItem key={question} question={question} answer={answer} />)}</div>
        </Reveal>

        <Reveal as="section" className="tw6-find" id="find-us">
          <div className="tw6-find-copy">
            <h2>Come in, ask questions, and keep your care moving.</h2>
            <p>Visit the clinic in Ermita, Manila, or contact the team directly for appointment and service information.</p>
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
            <div className="tw6-map-head"><div><strong>CodiSmile Dental Clinic</strong><span>Clinic location</span></div><a href={directionsUrl} target="_blank" rel="noreferrer" aria-label="Open CodiSmile in Google Maps"><LocateFixed size={18} /></a></div>
            <div className="tw6-map-frame">
              <iframe title="CodiSmile Dental Clinic map" src={mapEmbed} loading="lazy" referrerPolicy="no-referrer-when-downgrade" />
            </div>
            <a className="tw6-map-open" href={directionsUrl} target="_blank" rel="noreferrer">Open in Google Maps <ArrowUpRight size={15} /></a>
          </div>
        </Reveal>
      </main>

      <footer className="tw6-footer">
        <div className="tw6-footer-top">
          <div className="tw6-footer-brand">
            <picture><source type="image/webp" srcSet="/codismile/codismile-logo-96.webp 1x, /codismile/codismile-logo-192.webp 2x" /><img src="/codismile/codismile-logo-96.png" srcSet="/codismile/codismile-logo-96.png 1x, /codismile/codismile-logo-192.png 2x" width="40" height="40" alt="" /></picture>
            <div>
              <strong>ToothWise</strong>
              <span>AI-assisted dental screening and patient workflow for {CLINIC.name}.</span>
            </div>
          </div>
          <button type="button" className="tw6-footer-cta" onClick={() => navigate('/patient-portal')}>
            Open Patient Portal <ArrowRight size={15} />
          </button>
        </div>

        <div className="tw6-footer-grid">
          <div className="tw6-footer-col">
            <span>Visit</span>
            <p>{CLINIC.address}</p>
            <a target="_blank" rel="noreferrer" href={directionsUrl}>Get directions <ArrowUpRight size={12} /></a>
          </div>
          <div className="tw6-footer-col">
            <span>Contact</span>
            <a href={phoneHref}>{CLINIC.phone}</a>
            <p>Mon–Sat 9:00 AM–5:00 PM<br />Sun 9:00 AM–2:00 PM</p>
          </div>
          <div className="tw6-footer-col tw6-footer-nav">
            <span>Explore</span>
            <button type="button" onClick={(event) => scrollToSection(event, 'toothwise')}>ToothWise</button>
            <button type="button" onClick={(event) => scrollToSection(event, 'services')}>Services</button>
            <button type="button" onClick={(event) => scrollToSection(event, 'faq')}>FAQ</button>
            <button type="button" onClick={(event) => scrollToSection(event, 'find-us')}>Find us</button>
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
