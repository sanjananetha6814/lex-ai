import { useEffect, useRef, useState } from 'react'
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUpRight, AudioLines, Award, Bookmark, Briefcase, Building2, Calendar, Check, ChevronDown, CircleHelp, Clipboard, Clock, FileCheck2, FileSearch, FileText, Filter, Globe2, Heart, Info, Languages, LockKeyhole, MapPin, Menu, MessageCircle, Mic, Moon, MoreHorizontal, Phone, Plus, Scale, Search, Send, Settings, Shield, ShieldCheck, Sparkles, Star, Sun, ThumbsDown, ThumbsUp, Upload, UserRoundCheck, Video, X } from 'lucide-react'
import { askLegalQuestion, uploadAndAnalyzeDocument, loginUser, registerUser, fetchCurrentUser, logoutUser } from './services/mockApi.js'

const initialMessages = [
  { id: 1, role: 'user', text: 'What does an indemnity clause mean?' },
  { id: 2, role: 'assistant', title: 'Simple Explanation', text: 'An indemnity clause generally means that one party agrees to cover certain losses or damages suffered by another party.', explanation: 'An indemnity clause generally means that one party agrees to cover certain losses or damages suffered by another party.', implication: 'If something goes wrong and the clause applies, the responsible party may have to compensate the other party.', checks: ['Which events are covered?', 'Is there a cap on what you could owe?', 'Does it cover another party’s negligence?'], consult: 'Consider a lawyer if the clause is broad, unlimited, or shifts responsibility for another party’s actions to you.', sources: ['Indian Contract Act, 1872 · Sections 124–125 (example reference)', 'Your agreement · Indemnity section'], caveat: 'The exact meaning depends on your agreement and jurisdiction. This is general legal information, not legal advice.' },
]

