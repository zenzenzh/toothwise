import { useEffect } from 'react';

const SITE_URL = process.env.REACT_APP_SITE_URL || window.location.origin;
const DEFAULT_IMAGE = `${SITE_URL}/social-share.svg`;

function upsertMeta(attribute, key, content) {
  if (!content) return;
  let node = document.head.querySelector(`meta[${attribute}="${key}"]`);
  if (!node) {
    node = document.createElement('meta');
    node.setAttribute(attribute, key);
    document.head.appendChild(node);
  }
  node.setAttribute('content', content);
}

function upsertLink(rel, href) {
  let node = document.head.querySelector(`link[rel="${rel}"]`);
  if (!node) {
    node = document.createElement('link');
    node.setAttribute('rel', rel);
    document.head.appendChild(node);
  }
  node.setAttribute('href', href);
}

export default function SEO({
  title,
  description,
  path = window.location.pathname,
  image = DEFAULT_IMAGE,
  noIndex = false,
  structuredData,
}) {
  useEffect(() => {
    document.title = title;
    upsertMeta('name', 'description', description);
    upsertMeta('name', 'robots', noIndex ? 'noindex,nofollow' : 'index,follow');
    upsertMeta('property', 'og:title', title);
    upsertMeta('property', 'og:description', description);
    upsertMeta('property', 'og:type', 'website');
    upsertMeta('property', 'og:url', `${SITE_URL}${path}`);
    upsertMeta('property', 'og:image', image);
    upsertMeta('name', 'twitter:card', 'summary_large_image');
    upsertMeta('name', 'twitter:title', title);
    upsertMeta('name', 'twitter:description', description);
    upsertMeta('name', 'twitter:image', image);
    upsertLink('canonical', `${SITE_URL}${path}`);

    const existing = document.getElementById('toothwise-structured-data');
    if (existing) existing.remove();

    if (structuredData) {
      const script = document.createElement('script');
      script.id = 'toothwise-structured-data';
      script.type = 'application/ld+json';
      script.textContent = JSON.stringify(structuredData);
      document.head.appendChild(script);
    }

    const measurementId = process.env.REACT_APP_GA_MEASUREMENT_ID;
    if (measurementId && !window.__TOOTHWISE_GA__) {
      window.__TOOTHWISE_GA__ = true;
      const script = document.createElement('script');
      script.async = true;
      script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`;
      document.head.appendChild(script);

      window.dataLayer = window.dataLayer || [];
      window.gtag = function gtag() { window.dataLayer.push(arguments); };
      window.gtag('js', new Date());
      window.gtag('config', measurementId, { anonymize_ip: true });
    }

    if (window.gtag && measurementId) {
      window.gtag('event', 'page_view', { page_path: path, page_title: title });
    }
  }, [title, description, path, image, noIndex, structuredData]);

  return null;
}
