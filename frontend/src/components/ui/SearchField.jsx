import React, { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import PropTypes from 'prop-types';
import { Search, X } from 'lucide-react';

/**
 * SearchField — search box with a clear button, Esc-to-clear and a global
 * "/" shortcut that focuses it (ignored while typing in another field).
 */
const SearchField = forwardRef(({ id, label, value, onChange, placeholder, shortcut = true }, ref) => {
  const inputRef = useRef(null);
  useImperativeHandle(ref, () => inputRef.current);

  useEffect(() => {
    if (!shortcut) return undefined;
    const onKey = (e) => {
      const tag = document.activeElement?.tagName;
      if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey
        && tag !== 'INPUT' && tag !== 'TEXTAREA' && tag !== 'SELECT'
        && !document.querySelector('[aria-modal="true"]')) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [shortcut]);

  const clear = () => { onChange(''); inputRef.current?.focus(); };

  return (
    <div className="tw-search" role="search">
      <Search size={16} className="tw-search__icon" aria-hidden="true" />
      <label htmlFor={id} className="sr-only">{label}</label>
      <input
        id={id}
        ref={inputRef}
        type="search"
        className="tw-search__input"
        placeholder={placeholder}
        value={value}
        onChange={e => onChange(e.target.value)}
        onKeyDown={e => { if (e.key === 'Escape' && value) { e.preventDefault(); onChange(''); } }}
        autoComplete="off"
      />
      {value ? (
        <button type="button" className="tw-search__clear" onClick={clear} aria-label="Clear search">
          <X size={15} aria-hidden="true" />
        </button>
      ) : (
        shortcut && <kbd className="tw-search__kbd" aria-hidden="true">/</kbd>
      )}
    </div>
  );
});

SearchField.displayName = 'SearchField';

SearchField.propTypes = {
  id: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  placeholder: PropTypes.string,
  shortcut: PropTypes.bool,
};

export default SearchField;