export default function LexAI() {
  const [entered, enter] = useState(false)
  const [view, setView] = useState('home')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [dark, setDark] = useState(false)
  const [language, setLanguage] = useState('English')
  const [messages, setMessages] = useState(initialMessages)
  const [saved, setSaved] = useState([])
  const [toast, setToast] = useState('')
  const [thinking, setThinking] = useState(false)
  const [file, setFile] = useState(null)
  const [fileState, setFileState] = useState('idle')
  const [analysisData, setAnalysisData] = useState(null)
  const [voice, setVoice] = useState('idle')
  const [lawyersList, setLawyersList] = useState(directory)
  const [selectedLawyer, setSelectedLawyer] = useState(() => directory[0])
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const stored = window.sessionStorage?.getItem('lexai_user')
      if (stored) return JSON.parse(stored)
    } catch {}
    return {
      id: 1,
      email: 'alex.morgan@workspace.lexai',
      role: 'USER',
      profile: { full_name: 'Alex Morgan', city: 'Bengaluru' }
    }
  })
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const [authMode, setAuthMode] = useState('login')
  const notify = (message) => setToast(message)

  useEffect(() => {
    fetchCurrentUser().then(user => {
      if (user) setCurrentUser(user)
    })
  }, [])

  useEffect(() => {
    fetch(`${API_BASE}/lawyers`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          const transformed = data.map(transformBackendLawyer)
          setLawyersList(transformed)
          setSelectedLawyer(prev => {
            const found = transformed.find(l => l.id === prev?.id || l.name === prev?.name)
            return found || transformed[0]
          })
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => { if (!toast) return undefined; const timer = setTimeout(() => setToast(''), 2800); return () => clearTimeout(timer) }, [toast])
  const navigate = (next, lawyer = null) => { enter(true); if (lawyer) setSelectedLawyer(lawyer); setView(next); setMobileOpen(false) }
  const ask = async (question) => {
    if (!question.trim() || thinking) return
    enter(true); setView('chat'); setMessages((all) => [...all, { id: Date.now(), role: 'user', text: question.trim() }]); setThinking(true)
    try { const answer = await askLegalQuestion(question, language); setMessages((all) => [...all, answer]) } catch { notify('The response could not be generated. Please try again.') } finally { setThinking(false) }
  }
  const startVoice = () => {
    if (voice !== 'idle') return
    setVoice('listening'); notify('Listening… tell me your legal question.')
    setTimeout(() => { setVoice('transcribed'); notify('Heard: “What are my rights as a tenant?”'); setTimeout(() => { setVoice('idle'); ask('What are my rights as a tenant?') }, 500) }, 1500)
  }
  const upload = async (chosen) => {
    if (!chosen) return
    if (!['application/pdf', 'image/jpeg', 'image/png'].includes(chosen.type)) { notify('Choose a PDF, JPG or PNG document.'); return }
    setFile(chosen); setFileState('uploading')
    try {
      const result = await uploadAndAnalyzeDocument(chosen, (step) => setFileState(step))
      setAnalysisData(result)
      setFileState('done')
      notify('Document analysis is ready.')
    } catch {
      setFileState('error')
      notify('We could not analyze this file. Please try again.')
    }
  }
  const sample = async () => {
    const sampleBlob = new Blob(
      ["RENTAL LEASE AGREEMENT\nMonthly Rent: ₹18,500 payable on or before the 5th.\nSecurity Deposit: ₹50,000 returnable on vacation.\nTermination: Either party may terminate with 60 days written notice.\nIndemnity: Tenant shall indemnify and hold harmless the Landlord from liabilities, claims, and damages."],
      { type: "application/pdf" }
    )
    const sampleFile = new File([sampleBlob], "Rental_Agreement.pdf", { type: "application/pdf" })
    setFile(sampleFile); setFileState('uploading')
    try {
      const result = await uploadAndAnalyzeDocument(sampleFile, (step) => setFileState(step))
      setAnalysisData(result)
      setFileState('done')
      notify('Sample rental agreement analyzed.')
    } catch {
      setFileState('error')
      notify('Could not complete sample document analysis.')
    }
  }
  const toggleSaved = (answer) => { const exists = saved.some((item) => item.id === answer.id); setSaved((all) => exists ? all.filter((item) => item.id !== answer.id) : [answer, ...all]); notify(exists ? 'Removed from saved answers.' : 'Answer saved.') }
  const copy = async (answer) => { try { await navigator.clipboard.writeText(`${answer.explanation}\n\n${answer.implication}`); notify('Answer copied to clipboard.') } catch { notify('Clipboard is unavailable in this browser.') } }
  const regenerate = async () => {
    const latest = [...messages].reverse().find((item) => item.role === 'user')
    if (!latest || thinking) return
    setThinking(true)
    try {
      const answer = await askLegalQuestion(latest.text, language)
      setMessages((all) => [...all, answer])
    }
    catch { notify('Could not regenerate the answer. Please try again.') }
    finally { setThinking(false) }
  }

  const displayName = currentUser?.profile?.full_name || currentUser?.email?.split('@')[0] || 'Alex Morgan'
  const initials = displayName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'AM'
  const isDemo = currentUser?.email === 'alex.morgan@workspace.lexai'

  const handleLogout = () => {
    logoutUser()
    const demoUser = {
      id: 1,
      email: 'alex.morgan@workspace.lexai',
      role: 'USER',
      profile: { full_name: 'Alex Morgan', city: 'Bengaluru' }
    }
    setCurrentUser(demoUser)
    notify('Signed out. Returned to demo workspace.')
  }

  if (!entered) return <Landing enter={() => navigate('home')} demo={(question) => typeof question === 'string' && question.trim() ? ask(question) : navigate('chat')} />
  return <div className={`app product ${dark ? 'dark' : ''}`}>
    <aside className={`sidebar ${mobileOpen ? 'open' : ''}`}>
      <div className="brand-row"><button className="brand" onClick={() => navigate('home')}><span className="brand-icon"><Scale size={18} /></span><span>Lex<span>AI</span><small>LEGAL CLARITY, FOR ALL</small></span></button><button className="mobile-close icon-button" onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={17} /></button></div>
      <button className="new-chat" onClick={() => { setMessages([]); navigate('chat') }}><Plus size={16} /> New conversation <small>⌘ K</small></button>
      <span className="side-label">WORKSPACE</span>
      <nav>{[['home','Overview',MessageCircle],['chat','Chat',MessageCircle],['documents','Documents',FileText],['saved','Saved answers',Bookmark],['lawyers','Lawyer connect',UserRoundCheck]].map(([id,label,Icon]) => <button key={id} className={`side-link ${view === id || (id === 'lawyers' && (view === 'lawyer-profile' || view === 'consultation')) ? 'selected' : ''}`} onClick={() => navigate(id)}><Icon size={16} />{label}</button>)}</nav>
      <span className="side-label recent-label">RECENT</span><button className="recent-link" onClick={() => navigate('chat')}>● Indemnity clause, simply explained</button><button className="recent-link" onClick={() => navigate('chat')}>● Tenant rights and notice periods</button>
      <div className="side-bottom"><div className="side-privacy"><ShieldCheck size={16} /><span><strong>Your privacy matters</strong><small>Documents are processed securely</small></span></div><button className={`side-link ${view === 'settings' ? 'selected' : ''}`} onClick={() => navigate('settings')}><Settings size={16} />Settings</button><button className="user-mini" onClick={() => { setAuthMode('login'); setAuthModalOpen(true); }} title="Click to switch account or sign in"><i>{initials}</i><span><strong>{displayName}</strong><small>{currentUser?.role === 'LAWYER' ? 'Advocate Profile' : isDemo ? 'Demo Workspace' : 'Personal Workspace'}</small></span><MoreHorizontal size={17} /></button></div>
    </aside>
    {mobileOpen && <button className="scrim" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}
    <main className={`main-content main-shell view-${view}`}>
      <header className="topbar">
        <div className="topbar-inner">
          <button className="mobile-menu icon-button" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={18} /></button>
          <div className="crumb">
            <button className="crumb-btn" onClick={() => navigate('home')}>LexAI</button>
            <ArrowRight size={13} />
            {view === 'lawyer-profile' ? (
              <>
                <button className="crumb-btn" onClick={() => navigate('lawyers')}>Lawyer Connect</button>
                <ArrowRight size={13} />
                <strong>{selectedLawyer?.name || 'Lawyer Profile'}</strong>
              </>
            ) : view === 'consultation' ? (
              <>
                <button className="crumb-btn" onClick={() => navigate('lawyers')}>Lawyer Connect</button>
                <ArrowRight size={13} />
                <button className="crumb-btn" onClick={() => navigate('lawyer-profile', selectedLawyer)}>{selectedLawyer?.name || 'Profile'}</button>
                <ArrowRight size={13} />
                <strong>Request Consultation</strong>
              </>
            ) : (
              <strong>{({home:'Chat',chat:'Chat',documents:'Documents',saved:'Saved Answers',lawyers:'Lawyer Connect',settings:'Settings'})[view] || 'Lawyer Connect'}</strong>
            )}
          </div>
          <div className="top-actions">
            <button className="privacy-chip" onClick={() => navigate('settings')}><Shield size={14} /> Documents are private</button>
            <button className="icon-button theme" aria-label="Toggle color mode" onClick={() => setDark(!dark)}>{dark ? <Sun size={16} /> : <Moon size={16} />}</button>
            <button className="avatar-small" onClick={() => { setAuthMode('login'); setAuthModalOpen(true); }} aria-label="Account Settings & Authentication" title={`${displayName} (${currentUser?.email}) · Click to switch account`}>{initials}</button>
          </div>
        </div>
      </header>
      <div className="content" key={view}>
        {view === 'home' && <Home ask={ask} navigate={navigate} voice={voice} startVoice={startVoice} saved={saved} displayName={displayName} onOpenAuth={() => { setAuthMode('login'); setAuthModalOpen(true); }} />}
        {view === 'chat' && <Chat messages={messages} ask={ask} thinking={thinking} language={language} setLanguage={setLanguage} voice={voice} startVoice={startVoice} toggleSaved={toggleSaved} copy={copy} regenerate={regenerate} navigate={navigate} notify={notify} />}
        {view === 'documents' && <Documents file={file} fileState={fileState} analysisData={analysisData} upload={upload} sample={sample} ask={ask} onNavigate={navigate} />}
        {view === 'saved' && <Saved answers={saved} toggleSaved={toggleSaved} copy={copy} navigate={navigate} />}
        {view === 'lawyers' && <Lawyers lawyers={lawyersList} notify={notify} onViewProfile={(l) => navigate('lawyer-profile', l)} onRequestConsultation={(l) => navigate('consultation', l)} />}
        {view === 'lawyer-profile' && <LawyerProfile lawyer={selectedLawyer} onBack={() => navigate('lawyers')} onRequestConsultation={(l) => navigate('consultation', l)} />}
        {view === 'consultation' && <ConsultationRequest lawyer={selectedLawyer} onBack={() => navigate('lawyer-profile', selectedLawyer)} notify={notify} navigate={navigate} />}
        {view === 'settings' && <SettingsPage language={language} setLanguage={setLanguage} dark={dark} setDark={setDark} notify={notify} currentUser={currentUser} displayName={displayName} initials={initials} onOpenAuth={(mode = 'login') => { setAuthMode(mode); setAuthModalOpen(true); }} onLogout={handleLogout} />}
      </div>
      <footer className="app-disclaimer">LexAI provides legal information, not legal advice. AI complements professional lawyers rather than replacing them.</footer>
    </main>
    {toast && <div className="toast" role="status"><Check size={15} />{toast}</div>}
    <AuthModal
      isOpen={authModalOpen}
      onClose={() => setAuthModalOpen(false)}
      initialMode={authMode}
      onAuthSuccess={(user) => {
        setCurrentUser(user)
      }}
      notify={notify}
    />
  </div>
}

function Landing({ enter, demo }) {
  const [previewQuestion,setPreviewQuestion]=useState('')
  const submitPreview=(event)=>{event.preventDefault();if(previewQuestion.trim())demo(previewQuestion.trim())}
  const features = [[MessageCircle,'AI Legal Chatbot','Ask everyday legal questions and get a clear starting point.'],[FileSearch,'Document Analyzer','Find clauses, obligations and details that deserve a closer look.'],[AudioLines,'Voice Assistance','Speak naturally when typing is not the easiest way to ask.'],[Languages,'Multilingual Support','Get explanations in six languages, including regional languages.'],[LockKeyhole,'Privacy & Security','Documents are processed securely, with clear limits.'],[UserRoundCheck,'Lawyer Referral','Find a verified professional when a question needs individual advice.']]
  return <div className="landing"><header className="landing-nav"><a href="#top" className="landing-brand"><span className="brand-icon"><Scale size={18} /></span>Lex<span>AI</span></a><nav><a href="#features">Platform</a><a href="#how">How it works</a><a href="#trust">Our approach</a></nav><button onClick={enter}>Open LexAI <ArrowUpRight size={15} /></button></header>
    <section className="hero" id="top"><div className="hero-grid" /><div className="hero-copy"><span className="eyebrow"><Sparkles size={13} /> A clearer way through legal questions</span><h1>Understand the law.<br /><em>Make better decisions.</em></h1><p>AI-powered legal information, document analysis, and access to professional help — all in one place.</p><div className="hero-actions"><button className="primary" onClick={enter}>Try LexAI <ArrowRight size={16} /></button><a href="#how">See How It Works <ArrowDown size={15} /></a></div><small><ShieldCheck size={14} /> Legal information, with clear limits and human support.</small></div>
      <div className="demo-card"><div className="demo-head"><span><Scale size={14} /> LexAI</span><small><i /> READY TO HELP</small></div><div className="demo-file"><FileText size={18} /><span><strong>Rental_Agreement.pdf</strong><small>12 pages · Uploaded just now</small></span><Check size={15} /></div><div className="demo-user"><span>AM</span><div><small>YOU ASKED</small><p>Can my landlord increase my rent suddenly?</p></div></div><div className="demo-answer"><Scale size={16} /><div><small>LEXAI EXPLAINED</small><p>Your agreement lists rent at <b>₹18,500/month</b>. Whether it can change depends on the rent-increase clause and local law.</p><p>Check the notice requirements in your agreement. If the terms are unclear or disputed, consider asking a local lawyer to review them.</p><label><Check size={11} /> Plain-language summary</label></div></div><div className="demo-disclaimer"><ShieldCheck size={13} /> General information, not legal advice</div><form className="demo-composer" onSubmit={submitPreview}><input aria-label="Ask LexAI a follow-up question" value={previewQuestion} onChange={event=>setPreviewQuestion(event.target.value)} placeholder="Ask about a clause..." /><button aria-label="Send preview question" type="submit"><Send size={15}/></button></form><div className="float-note"><FileCheck2 size={16} /><span><b>Document analyzed</b><small>Key terms brought into focus</small></span></div></div>
      <div className="hero-foot"><span>BUILT FOR CLARITY</span><span>INFORMATION, NOT ADVICE</span><span>HUMAN HELP WHEN IT MATTERS</span></div></section>
    <section className="awareness section-wrap"><span className="kicker">A MORE INFORMED START</span><div className="awareness-grid"><h2>Legal language<br />shouldn’t be a barrier.</h2><div><p>People make important decisions every day without knowing what a document says or where to begin. LexAI makes legal information easier to approach, so the next step feels clearer.</p><button className="text-action" onClick={demo}>Explore the assistant <ArrowRight size={15} /></button></div></div><div className="benefit-grid">{['Make informed decisions','Understand complex language','Prepare for a lawyer conversation','Improve access to justice'].map((x,i)=><div key={x}><small>0{i+1}</small><b>{x}</b></div>)}</div></section>
    <section className="features section-wrap" id="features"><div className="feature-head"><div><span className="kicker">THE LEXAI PLATFORM</span><h2>One thoughtful place to<br />find your footing.</h2></div><p>Every feature helps you understand more, not make the decision for you.</p></div><div className="feature-grid">{features.map(([Icon,title,text],i)=><article key={title}><small>0{i+1}</small><span><Icon size={19} /></span><h3>{title}</h3><p>{text}</p><ArrowUpRight size={15} /></article>)}</div></section>
    <section className="workflow" id="how"><div className="section-wrap"><span className="kicker">A SIMPLE PATH FORWARD</span><div className="feature-head"><h2>Clarity, one step<br />at a time.</h2><p>From the first question to the next right conversation, LexAI keeps you oriented.</p></div><div className="steps">{[['ASK','Ask or upload','Start with a legal question or document.'],['ANALYZE','Request analyzed','LexAI identifies the relevant information and clauses.'],['EXPLAIN','Understand simply','Get a plain-language summary, details to check and sources.'],['CONNECT','Talk with a lawyer','Connect with a professional when your matter needs tailored advice.']].map(([n,t,d])=><article key={n}><small>{n}</small><h3>{t}</h3><p>{d}</p></article>)}</div></div></section>
    <section className="trust section-wrap" id="trust"><div className="trust-panel"><div><span className="kicker">TRUST THROUGH TRANSPARENCY</span><h2>Helpful by design.<br />Honest about its limits.</h2><p>LexAI provides legal information, not legal advice. It can help you get oriented, but it does not replace a lawyer who understands your circumstances and jurisdiction.</p><button className="dark-button" onClick={enter}>Try LexAI <ArrowRight size={15} /></button></div><div className="trust-list">{[['Private document processing','Designed with privacy in mind; avoid sharing unnecessary details',LockKeyhole],['Transparent AI limitations','Know what AI can and cannot tell you',Info],['Professional lawyer referral','Find tailored help when your matter needs it',Heart],['Accessible legal information','Plain-language explanations with sources to explore',Globe2]].map(([a,b,I])=><div key={a}><I size={17} /><span><b>{a}</b><small>{b}</small></span><Check size={14} /></div>)}</div></div><div className="impact"><div><b>24/7 Accessibility</b><small>Legal information when you need a place to start</small></div><div><b>Reduced Cost</b><small>Understand basics before deciding on a consultation</small></div><div><b>Better Awareness</b><small>Know which terms and questions matter</small></div><div><b>Simplified Language</b><small>Complex wording explained more clearly</small></div><div><b>Informed Decisions</b><small>Feel prepared to consider your next step</small></div><div><b>Access to Justice</b><small>More people can find information and support</small></div></div></section>
    <section className="future"><div className="section-wrap"><div><span className="kicker">WHERE WE’RE HEADED</span><h2>Access to justice is<br />a journey we build together.</h2></div><div className="future-grid">{[['Voice Assistant','Ask legal questions conversationally.'],['Regional Languages','Bring explanations into more local languages.'],['Mobile Apps','Reach LexAI wherever you are.'],['Case Tracking','Keep important milestones and updates together.'],['Government Portal Integration','Connect people with public legal resources.'],['AI Document Drafting','Help prepare clear document drafts for review.']].map(([title,text])=><article key={title}><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>
    <footer className="landing-footer"><b><Scale size={16} /> LexAI</b><p><strong>LexAI — Legal information, not legal advice.</strong> AI complements professional lawyers rather than replacing them.</p><small>© 2026 LexAI</small></footer>
  </div>
}

function SidebarIcon() { return <Scale size={17} /> }
function Home({ ask, navigate, voice, startVoice, saved, displayName }) {
  const [query, setQuery] = useState('')
  const send = (e) => { e.preventDefault(); if (query.trim()) { ask(query); setQuery('') } }
  const firstName = displayName ? displayName.split(' ')[0] : 'there'
  return (
    <div className="home-view">
      <div className="welcome">
        <div>
          <span className="kicker">WEDNESDAY, OCTOBER 14</span>
          <h1>Good afternoon, {firstName} <em>✳</em></h1>
          <p>How can LexAI help you today?</p>
          <small>Understand legal information in simple language.</small>
        </div>
        <div className="welcome-seal"><SidebarIcon /></div>
      </div>
      <form className="ask-box" onSubmit={send}>
        <div>
          <Sparkles size={16} />
          <textarea value={query} onChange={e => setQuery(e.target.value)} placeholder="Ask a legal question…" aria-label="Ask a legal question" onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) send(e) }} />
        </div>
        <footer>
          <div>
            <button type="button" onClick={() => navigate('documents')}><Upload size={14} /> Upload document</button>
            <button type="button" onClick={startVoice} className={voice === 'listening' ? 'listening' : ''}><Mic size={14} />{voice === 'listening' ? 'Listening…' : 'Voice question'}</button>
          </div>
          <button className="submit" disabled={!query.trim()}>Ask LexAI <Send size={14} /></button>
        </footer>
      </form>
      <div className="quiet-privacy"><ShieldCheck size={13} /> Your question stays in this private workspace <span>·</span> General legal information, not legal advice</div>
      <div className="actions-title">
        <div><span className="kicker">START WITH WHAT YOU NEED</span><h2>How can we help?</h2></div>
        <button onClick={() => navigate('chat')}>Open chat <ArrowRight size={13} /></button>
      </div>
      <div className="quick-grid">
        {[
          ['Understand a document', 'Rental agreements, notices, contracts', FileText, 'documents'],
          ['Ask a legal question', 'Get a straightforward explanation', CircleHelp, 'chat'],
          ['Check my rights', 'Explore general rights and duties', ShieldCheck, 'tenant'],
          ['Find a lawyer', 'Connect with a verified professional', UserRoundCheck, 'lawyers']
        ].map(([title, sub, Icon, to]) => (
          <button key={title} onClick={() => to === 'tenant' ? ask('What are my rights as a tenant?') : navigate(to)}>
            <span><Icon size={18} /></span>
            <div><b>{title}</b><small>{sub}</small></div>
            <ArrowRight size={15} />
          </button>
        ))}
      </div>
      <div className="home-bottom">
        <section className="recent-panel">
          <span className="kicker">PICK UP WHERE YOU LEFT OFF</span>
          <h2>Recent conversations</h2>
          <button onClick={() => navigate('chat')}>
            <Sparkles size={16} />
            <span><b>What does an indemnity clause mean?</b><small>Today · General information</small></span>
            <ArrowRight size={14} />
          </button>
          <button onClick={() => navigate('chat')}>
            <FileCheck2 size={16} />
            <span><b>Rental notice period explained</b><small>Yesterday · Tenant rights</small></span>
            <ArrowRight size={14} />
          </button>
        </section>
        <section className="mini-trust">
          <ShieldCheck size={17} />
          <span className="kicker">A NOTE ON TRUST</span>
          <h3>AI helps you get oriented.<br />Your judgment comes first.</h3>
          <p>Use LexAI to understand information and prepare questions. For advice on your circumstances, talk to a qualified lawyer.</p>
          <button onClick={() => navigate('settings')}>How we handle privacy <ArrowRight size={13} /></button>
        </section>
      </div>
      {saved.length > 0 && (
        <button className="saved-nudge" onClick={() => navigate('saved')}>
          <Bookmark size={14} />{saved.length} saved answers <ArrowRight size={13} />
        </button>
      )}
    </div>
  )
}

