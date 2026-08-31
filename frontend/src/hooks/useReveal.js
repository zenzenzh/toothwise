import { useEffect, useRef, useState } from 'react';

export default function useReveal(options = {}) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  const { root = null, rootMargin = '0px 0px -8% 0px', threshold = 0.08 } = options;

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === 'undefined') {
      setVisible(true);
      return undefined;
    }

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setVisible(true);
        observer.disconnect();
      }
    }, { root, rootMargin, threshold });

    observer.observe(node);
    return () => observer.disconnect();
  }, [root, rootMargin, threshold]);

  return [ref, visible];
}
