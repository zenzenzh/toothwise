import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpRight, MessageCircle, Phone, Send, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { chatbotAPI, patientScreeningsAPI } from '../api';
import LogoMark from './LogoMark';
import { answerPatientQuestion } from '../utils/screeningAssistant';

const CLINIC_PHONE = '+63 956 196 5325';
const QUICK_PROMPTS = [
  'What are your clinic hours?',
  'What services do you offer?',
  'How does ToothWise AI screening work?',
];
const PATIENT_QUICK_PROMPTS = [
  'What did my last screening find?',
  "What's my current risk level?",
  'What should I do next?',
];

const INITIAL_MESSAGE = {
  from: 'bot',
  text: 'Hi! I’m the ToothWise AI Assistant. I can answer general questions about CodiSmile, dental care, and how ToothWise works.',
};

/**
 * `patient` (optional): when the logged-in patient is passed in, this
 * widget also loads that patient's own screening history (already-
 * authenticated data the portal itself shows) and answers questions about
 * it locally, entirely in the browser - see utils/screeningAssistant.js
 * for why that lookup never goes over the network. Anything it doesn't
 * recognize as a screening question still falls back to the same general
 * clinic assistant used when logged out.
 */
export default function ChatWidget({ patient } = {}) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [screenings, setScreenings] = useState([]);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!patient) return;
    patientScreeningsAPI.mine().then(r => setScreenings(r.data)).catch(() => setScreenings([]));
  }, [patient]);

  // Reset to the right greeting if the patient logs in/out while the
  // widget instance is still mounted (it lives above the auth branch).
  useEffect(() => {
    setMessages([patient ? {
      from: 'bot',
      text: `Hi ${patient.full_name.split(' ')[0]}! Ask me about your screening history and risk level, or any general dental question.`,
    } : INITIAL_MESSAGE]);
  }, [patient]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    window.setTimeout(() => inputRef.current?.focus(), 0);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open]);

  // Lets other parts of the patient portal (e.g. a "Ask about your
  // results" button on the dashboard) open this same widget instead of
  // duplicating a second chat UI.
  useEffect(() => {
    const onOpenRequest = () => setOpen(true);
    window.addEventListener('tw-open-chat', onOpenRequest);
    return () => window.removeEventListener('tw-open-chat', onOpenRequest);
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, typing]);

  async function sendMessage(rawText) {
    const text = rawText.trim();
    if (!text || typing) return;

    setInput('');
    const userMessage = { from: 'user', text };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);

    if (patient) {
      const localAnswer = answerPatientQuestion(text, screenings);
      if (localAnswer) {
        setMessages(current => [...current, { from: 'bot', text: localAnswer }]);
        return;
      }
    }

    setTyping(true);
    try {
      const response = await chatbotAPI.chat(text, messages);
      setMessages(current => [...current, { from: 'bot', text: response.data.reply }]);
    } catch (error) {
      const status = error.response?.status;
      const detail = error.response?.data?.detail;
      const fallback = status === 429
        ? 'The free AI quota is temporarily busy. Please try again shortly or call the clinic.'
        : detail || 'I’m having trouble connecting right now. You can call CodiSmile directly for help.';
      setMessages(current => [...current, { from: 'bot', text: fallback }]);
      if (status !== 429) toast.error('AI assistant is temporarily unavailable.');
    } finally {
      setTyping(false);
    }
  }

  function send(e) {
    e.preventDefault();
    sendMessage(input);
  }

  const quickPrompts = patient ? PATIENT_QUICK_PROMPTS : QUICK_PROMPTS;

  return (
    <div className="chat-widget-root">
      {open && <div
        className="chat-panel chat-panel-open"
        role="dialog"
        aria-label="ToothWise AI Assistant"
        aria-modal="false"
      >
        <div className="chat-panel-header">
          <div className="chat-brand-row">
            <div className="chat-avatar"><img src="/codismile/codismile-logo-96.png" srcSet="/codismile/codismile-logo-96.png 1x, /codismile/codismile-logo-192.png 2x" alt="" width="42" height="42" /></div>
            <div>
              <strong>ToothWise Assistant</strong>
              <span className="chat-status"><span className="chat-status-dot" aria-hidden="true" /> Online · {patient ? 'your screenings and general info' : 'general clinic questions'}</span>
            </div>
          </div>
          <button className="chat-close" aria-label="Close chat" onClick={() => setOpen(false)}><X size={18} /></button>
        </div>

        <div className="chat-panel-body" ref={scrollRef} aria-live="polite" aria-label="Conversation">
          {messages.map((message, index) => (
            <div key={`${message.from}-${index}`} className={`chat-message chat-message-${message.from}`}>
              {message.from === 'bot' && <div className="chat-message-icon"><LogoMark size={18} /></div>}
              <div className="chat-bubble">{message.text}</div>
            </div>
          ))}
          {messages.length === 1 && !typing && (
            <div className="chat-quick-prompts">
              {quickPrompts.map(prompt => (
                <button key={prompt} onClick={() => sendMessage(prompt)}>{prompt}<ArrowUpRight size={16} aria-hidden="true" /></button>
              ))}
            </div>
          )}
          {typing && (
            <div className="chat-message chat-message-bot">
              <div className="chat-message-icon"><LogoMark size={18} /></div>
              <div className="chat-bubble chat-typing" aria-label="Assistant is typing"><span /><span /><span /></div>
            </div>
          )}
        </div>

        <div className="chat-composer">
          <form className="chat-panel-input" onSubmit={send}>
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder={patient ? 'Ask about your screenings…' : 'Ask a question…'}
              maxLength={1200}
              aria-label="Type a message"
            />
            <button type="submit" aria-label="Send message" disabled={!input.trim() || typing}>
              <Send size={17} />
            </button>
          </form>
          <p className="chat-privacy-note">{patient
            ? 'Questions about your own screenings are answered on this device only, never sent to the AI provider.'
            : 'Please don’t share passwords, patient IDs, records, or private health information.'}</p>
          <div className="chat-panel-footer">
            <a href={`tel:${CLINIC_PHONE.replace(/\s/g, '')}`}><Phone size={15} /> Call CodiSmile</a>
            {!patient && <button onClick={() => navigate('/patient-portal')}>Patient Portal <ArrowUpRight size={15} /></button>}
          </div>
        </div>
      </div>}

      <button
        className={open ? 'chat-fab is-open' : 'chat-fab'}
        onClick={() => setOpen(value => !value)}
        aria-label={open ? 'Close AI assistant' : 'Open AI assistant'}
        aria-expanded={open}
      >
        {open ? <X size={22} /> : <><MessageCircle size={22} /><span className="chat-fab-label">Ask ToothWise</span></>}
        {!open && <span className="chat-fab-ping" aria-hidden="true" />}
      </button>
    </div>
  );
}