function Chat({ messages, ask, thinking, language, setLanguage, startVoice, toggleSaved, copy, regenerate, navigate, notify }) {
  const [query,setQuery]=useState(''),[sources,setSources]=useState({})
  const send=(e)=>{e.preventDefault();if(query.trim()){ask(query);setQuery('')}}
  return <div className="chat-view"><header className="page-head"><div><span className="kicker">YOUR LEGAL INFORMATION ASSISTANT</span><h1>Ask LexAI</h1><p>Clear explanations to help you understand what to look at next.</p></div><label className="select-control"><Globe2 size={14}/><select aria-label="Response language" value={language} onChange={e=>setLanguage(e.target.value)}>{['English','Hindi','Telugu','Tamil','Kannada','Marathi'].map(x=><option key={x}>{x}</option>)}</select><ChevronDown size={13}/></label></header><div className="messages">{messages.length===0&&<div className="chat-empty"><Sparkles size={22}/><h2>Start with a question</h2><p>Ask about a legal term, document or general right.</p><button onClick={()=>setQuery('What does an indemnity clause mean?')}>Explain indemnity</button></div>}{messages.map(m=>m.role==='user'?<div className="user-row" key={m.id}><p>{m.text}</p><span>AM</span></div>:<article className="answer" key={m.id}><span className="answer-avatar"><Scale size={16}/></span><div className="answer-content"><b>LexAI <small>GENERAL INFORMATION</small></b><section><h3><Sparkles size={14}/>{m.title||'Simple Explanation'}</h3><p>{m.explanation||m.text}</p></section><section><h3>What it means for you</h3><p>{m.implication}</p></section><section><h3>Important things to check</h3><ul>{m.checks?.map(x=><li key={x}>{x}</li>)}</ul></section><aside><Info size={15}/><p><b>When to consult a lawyer</b>{m.consult}</p></aside><small className="caveat"><ShieldCheck size={13}/>{m.caveat||'This is general legal information, not legal advice. The exact meaning depends on your agreement and jurisdiction.'}</small><div className="sources"><button onClick={()=>setSources({...sources,[m.id]:!sources[m.id]})}><FileText size={14}/> Sources ({m.sources?.length||0}) <ChevronDown size={13}/></button>{sources[m.id]&&<ul>{m.sources?.map(x=><li key={x}>{x}</li>)}</ul>}</div><div className="answer-actions"><div><button title="Copy answer" onClick={()=>copy(m)}><Clipboard size={14}/></button><button title="Regenerate" onClick={regenerate}><AudioLines size={14}/></button><button title="Save answer" onClick={()=>toggleSaved(m)}><Bookmark size={14}/></button></div><div><button title="Helpful" onClick={()=>notify('Thanks for your feedback.')}><ThumbsUp size={14}/></button><button title="Not helpful" onClick={()=>notify('Thanks for your feedback.')}><ThumbsDown size={14}/></button><button className="talk-lawyer" onClick={()=>navigate('lawyers')}>Talk to a lawyer <ArrowRight size={12}/></button></div></div></div></article>)}{thinking&&<div className="thinking"><span className="answer-avatar"><Scale size={15}/></span>Looking at your question <i/><i/><i/></div>}</div><form className="chat-composer" onSubmit={send}><textarea aria-label="Follow-up question" placeholder="Ask a follow-up question…" value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey)send(e)}}/><footer><button type="button" onClick={startVoice} title="Ask using your voice"><Mic size={15}/></button><small>Response in {language}</small><button className="send" disabled={!query.trim()} aria-label="Send question"><Send size={14}/></button></footer></form><p className="chat-disclaimer">LexAI provides legal information, not legal advice. AI complements professional lawyers rather than replacing them.</p></div>
}

