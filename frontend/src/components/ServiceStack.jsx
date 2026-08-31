import { useRef, useState } from 'react';
import { ArrowLeft, ArrowRight } from 'lucide-react';

const SWIPE_THRESHOLD = 70;

export default function ServiceStack({ cards, onAskAbout }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [dragX, setDragX] = useState(0);
  const [dragging, setDragging] = useState(false);
  const startXRef = useRef(0);
  const pointerIdRef = useRef(null);

  const count = cards.length;
  const goTo = (index) => setActiveIndex(((index % count) + count) % count);
  const next = () => goTo(activeIndex + 1);
  const prev = () => goTo(activeIndex - 1);

  function handlePointerDown(event) {
    startXRef.current = event.clientX;
    pointerIdRef.current = event.pointerId;
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(true);
  }

  function handlePointerMove(event) {
    if (!dragging || event.pointerId !== pointerIdRef.current) return;
    setDragX(event.clientX - startXRef.current);
  }

  function endDrag(event) {
    if (!dragging || event.pointerId !== pointerIdRef.current) return;
    if (dragX <= -SWIPE_THRESHOLD) next();
    else if (dragX >= SWIPE_THRESHOLD) prev();
    setDragging(false);
    setDragX(0);
    pointerIdRef.current = null;
  }

  function handleKeyDown(event) {
    if (event.key === 'ArrowRight') { event.preventDefault(); next(); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); prev(); }
  }

  return (
    <div className="tw-stack-wrap">
      <div
        className="tw-stack"
        role="group"
        aria-roledescription="carousel"
        aria-label="Service categories"
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        {cards.map((card, index) => {
          let offset = index - activeIndex;
          if (offset < 0) offset += count;
          if (offset > 2) return null;

          const isTop = offset === 0;
          const dragRotate = isTop ? dragX / 22 : 0;
          const dragTranslate = isTop ? dragX : 0;
          const style = isTop
            ? {
                transform: `translateX(${dragTranslate}px) rotate(${dragRotate}deg)`,
                transition: dragging ? 'none' : undefined,
                opacity: 1 - Math.min(Math.abs(dragX) / 340, 0.5),
              }
            : {
                transform: `translateY(${offset * 14}px) scale(${1 - offset * 0.05})`,
                zIndex: 10 - offset,
              };

          return (
            <article
              key={card.title}
              className={`tw-stack-card${isTop ? ' is-top' : ''}`}
              style={style}
              onPointerDown={isTop ? handlePointerDown : undefined}
              onPointerMove={isTop ? handlePointerMove : undefined}
              onPointerUp={isTop ? endDrag : undefined}
              onPointerCancel={isTop ? endDrag : undefined}
              aria-hidden={!isTop}
            >
              <div className="tw-stack-card-art">
                <img src={card.image} alt={card.title} draggable={false} />
                <div className="tw-stack-card-badge" style={{ background: card.gradient }}>
                  <card.icon size={16} />
                </div>
              </div>
              <div className="tw-stack-card-body">
                <span>{card.eyebrow}</span>
                <h3>{card.title}</h3>
                <p>{card.blurb}</p>
                <ul>
                  {card.items.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
              {isTop && (
                <button type="button" className="tw-stack-card-cta" onClick={onAskAbout}>
                  Ask about this <ArrowRight size={14} />
                </button>
              )}
            </article>
          );
        })}
      </div>

      <div className="tw-stack-controls">
        <button type="button" onClick={prev} aria-label="Previous service category"><ArrowLeft size={17} /></button>
        <div className="tw-stack-dots">
          {cards.map((card, index) => (
            <button
              key={card.title}
              type="button"
              className={index === activeIndex ? 'is-active' : ''}
              aria-label={`Show ${card.title}`}
              onClick={() => goTo(index)}
            />
          ))}
        </div>
        <button type="button" onClick={next} aria-label="Next service category"><ArrowRight size={17} /></button>
      </div>
      <p className="tw-stack-hint">Swipe, drag, or use the arrows to browse.</p>
    </div>
  );
}