function Documents({ file, fileState, analysisData, upload, sample, ask, onNavigate }) {
  const ref = useRef(null)
  const [drag, setDrag] = useState(false)
  return (
    <div className="documents-view">
      <header className="page-head">
        <div>
          <span className="kicker">DOCUMENT INTELLIGENCE</span>
          <h1>Understand your legal document</h1>
          <p>Bring important terms into focus, in clear everyday language.</p>
        </div>
        <span className="private-badge"><ShieldCheck size={13} /> Private workspace</span>
      </header>

      <input ref={ref} hidden type="file" accept="application/pdf,image/jpeg,image/png" onChange={e => upload(e.target.files[0])} />

      {fileState === 'idle' && (
        <div
          className={`upload-zone ${drag ? 'drag' : ''}`}
          onDragOver={e => { e.preventDefault(); setDrag(true) }}
          onDragLeave={() => setDrag(false)}
          onDrop={e => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files[0]) }}
        >
          <span><Upload size={20} /></span>
          <h2>Drop your PDF here or browse files</h2>
          <p>PDF, JPG or PNG · Up to 20 MB</p>
          <button className="primary browse" onClick={() => ref.current?.click()}>Browse files <ArrowRight size={14} /></button>
          <small>or</small>
          <button className="sample" onClick={sample}><FileText size={14} /> Try a sample rental agreement</button>
          <p className="safe-note">Your uploaded documents are processed securely. Avoid uploading information you do not want analyzed.</p>
        </div>
      )}

      {['uploading', 'processing', 'analyzing'].includes(fileState) && (
        <div className="processing">
          <span className="spinner" />
          <h2>
            {fileState === 'uploading' && 'Uploading document…'}
            {fileState === 'processing' && 'Scanning document & extracting text…'}
            {fileState === 'analyzing' && 'Analyzing legal clauses…'}
          </h2>
          <p>{file?.name} · {fileState === 'uploading' ? 'verifying file signature and size' : fileState === 'processing' ? 'reading text and chunking' : 'identifying risks and statutory obligations'}</p>
          <div>
            <b><Check size={13} /> {fileState === 'uploading' ? 'Uploading' : 'File uploaded'}</b>
            <span>{fileState === 'uploading' ? '○ Extraction queued' : <><Check size={13} /> Text extracted</>}</span>
            <span>{fileState === 'analyzing' ? <><i /> AI analyzing</> : '○ Analysis'}</span>
          </div>
        </div>
      )}

      {fileState === 'error' && (
        <div className="empty">
          <h2>We couldn’t analyze this file</h2>
          <p>Choose a PDF, JPG or PNG and try again.</p>
          <button onClick={() => ref.current?.click()}>Try a different document</button>
        </div>
      )}

      {fileState === 'done' && (
        <Analysis file={file} analysisData={analysisData} ask={ask} onNavigate={onNavigate} onReset={() => ref.current?.click()} />
      )}

      <div className="document-privacy">
        <ShieldCheck size={14} />
        <span><b>Your documents are private.</b> Processed securely. LexAI provides information, not legal advice.</span>
      </div>
    </div>
  )
}

function Analysis({ file, analysisData, ask, onNavigate, onReset }) {
  const fallbackClauses = [
    { clause: 'Payment terms', text: 'Monthly rent is listed as ₹18,500, with a security deposit equal to two months of rent.', level: 'Low', excerpt: 'Rent of ₹18,500 payable on or before the 5th day of each calendar month.' },
    { clause: 'Termination clause', text: 'Either party may end the agreement with 60 days’ written notice, subject to local law.', level: 'Needs attention', excerpt: 'Either party may terminate this agreement with 60 days prior written notice.' },
    { clause: 'Indemnity clause', text: 'This clause may require the tenant to compensate the landlord for certain losses. The covered events are not fully specific.', level: 'High attention', excerpt: 'Tenant shall indemnify and hold harmless the Landlord from all claims and losses.' }
  ]

  const rawClauses = analysisData?.clauses || []
  const clauses = rawClauses.length > 0 ? rawClauses.map(c => ({
    clause: c.clause,
    level: c.level || 'Low',
    text: c.explanation,
    excerpt: c.text
  })) : fallbackClauses

  const overallRisk = analysisData?.overall_risk || 'LOW'
  const summaryText = analysisData?.summary || 'This appears to be a residential rental agreement. It outlines rent, deposit, maintenance responsibilities and how either party can end the tenancy.'
  const unclearText = analysisData?.unclear_items || 'The agreement does not clearly state who handles urgent repairs. Confirm this in writing before signing.'

  return (
    <div className="analysis">
      <div className="analysis-heading">
        <div>
          <span className="success"><Check size={13} /> ANALYSIS COMPLETE</span>
          <h2>Document Analysis</h2>
          <p>A plain-language overview of the details to review.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {onReset && (
            <button className="link-btn" onClick={onReset} style={{ fontSize: '0.85rem', cursor: 'pointer' }}>
              Upload another
            </button>
          )}
          <span className="private-badge"><FileCheck2 size={14} /> Ready</span>
        </div>
      </div>

      <div className="file-info">
        <FileText size={18} />
        <span>
          <b>{file?.name || analysisData?.title || 'Rental_Agreement.pdf'}</b>
          <small>Text extracted · {clauses.length} key clauses identified</small>
        </span>
        <small style={{ fontWeight: 600 }}>{overallRisk} RISK</small>
      </div>

      <div className="summary">
        <span><Sparkles size={14} /> DOCUMENT SUMMARY</span>
        <p>{summaryText}</p>
        <div>
          <small><i className="low" /> Low</small>
          <small><i className="mid" /> Needs attention</small>
          <small><i className="high" /> High attention</small>
        </div>
      </div>

      <h3 className="clause-heading">Important clauses <small>{clauses.length} items to review</small></h3>
      {clauses.map((item) => (
        <article className="clause" key={item.clause}>
          <span className={`severity ${item.level.toLowerCase().replace(' ', '-')}`}>{item.level}</span>
          <h3>{item.clause}</h3>
          <small>Simple explanation</small>
          <p>{item.text}</p>
          {item.excerpt && (
            <div className="clause-excerpt" style={{ margin: '8px 0 12px', padding: '8px 12px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', borderLeft: '2px solid var(--border-soft, #444)', fontSize: '0.85rem', color: 'var(--text-muted, #aaa)', fontStyle: 'italic' }}>
              <span style={{ fontWeight: 600, display: 'block', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '2px', fontStyle: 'normal', color: 'var(--text-soft, #888)' }}>Document Text:</span>
              “{item.excerpt}”
            </div>
          )}
          <button onClick={() => ask(`Can you explain the ${item.clause.toLowerCase()} in my document?`)}>
            Ask LexAI about this clause <ArrowRight size={13} />
          </button>
        </article>
      ))}

      <div className="unclear">
        <Info size={15} />
        <p><b>Missing or unclear information</b>{unclearText}</p>
      </div>

      <div className="analysis-end">
        <small><ShieldCheck size={14} /> AI-generated overview, not legal advice. Local laws may change how terms apply.</small>
        <button className="primary" onClick={() => onNavigate('lawyers')}>Discuss with a lawyer <ArrowRight size={14} /></button>
      </div>
    </div>
  )
}

function Saved({answers,toggleSaved,copy,navigate}) { return <div className="saved-view"><header className="page-head"><div><span className="kicker">YOUR PERSONAL LIBRARY</span><h1>Saved answers</h1><p>Keep useful explanations close at hand.</p></div><span className="private-badge">{answers.length} saved</span></header>{answers.length===0?<div className="empty"><span><Bookmark size={19}/></span><h2>Your library is ready</h2><p>Save a helpful explanation from any chat and it will appear here.</p><button className="primary" onClick={()=>navigate('chat')}>Browse conversations <ArrowRight size={14}/></button></div>:<div className="saved-grid">{answers.map(a=><article key={a.id}><div><Bookmark size={14}/> Saved explanation <button onClick={()=>toggleSaved(a)} aria-label="Remove saved answer"><X size={15}/></button></div><h2>{a.text}</h2><p>{a.implication}</p><footer><button onClick={()=>copy(a)}>Copy <Clipboard size={13}/></button><button onClick={()=>navigate('chat')}>Open in chat <ArrowRight size={13}/></button></footer></article>)}</div>}</div> }

const directory = [
  Object.assign(['Ananya Rao','Property Law','11 years','Bengaluru','English · Kannada · Telugu','4.9','126','AR','sage'], {
    id: 'ananya-rao',
    name: 'Adv. Ananya Rao',
    specialty: 'Property Law',
    years: '11 years',
    city: 'Bengaluru',
    langs: 'English · Kannada · Telugu',
    rating: '4.9',
    reviews: '126',
    initials: 'AR',
    tone: 'sage',
    fee: '₹1,500',
    feeNumber: 1500,
    availability: 'Available Today',
    nextSlot: 'Today, 04:00 PM',
    barId: 'KAR/1429/2015',
    bio: 'Adv. Ananya Rao has over 11 years of experience in property conveyance, real estate title verification, landlord-tenant disputes, and RERA compliance across Karnataka. She has advised hundreds of individuals, tenants, and families on lease negotiation, tenancy rights, and property acquisition.',
    areas: ['Property Title Due Diligence', 'Rental & Lease Agreements', 'Landlord-Tenant Disputes', 'RERA Registrations & Appeals', 'Inheritance & Succession Deeds', 'Real Estate Conveyance'],
    qualifications: ['B.A. LL.B (Hons.), National Law School of India University (NLSIU)', 'LL.M in Real Estate & Urban Law', 'Enrolled Advocate, Bar Council of Karnataka (2015)'],
    experienceSummary: '11+ years active practice · 850+ agreements vetted · High resolution rate in tenant-owner disputes',
    slots: ['10:00 AM', '11:30 AM', '02:00 PM', '04:00 PM', '05:30 PM'],
    reviewsList: [
      { author: 'Pooja Sharma', rating: 5, date: 'Oct 2026', comment: 'Ananya identified two high-liability clauses in our lease agreement that saved us significant hassle and deposit deduction. Highly recommended!' },
      { author: 'Karthik V.', rating: 5, date: 'Sep 2026', comment: 'Extremely clear explanation of property mutation and partition documents. Prompt and practical advice.' }
    ]
  }),
  Object.assign(['Rohan Mehta','Consumer Law','8 years','Mumbai','English · Hindi · Marathi','4.8','94','RM','coral'], {
    id: 'rohan-mehta',
    name: 'Adv. Rohan Mehta',
    specialty: 'Consumer Law',
    years: '8 years',
    city: 'Mumbai',
    langs: 'English · Hindi · Marathi',
    rating: '4.8',
    reviews: '94',
    initials: 'RM',
    tone: 'coral',
    fee: '₹1,200',
    feeNumber: 1200,
    availability: 'Available Tomorrow',
    nextSlot: 'Tomorrow, 11:30 AM',
    barId: 'MAH/3820/2018',
    bio: 'Adv. Rohan Mehta focuses on consumer dispute resolution, defective service claims, e-commerce grievances, and unfair contract terms. He regularly represents consumers before District and State Consumer Disputes Redressal Commissions.',
    areas: ['Consumer Protection Act', 'E-Commerce & Online Fraud Claims', 'Unfair Contract Terms', 'Defective Products & Services', 'Insurance Claim Repudiations', 'Arbitration & Mediation'],
    qualifications: ['LL.B, Government Law College (GLC), Mumbai', 'Post Graduate Diploma in Cyber Law', 'Bar Council of Maharashtra & Goa (2018)'],
    experienceSummary: '8+ years representing consumers · 320+ successful consumer redressal cases · Special focus on digital services',
    slots: ['11:00 AM', '01:30 PM', '03:30 PM', '05:00 PM'],
    reviewsList: [
      { author: 'Vikram Joshi', rating: 5, date: 'Oct 2026', comment: 'Helped me draft a formal legal notice for an unfair e-commerce refund denial. The dispute was settled in 10 days!' },
      { author: 'Neha P.', rating: 4.8, date: 'Aug 2026', comment: 'Very patient and articulate. Explained consumer forum procedures in simple steps.' }
    ]
  }),
  Object.assign(['Farah Khan','Family Law','14 years','Hyderabad','English · Hindi · Telugu','5.0','203','FK','blue'], {
    id: 'farah-khan',
    name: 'Adv. Farah Khan',
    specialty: 'Family Law',
    years: '14 years',
    city: 'Hyderabad',
    langs: 'English · Hindi · Telugu',
    rating: '5.0',
    reviews: '203',
    initials: 'FK',
    tone: 'blue',
    fee: '₹1,800',
    feeNumber: 1800,
    availability: 'Available Today',
    nextSlot: 'Today, 05:00 PM',
    barId: 'TS/910/2012',
    bio: 'Adv. Farah Khan is an empathetic and seasoned advocate with 14 years of practice in family and civil matters, including marital settlement agreements, mutual divorce, child custody arrangements, and domestic maintenance rights.',
    areas: ['Mutual Consent Settlements', 'Child Custody & Guardianship', 'Maintenance & Alimony Claims', 'Pre-Marital Consultations', 'Domestic Violence Act Petitions', 'Family Property Settlements'],
    qualifications: ['B.A. LL.B, NALSAR University of Law, Hyderabad', 'Certified Family Mediator (ICMA)', 'Bar Council of Telangana & AP (2012)'],
    experienceSummary: '14 years in practice · 600+ family consultations · Emphasis on amicable mediation and dignity',
    slots: ['10:30 AM', '12:00 PM', '03:00 PM', '05:00 PM'],
    reviewsList: [
      { author: 'Sunita M.', rating: 5, date: 'Oct 2026', comment: 'Farah handled our consultation with exceptional grace and legal clarity. She clarified all custody and maintenance aspects.' },
      { author: 'Rahul K.', rating: 5, date: 'Sep 2026', comment: 'Objective, compassionate, and sharp legal acumen. Exactly what one needs in complex family situations.' }
    ]
  }),
  Object.assign(['Vikram Iyer','Corporate Law','9 years','Chennai','English · Tamil','4.9','81','VI','lilac'], {
    id: 'vikram-iyer',
    name: 'Adv. Vikram Iyer',
    specialty: 'Corporate Law',
    years: '9 years',
    city: 'Chennai',
    langs: 'English · Tamil',
    rating: '4.9',
    reviews: '81',
    initials: 'VI',
    tone: 'lilac',
    fee: '₹2,000',
    feeNumber: 2000,
    availability: 'Available Today',
    nextSlot: 'Today, 02:30 PM',
    barId: 'TN/2441/2017',
    bio: 'Adv. Vikram Iyer advises startups, founders, and MSMEs on commercial contract drafting, non-disclosure agreements (NDAs), founder agreements, intellectual property protection, and regulatory compliance.',
    areas: ['Commercial Contracts & MSAs', 'Non-Disclosure Agreements (NDAs)', 'Founders Agreements & ESOPs', 'Trademark & Copyright Filing', 'Vendor & Supplier Contracts', 'Company Incorporation & Governance'],
    qualifications: ['B.B.A. LL.B (Hons.), Tamil Nadu National Law University', 'Company Secretary (ICSI Executive)', 'Bar Council of Tamil Nadu (2017)'],
    experienceSummary: '9 years corporate advisory · 400+ commercial contracts reviewed · Legal counsel to 50+ startups',
    slots: ['11:30 AM', '02:30 PM', '04:30 PM', '06:00 PM'],
    reviewsList: [
      { author: 'Arun Balan', rating: 5, date: 'Oct 2026', comment: 'Reviewed our SaaS client MSA in detail. Flagged critical IP ownership risks we had overlooked completely.' },
      { author: 'Divya R.', rating: 4.9, date: 'Jul 2026', comment: 'Practical startup advice without unnecessary legal jargon. Highly recommended for commercial agreements.' }
    ]
  }),
  Object.assign(['Maya Singh','Criminal Law','12 years','Delhi','English · Hindi','4.9','117','MS','sage'], {
    id: 'maya-singh',
    name: 'Adv. Maya Singh',
    specialty: 'Criminal Law',
    years: '12 years',
    city: 'Delhi',
    langs: 'English · Hindi',
    rating: '4.9',
    reviews: '117',
    initials: 'MS',
    tone: 'sage',
    fee: '₹1,600',
    feeNumber: 1600,
    availability: 'Available Today',
    nextSlot: 'Today, 03:00 PM',
    barId: 'D/1892/2014',
    bio: 'Adv. Maya Singh is an advocate practicing before Delhi District Courts and the High Court of Delhi. She focuses on criminal defense advisory, bail applications, police complaint drafting, cybercrime defense, and anticipatory relief.',
    areas: ['Bail Applications & Anticipatory Bail', 'Cybercrime & Online Harassment', 'Cheque Bounce (Sec 138 NI Act)', 'Police Complaints & FIR Advisory', 'White Collar Offenses', 'Constitutional Writs'],
    qualifications: ['LL.B, Campus Law Centre, Faculty of Law, University of Delhi', 'Diploma in Cyber Laws & Forensics', 'Bar Council of Delhi (2014)'],
    experienceSummary: '12 years courtroom and defense advisory · 500+ bail & criminal matters handled',
    slots: ['10:00 AM', '01:00 PM', '03:00 PM', '05:30 PM'],
    reviewsList: [
      { author: 'Amit Saxena', rating: 5, date: 'Oct 2026', comment: 'Fast and reliable guidance during an urgent police inquiry matter. Adv. Maya was calm, decisive, and reassuring.' },
      { author: 'Tanya B.', rating: 4.9, date: 'Aug 2026', comment: 'Excellent guidance on a cyber extortion complaint. Guided us through reporting to the cyber cell step-by-step.' }
    ]
  })
]

const API_BASE = import.meta.env.VITE_API_URL || '/api'

function transformBackendLawyer(l) {
  const p = l.profile || {}
  const reviewsArr = (l.reviews || []).map(r => ({
    author: r.client_name,
    rating: r.rating,
    date: 'Verified Client',
    comment: r.comment
  }))

  return Object.assign([
    l.name,
    p.specialty || '',
    p.experience_years || '',
    l.city || '',
    p.languages || '',
    String(p.rating || 4.9),
    p.review_count || '120+',
    p.initials || 'AR',
    p.tone || 'sage'
  ], {
    id: l.id,
    name: l.name,
    email: l.email,
    phone: l.phone,
    specialty: p.specialty || '',
    years: p.experience_years || '',
    city: l.city || '',
    langs: p.languages || '',
    rating: String(p.rating || 4.9),
    reviews: p.review_count || '120+',
    initials: p.initials || 'AR',
    tone: p.tone || 'sage',
    fee: p.consultation_fee || '₹1,500',
    feeNumber: p.fee_number || 1500,
    availability: p.availability_status || 'Available Today',
    nextSlot: p.next_slot || 'Today at 4:00 PM',
    barId: l.bar_council_id || 'BAR/2015',
    bio: p.bio || '',
    areas: p.practice_areas || ['Property Law', 'Legal Notice', 'Tenancy Disputes'],
    qualifications: p.qualifications || ['LL.B, University Law College', 'State Bar Council Enrolment'],
    experienceSummary: p.practice_summary || '',
    slots: p.slots || ['10:00 AM', '11:30 AM', '02:00 PM', '04:00 PM', '05:30 PM'],
    reviewsList: reviewsArr.length > 0 ? reviewsArr : [
      { author: 'Verified Client', rating: 5, date: 'Recent', comment: 'Extremely helpful session. Resolved all questions in simple language.' }
    ]
  })
}

function Lawyers({ lawyers = directory, notify, onViewProfile, onRequestConsultation }) {
  const currentList = lawyers && lawyers.length > 0 ? lawyers : directory
  const [query, setQuery] = useState('')
  const [area, setArea] = useState('All areas')
  const areas = ['All areas', ...new Set(currentList.map(x => x.specialty || x[1]))]
  const filtered = currentList.filter(x => {
    const text = [x.name || x[0], x.specialty || x[1], x.city || x[3], x.langs || x[4], x.bio || ''].join(' ').toLowerCase()
    return text.includes(query.toLowerCase()) && (area === 'All areas' || (x.specialty || x[1]) === area)
  })

  return (
    <div className="lawyers-view">
      <header className="page-head">
        <div>
          <span className="kicker">HUMAN EXPERTISE, WHEN IT MATTERS</span>
          <h1>Need professional legal help?</h1>
          <p>Complex situations deserve advice from someone who understands your circumstances.</p>
        </div>
        <span className="private-badge"><UserRoundCheck size={14} /> Verified professionals</span>
      </header>

      <div className="lawyer-search">
        <label>
          <Search size={15} />
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search by name, location or language" />
        </label>
        <label>
          <Filter size={14} />
          <select value={area} onChange={e => setArea(e.target.value)}>
            {areas.map(x => <option key={x}>{x}</option>)}
          </select>
          <ChevronDown size={13} />
        </label>
      </div>

      <div className="lawyer-grid">
        {filtered.map(l => (
          <article className="lawyer-card" key={l[0]}>
            <div className="lawyer-head">
              <span className={`lawyer-avatar ${l.tone || l[8]}`}>{l.initials || l[7]}</span>
              <div className="lawyer-head-badges">
                <span className="card-fee-tag">{l.fee || '₹1,500'}</span>
                <small><Check size={11} /> Verified</small>
              </div>
            </div>
            <h2>{l.name || l[0]}</h2>
            <p>{l.specialty || l[1]}</p>
            <div className="rating">
              <Star size={13} fill="currentColor" />
              <b>{l.rating || l[5]}</b>
              <span>({l.reviews || l[6]} reviews)</span>
              <i />
              {l.years || l[2]}
            </div>
            <small className="lawyer-meta"><MapPin size={12} /> {l.city || l[3]}</small>
            <small className="lawyer-meta"><Globe2 size={12} /> {l.langs || l[4]}</small>
            <div className="lawyer-avail-note">
              <Clock size={11} /> {l.availability || 'Available Today'}
            </div>
            <footer>
              <button type="button" onClick={() => onViewProfile ? onViewProfile(l) : notify(`${l[0]}’s profile is ready to view.`)}>View profile</button>
              <button type="button" onClick={() => onRequestConsultation ? onRequestConsultation(l) : notify(`Consultation request started with ${l[0]}.`)}>Request consultation <ArrowRight size={13} /></button>
            </footer>
          </article>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="empty">
          <h2>No lawyers match this search</h2>
          <p>Try another name, area, location or language.</p>
        </div>
      )}

      <div className="referral-note">
        <Heart size={15} />
        <span><b>LexAI refers complex matters to professionals.</b> Availability and fees are agreed directly with the lawyer.</span>
      </div>
    </div>
  )
}

function LawyerProfile({ lawyer, onBack, onRequestConsultation }) {
  const initial = lawyer || directory[0]
  const [fetchedProfile, setFetchedProfile] = useState(null)

  useEffect(() => {
    if (!lawyer?.id) return
    let active = true
    fetch(`${API_BASE}/lawyers/${lawyer.id}`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data && active) setFetchedProfile(transformBackendLawyer(data))
      })
      .catch(() => {})
    return () => { active = false }
  }, [lawyer?.id])

  const currentLawyer = (fetchedProfile && fetchedProfile.id === lawyer?.id) ? fetchedProfile : initial

  return (
    <div className="lawyer-profile-view">
      <button className="back-nav-btn" onClick={onBack}>
        <ArrowLeft size={15} /> Back to all lawyers
      </button>

      <div className="profile-hero-card">
        <div className="profile-hero-main">
          <span className={`profile-avatar ${currentLawyer.tone || 'sage'}`}>
            {currentLawyer.initials || 'AR'}
          </span>
          <div className="profile-hero-info">
            <div className="profile-badge-row">
              <span className="bar-verified-chip"><Check size={12} /> Bar Verified Advocate</span>
              <span className="bar-id-chip"><Award size={12} /> Reg: {currentLawyer.barId || 'BAR/2015'}</span>
            </div>
            <h1>{currentLawyer.name || currentLawyer[0]}</h1>
            <p className="profile-specialty"><Briefcase size={15} /> {currentLawyer.specialty || currentLawyer[1]} · {currentLawyer.years || currentLawyer[2]} Practice</p>
            <div className="profile-meta-chips">
              <span className="profile-meta-item"><MapPin size={13} /> {currentLawyer.city || currentLawyer[3]}</span>
              <span className="profile-meta-item"><Globe2 size={13} /> {currentLawyer.langs || currentLawyer[4]}</span>
              <span className="profile-meta-item rating">
                <Star size={13} fill="currentColor" />
                <b>{currentLawyer.rating || currentLawyer[5]}</b>
                <span>({currentLawyer.reviews || currentLawyer[6]} client reviews)</span>
              </span>
            </div>
          </div>
        </div>

        <div className="profile-hero-action">
          <div className="fee-badge-big">
            {currentLawyer.fee || '₹1,500'}
            <small>per 30-min consultation</small>
          </div>
          <span className="avail-tag"><i /> {currentLawyer.availability || 'Available Today'}</span>
          <button className="primary hero-book-btn" onClick={() => onRequestConsultation(currentLawyer)}>
            Request Consultation <ArrowRight size={14} />
          </button>
        </div>
      </div>

      <div className="profile-layout">
        <div className="profile-main-col">
          <section className="profile-section-card">
            <h2><Briefcase size={17} /> Professional Overview</h2>
            <p className="profile-bio-text">{currentLawyer.bio || `${currentLawyer.name} is a dedicated legal advocate specializing in ${currentLawyer.specialty} with ${currentLawyer.years} of experience.`}</p>
            <div className="experience-highlight">
              <Award size={16} />
              <div>
                <b>Practice Highlights</b>
                <p>{currentLawyer.experienceSummary || 'Verified advocate with proven track record in advisory, agreement drafting, and dispute management.'}</p>
              </div>
            </div>
          </section>

          <section className="profile-section-card">
            <h2><Scale size={17} /> Areas of Practice</h2>
            <div className="practice-tags-grid">
              {(currentLawyer.areas || ['Legal Consultation', 'Document Review', 'Dispute Resolution', 'Drafting Notices']).map(area => (
                <span key={area} className="practice-tag-item">
                  <Check size={12} /> {area}
                </span>
              ))}
            </div>
          </section>

          <section className="profile-section-card">
            <h2><Award size={17} /> Qualifications & Bar Admissions</h2>
            <ul className="credentials-list">
              {(currentLawyer.qualifications || ['LL.B, University Law College', 'Enrolled Advocate with State Bar Council']).map(q => (
                <li key={q} className="credentials-item">
                  <Check size={14} />
                  <span>{q}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="profile-section-card">
            <h2><Star size={17} fill="currentColor" /> Client Feedback & Ratings</h2>
            <div className="reviews-summary-bar">
              <div className="rating-score">
                <b>{currentLawyer.rating || '4.9'}</b>
                <div className="stars-row">
                  {[...Array(5)].map((_, i) => <Star key={i} size={13} fill="currentColor" />)}
                </div>
                <span>Based on {currentLawyer.reviews || '120+'} verified client sessions</span>
              </div>
              <span className="satisfaction-badge">100% Verified Consultations</span>
            </div>
            <div className="reviews-list">
              {(currentLawyer.reviewsList || [
                { author: 'Verified Client', rating: 5, date: 'Recent', comment: 'Extremely helpful session. Resolved all questions in simple language.' }
              ]).map((rev, i) => (
                <div key={i} className="review-item">
                  <div className="review-header">
                    <b>{rev.author}</b>
                    <div className="review-stars">
                      <Star size={12} fill="currentColor" />
                      <span>{rev.rating}.0</span>
                      <span className="review-date">· {rev.date}</span>
                    </div>
                  </div>
                  <p>{rev.comment}</p>
                </div>
              ))}
            </div>
          </section>
        </div>

        <aside className="profile-side-col">
          <div className="sticky-consult-card">
            <h3>Schedule a Session</h3>
            <div className="consult-rate-box">
              <span>Standard Consultation</span>
              <b>{currentLawyer.fee || '₹1,500'}</b>
              <small>Fixed 30-minute private consultation</small>
            </div>
            <div className="consult-perks">
              <div className="consult-perk-item">
                <Clock size={14} />
                <span>Next Slot: <b>{currentLawyer.nextSlot || 'Today'}</b></span>
              </div>
              <div className="consult-perk-item">
                <Video size={14} />
                <span>Available via Video, Phone or Chamber</span>
              </div>
              <div className="consult-perk-item">
                <ShieldCheck size={14} />
                <span>Protected by Attorney-Client Privilege</span>
              </div>
            </div>
            <button className="primary full-width-btn" onClick={() => onRequestConsultation(currentLawyer)}>
              Request Consultation <ArrowRight size={14} />
            </button>
            <div className="guarantee-box">
              <small><ShieldCheck size={13} /> Direct connection with independent legal counsel. Consultation fees are settled directly with the advocate without hidden charges.</small>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

function ConsultationRequest({ lawyer, onBack, notify, navigate }) {
  const currentLawyer = lawyer || directory[0]
  const [todayStr] = useState(() => new Date().toISOString().split('T')[0])

  const [mode, setMode] = useState('video')
  const [date, setDate] = useState(() => new Date().toISOString().split('T')[0])
  const [slot, setSlot] = useState(currentLawyer.slots ? currentLawyer.slots[0] : '10:00 AM')
  const [issue, setIssue] = useState('')
  const [isUrgent, setIsUrgent] = useState(false)
  const [fullName, setFullName] = useState('Alex Morgan')
  const [email, setEmail] = useState('alex.morgan@workspace.lexai')
  const [phone, setPhone] = useState('+91 98765 43210')
  const [language, setLanguage] = useState(currentLawyer.langs ? currentLawyer.langs.split(' · ')[0] : 'English')
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [refId, setRefId] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!issue.trim()) {
      notify('Please describe your legal issue or question.')
      return
    }

    const lawyerIdNum = typeof currentLawyer.id === 'number'
      ? currentLawyer.id
      : currentLawyer.name?.includes('Ananya') ? 1
      : currentLawyer.name?.includes('Rohan') ? 2
      : currentLawyer.name?.includes('Farah') ? 3
      : currentLawyer.name?.includes('Vikram') ? 4
      : currentLawyer.name?.includes('Maya') ? 5
      : 1

    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/consultations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lawyer_id: lawyerIdNum,
          client_name: fullName.trim(),
          client_email: email.trim(),
          client_phone: phone.trim(),
          client_language: language,
          format: mode,
          scheduled_date: date,
          scheduled_slot: slot,
          issue_description: issue.trim(),
          is_urgent: isUrgent,
        })
      })

      if (res.ok) {
        const data = await res.json()
        setRefId(data.reference_no)
        setIsSubmitted(true)
        notify(`Consultation request confirmed with ${currentLawyer.name}!`)
      } else {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.message || 'Failed to submit')
      }
    } catch {
      const generatedRef = 'LEX-' + Math.floor(100000 + Math.random() * 900000)
      setRefId(generatedRef)
      setIsSubmitted(true)
      notify(`Consultation request confirmed with ${currentLawyer.name}!`)
    } finally {
      setSubmitting(false)
    }
  }

  if (isSubmitted) {
    return (
      <div className="confirmation-page-view">
        <div className="confirmation-card">
          <div className="confirmation-icon">
            <FileCheck2 size={36} />
          </div>
          <span className="kicker">CONSULTATION CONFIRMED</span>
          <h1>Request Successfully Submitted!</h1>
          <p className="confirmation-sub">Adv. {currentLawyer.name} has received your consultation booking and will confirm your session shortly.</p>

          <div className="reference-pill">
            Reference Number: <b>#{refId}</b>
          </div>

          <div className="booking-receipt-box">
            <div className="receipt-row">
              <span>Advocate</span>
              <b>{currentLawyer.name} ({currentLawyer.specialty})</b>
            </div>
            <div className="receipt-row">
              <span>Session Format</span>
              <b>{mode === 'video' ? 'Video Conference (Google Meet / Zoom)' : mode === 'phone' ? 'Phone Call' : 'In-Person Chamber Visit'}</b>
            </div>
            <div className="receipt-row">
              <span>Scheduled Date & Time</span>
              <b>{date} at {slot}</b>
            </div>
            <div className="receipt-row">
              <span>Client Name</span>
              <b>{fullName} ({phone})</b>
            </div>
            <div className="receipt-row fee-highlight">
              <span>Consultation Fee</span>
              <b>{currentLawyer.fee || '₹1,500'} (Payable directly to advocate)</b>
            </div>
          </div>

          <div className="confirmation-steps-box">
            <b>What happens next?</b>
            <ol>
              <li>Adv. {currentLawyer.name} will review your request and send calendar invite within 2 hours.</li>
              <li>You will receive an SMS and email notification with your private meeting link.</li>
              <li>Keep any relevant legal documents (contracts, notices, IDs) ready for the discussion.</li>
            </ol>
          </div>

          <div className="confirmation-actions">
            <button className="primary" onClick={() => navigate('lawyers')}>
              Back to Lawyers Directory <ArrowRight size={14} />
            </button>
            <button className="secondary-action" onClick={() => navigate('chat')}>
              Ask LexAI Another Question
            </button>
            <button className="secondary-action" onClick={() => navigate('home')}>
              Workspace Overview
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="consultation-view">
      <button className="back-nav-btn" onClick={onBack}>
        <ArrowLeft size={15} /> Back to {currentLawyer.name}
      </button>

      <header className="page-head">
        <div>
          <span className="kicker">CONFIDENTIAL LEGAL CONSULTATION</span>
          <h1>Schedule Consultation Session</h1>
          <p>Book a dedicated 30-minute private consultation with {currentLawyer.name}.</p>
        </div>
        <span className="private-badge"><ShieldCheck size={14} /> Attorney-Client Privilege</span>
      </header>

      <div className="consult-form-grid">
        <form className="booking-form-card" onSubmit={handleSubmit}>
          <div className="form-step-block">
            <label className="step-label">1. Choose Consultation Format</label>
            <div className="consult-mode-cards">
              <div className={`mode-card-option ${mode === 'video' ? 'active' : ''}`} onClick={() => setMode('video')}>
                <div className="mode-card-header">
                  <Video size={18} />
                  <b>Video Call</b>
                </div>
                <small>Secure Google Meet / Zoom link. Recommended for reviewing documents.</small>
              </div>

              <div className={`mode-card-option ${mode === 'phone' ? 'active' : ''}`} onClick={() => setMode('phone')}>
                <div className="mode-card-header">
                  <Phone size={18} />
                  <b>Phone Call</b>
                </div>
                <small>Lawyer calls your phone directly at scheduled time.</small>
              </div>

              <div className={`mode-card-option ${mode === 'in-person' ? 'active' : ''}`} onClick={() => setMode('in-person')}>
                <div className="mode-card-header">
                  <Building2 size={18} />
                  <b>In-Person Visit</b>
                </div>
                <small>Chamber meeting in {currentLawyer.city || 'Lawyer Chamber'}.</small>
              </div>
            </div>
          </div>

          <div className="form-step-block">
            <label className="step-label">2. Select Preferred Date & Time</label>
            <div className="date-time-picker-row">
              <label className="input-field-wrap">
                <span className="field-hint"><Calendar size={13} /> Preferred Date</span>
                <input
                  type="date"
                  value={date}
                  min={todayStr}
                  onChange={e => setDate(e.target.value)}
                  required
                />
              </label>
            </div>
            <span className="field-subhint">Available Time Slots for {date}:</span>
            <div className="slot-chips-grid">
              {(currentLawyer.slots || ['10:00 AM', '11:30 AM', '02:00 PM', '04:00 PM', '05:30 PM']).map(s => (
                <button
                  type="button"
                  key={s}
                  className={`slot-chip-btn ${slot === s ? 'active' : ''}`}
                  onClick={() => setSlot(s)}
                >
                  <Clock size={12} /> {s}
                </button>
              ))}
            </div>
          </div>

          <div className="form-step-block">
            <label className="step-label">3. Describe Your Legal Issue or Question *</label>
            <p className="field-desc">Provide brief context so Adv. {currentLawyer.name} can prepare relevant statutory references and advice.</p>
            <textarea
              rows={4}
              required
              value={issue}
              onChange={e => setIssue(e.target.value)}
              placeholder="E.g., I received a notice from my landlord asking for a sudden 25% rent hike with only 15 days notice. I want to understand my tenancy rights and respond formally..."
            />
            <label className="urgent-check-row">
              <input type="checkbox" checked={isUrgent} onChange={e => setIsUrgent(e.target.checked)} />
              <span><b>Urgent inquiry</b> — Matter involves an impending court date or deadline within 48 hours</span>
            </label>
          </div>

          <div className="form-step-block">
            <label className="step-label">4. Your Contact Details</label>
            <div className="form-row-2">
              <label className="input-field-wrap">
                <span className="field-hint">Full Name *</span>
                <input type="text" value={fullName} onChange={e => setFullName(e.target.value)} required />
              </label>
              <label className="input-field-wrap">
                <span className="field-hint">Email Address *</span>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
              </label>
            </div>
            <div className="form-row-2">
              <label className="input-field-wrap">
                <span className="field-hint">Phone Number *</span>
                <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} required />
              </label>
              <label className="input-field-wrap">
                <span className="field-hint">Preferred Discussion Language</span>
                <select value={language} onChange={e => setLanguage(e.target.value)}>
                  {(currentLawyer.langs ? currentLawyer.langs.split(' · ') : ['English']).map(lang => (
                    <option key={lang}>{lang}</option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          <div className="form-submit-row">
            <button type="submit" className="primary submit-booking-btn" disabled={submitting}>
              {submitting ? 'Confirming Request...' : `Confirm Request · ${currentLawyer.fee || '₹1,500'}`} <ArrowRight size={15} />
            </button>
            <small className="payment-disclaimer">
              No advance deduction today. The consultation fee of {currentLawyer.fee || '₹1,500'} is settled directly with the advocate upon confirmation.
            </small>
          </div>
        </form>

        <aside className="booking-summary-col">
          <div className="booking-summary-box">
            <h3>Selected Legal Counsel</h3>
            <div className="lawyer-summary-tile">
              <span className={`lawyer-avatar small ${currentLawyer.tone || 'sage'}`}>{currentLawyer.initials || 'AR'}</span>
              <div>
                <b>{currentLawyer.name}</b>
                <small>{currentLawyer.specialty} · {currentLawyer.city}</small>
                <div className="rating">
                  <Star size={11} fill="currentColor" />
                  <b>{currentLawyer.rating}</b>
                  <span>({currentLawyer.reviews} reviews)</span>
                </div>
              </div>
            </div>

            <div className="fee-breakdown-table">
              <h4>Fee Summary</h4>
              <div className="fee-row">
                <span>30-Min Consultation</span>
                <b>{currentLawyer.fee || '₹1,500'}</b>
              </div>
              <div className="fee-row">
                <span>Platform Facilitation</span>
                <b className="free-tag">FREE (LexAI Connect)</b>
              </div>
              <div className="fee-row total">
                <span>Total Fee</span>
                <b>{currentLawyer.fee || '₹1,500'}</b>
              </div>
            </div>

            <div className="booking-assurances">
              <div className="assurance-item">
                <ShieldCheck size={14} />
                <span><b>100% Confidential</b> Attorney-client privileged communication</span>
              </div>
              <div className="assurance-item">
                <Clock size={14} />
                <span><b>Fast Response</b> Advocate confirms appointment within 2 hours</span>
              </div>
              <div className="assurance-item">
                <FileCheck2 size={14} />
                <span><b>Verified Bar Counsel</b> Licensed & practicing advocate</span>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

function SettingsPage({ language, setLanguage, dark, setDark, notify, currentUser, displayName, initials, onOpenAuth, onLogout }) {
  const isDemo = currentUser?.email === 'alex.morgan@workspace.lexai'

  return (
    <div className="settings-view">
      <header className="page-head">
        <div>
          <span className="kicker">YOUR WORKSPACE</span>
          <h1>Settings</h1>
          <p>Set up LexAI to feel right for you.</p>
        </div>
      </header>

      <section className="settings-panel">
        <header>
          <b>Preferences</b>
          <small>Personalize your experience.</small>
        </header>
        <div>
          <Languages size={17} />
          <span>
            <b>Response language</b>
            <small>Choose the language for LexAI answers</small>
          </span>
          <select value={language} onChange={e => setLanguage(e.target.value)}>
            {['English', 'Hindi', 'Telugu', 'Tamil', 'Kannada', 'Marathi'].map(x => <option key={x}>{x}</option>)}
          </select>
        </div>
        <div>
          <Moon size={17} />
          <span>
            <b>Appearance</b>
            <small>Adjust how LexAI looks on this device</small>
          </span>
          <button className={`switch ${dark ? 'on' : ''}`} onClick={() => setDark(!dark)} role="switch" aria-checked={dark}>
            <i />
          </button>
        </div>
        <div>
          <ShieldCheck size={17} />
          <span>
            <b>Privacy & Security</b>
            <small>Documents are encrypted in transit and analyzed in a sandboxed session.</small>
          </span>
          <button className="link-btn" onClick={() => notify('Documents and queries are verified against Indian statutory codes and stored securely.')}>
            Review details <ArrowRight size={13} />
          </button>
        </div>
      </section>

      <div className="settings-disclaimer">
        <Info size={17} />
        <div>
          <b>How to use LexAI</b>
          <p>LexAI provides legal information, not legal advice. AI complements professional lawyers rather than replacing them. Do not rely on a generated answer for urgent court deadlines or high-stakes decisions.</p>
        </div>
      </div>

      <div className="settings-profile">
        <i>{initials || 'AM'}</i>
        <span>
          <b>{displayName || 'Alex Morgan'}</b>
          <small>{currentUser?.email} · {currentUser?.role === 'LAWYER' ? 'Advocate Profile' : isDemo ? 'Demo Workspace' : 'Personal Workspace'}</small>
        </span>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button onClick={() => onOpenAuth?.('login')}>
            {isDemo ? 'Sign In / Register' : 'Switch Account'}
          </button>
          {!isDemo && (
            <button className="link-btn" onClick={onLogout} style={{ color: '#c53030' }}>
              Sign Out
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function AuthModal({ isOpen, onClose, initialMode = 'login', onAuthSuccess, notify }) {
  const [mode, setMode] = useState(initialMode)
  const [prevInitialMode, setPrevInitialMode] = useState(initialMode)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState('USER')
  const [city, setCity] = useState('Bengaluru')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  if (prevInitialMode !== initialMode) {
    setPrevInitialMode(initialMode)
    setMode(initialMode)
    setError('')
  }

  if (!isOpen) return null

  const handleFillDemo = () => {
    setMode('login')
    setEmail('alex.morgan@workspace.lexai')
    setPassword('DemoUserPass123!')
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (mode === 'login') {
        const data = await loginUser(email, password)
        notify(`Welcome back, ${data.user?.profile?.full_name || data.user?.email}!`)
        onAuthSuccess(data.user)
        onClose()
      } else {
        const payload = {
          email,
          password,
          role,
          full_name: fullName,
          city
        }
        const data = await registerUser(payload)
        notify(`Account created successfully! Signed in as ${data.user?.profile?.full_name || data.user?.email}`)
        onAuthSuccess(data.user)
        onClose()
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="auth-card" onClick={e => e.stopPropagation()}>
        <div className="auth-header">
          <div>
            <span className="kicker">LEXAI IDENTITY</span>
            <h2>{mode === 'login' ? 'Sign in to LexAI' : 'Create an Account'}</h2>
          </div>
          <button className="close-btn" onClick={onClose} aria-label="Close authentication modal">
            <X size={18} />
          </button>
        </div>

        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => { setMode('login'); setError('') }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`auth-tab ${mode === 'register' ? 'active' : ''}`}
            onClick={() => { setMode('register'); setError('') }}
          >
            Create Account
          </button>
        </div>

        {error && (
          <div className="auth-error">
            <Info size={14} />
            <span>{error}</span>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === 'register' && (
            <>
              <div className="auth-field">
                <label>Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Adv. Rajesh Kumar"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                />
              </div>

              <div className="auth-role-picker-container" style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                <label style={{ fontSize: '11px', fontWeight: 600, color: 'var(--muted, #78857e)' }}>Account Role</label>
                <div className="auth-role-picker">
                  <button
                    type="button"
                    className={`auth-role-btn ${role === 'USER' ? 'active' : ''}`}
                    onClick={() => setRole('USER')}
                  >
                    <UserRoundCheck size={14} /> Individual / Client
                  </button>
                  <button
                    type="button"
                    className={`auth-role-btn ${role === 'LAWYER' ? 'active' : ''}`}
                    onClick={() => setRole('LAWYER')}
                  >
                    <Scale size={14} /> Legal Advocate
                  </button>
                </div>
              </div>

              <div className="auth-field">
                <label>City / Jurisdiction</label>
                <input
                  type="text"
                  placeholder="e.g. Bengaluru, Delhi, Mumbai"
                  value={city}
                  onChange={e => setCity(e.target.value)}
                />
              </div>
            </>
          )}

          <div className="auth-field">
            <label>Email Address</label>
            <input
              type="email"
              required
              placeholder="name@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
            />
          </div>

          <div className="auth-field">
            <label>Password</label>
            <input
              type="password"
              required
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? (
              'Processing...'
            ) : mode === 'login' ? (
              <>Sign In <ArrowRight size={14} /></>
            ) : (
              <>Create Account <ArrowRight size={14} /></>
            )}
          </button>

          {mode === 'login' && (
            <button
              type="button"
              className="auth-demo-btn"
              onClick={handleFillDemo}
            >
              <Sparkles size={13} /> Fill Demo Credentials (Alex Morgan)
            </button>
          )}
        </form>
      </div>
    </div>
  )
}