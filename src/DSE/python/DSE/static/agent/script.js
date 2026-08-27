// EHR Navigator Agent — script.js
// Connects to the /agent/* endpoints of the DSE service.
// Requires arrow.js and dialog.js from the HF space in the same static folder.

const { useState, useEffect, useRef, useCallback } = React;

// ── Animation configuration ───────────────────────────────────────────────
// SPEED: 1.0 = original HF Space pace, 0.5 = twice as fast, 0.25 = four times.
const SPEED = 1;
const _ANIM_D = {               // original HF Space default values at SPEED = 1.0
  queueDelayLlm:   6000,        // ms — hold time while LLM processes a request
  queueDelayOther: 3000,        // ms — hold time for FHIR and response events
  gsapDuration:    1.6,         // s  — arrow travel time (also drives stagger/fadeAt)
  cssGlowCycle:    2.0,         // s  — one MedGemma glow pulse cycle
};
const ANIM = {
  queueDelayLlm:   _ANIM_D.queueDelayLlm   * SPEED,
  queueDelayOther: _ANIM_D.queueDelayOther * SPEED,
  gsapSpeed:       SPEED,
  // Glow starts after 15 % of the LLM hold — always visible before the hold expires
  cssGlowDelay: _ANIM_D.queueDelayLlm * SPEED * 0.15 / 1000,
  cssGlowCycle: _ANIM_D.cssGlowCycle  * SPEED,
};
document.documentElement.style.setProperty('--anim-glow-delay', `${ANIM.cssGlowDelay}s`);
document.documentElement.style.setProperty('--anim-glow-cycle', `${ANIM.cssGlowCycle}s`);

function Markdown({ content }) {
  const md = window.markdownit();
  return <div dangerouslySetInnerHTML={{ __html: md.render(content) }} />;
}

function AgentRunner({ onBack }) {
  const [questions, setQuestions]               = useState([]);
  const [selectedId, setSelectedId]             = useState(null);
  const [output, setOutput]                     = useState([]);
  const [answer, setAnswer]                     = useState('');
  const [intermediate, setIntermediate]         = useState('');
  const [isRunning, setIsRunning]               = useState(false);
  const [fhirActive, setFhirActive]             = useState(false);
  const [fhirReversed, setFhirReversed]         = useState(false);
  const [llmActive, setLlmActive]               = useState(false);
  const [llmReversed, setLlmReversed]           = useState(false);
  const [llmWorking, setLlmWorking]             = useState(false);
  const [showDetails, setShowDetails]           = useState(false);
  // Custom additions
  const [patientId, setPatientId]               = useState('7597');
  const [customPrompt, setCustomPrompt]         = useState('');

  useEffect(() => {
    fetch('questions').then(r => r.json()).then(setQuestions);
  }, []);

  const eventQueue    = useRef([]);
  const processing    = useRef(false);
  const esRef         = useRef(null);
  const timerRef      = useRef(null);
  const eventCounter  = useRef(0);

  const pushEvent = text => {
    setOutput(prev => [{ id: eventCounter.current++, text }, ...prev]);
  };

  const processQueue = useCallback(() => {
    if (!eventQueue.current.length) { processing.current = false; return; }
    processing.current = true;
    const raw   = eventQueue.current.shift();
    const msg   = JSON.parse(raw.data);

    // If the final answer is already waiting in the queue the backend has finished —
    // drain remaining events immediately instead of running the full animation replay.
    const finalPending = msg.final || eventQueue.current.some(e => JSON.parse(e.data).final);
    const delay = finalPending
      ? 50
      : (msg.destination === 'LLM' && msg.request ? ANIM.queueDelayLlm : ANIM.queueDelayOther);

    if (msg.destination === 'FHIR') {
      setFhirReversed(!msg.request); setFhirActive(true);
      setLlmActive(false); setLlmWorking(false);
    } else if (msg.destination === 'LLM') {
      setLlmReversed(!msg.request); setLlmActive(true);
      setFhirActive(false); setLlmWorking(msg.request);
    } else {
      setFhirActive(false); setLlmActive(false); setLlmWorking(false);
    }

    if (msg.final) {
      pushEvent(msg.event);
      setAnswer(msg.data || '');
      setIntermediate('');
      esRef.current.close();
      setIsRunning(false);
      setLlmWorking(false);
      if (eventQueue.current.length)
        timerRef.current = setTimeout(processQueue, delay);
      else
        processing.current = false;
      return;
    }

    if (msg.data && typeof msg.data !== 'string') {
      setIntermediate('```json\n' + JSON.stringify(msg.data, null, 2) + '\n```');
      pushEvent(`${msg.event}: structured data received`);
    } else {
      setIntermediate(msg.data || '');
      const suffix = msg.data && msg.data.length < 30 ? `: ${msg.data}` : '';
      pushEvent(`${msg.event}${suffix}`);
    }
    timerRef.current = setTimeout(processQueue, delay);
  }, []);

  const startRun = (questionId, prompt) => {
    setSelectedId(questionId ?? prompt);
    setOutput([]); setAnswer(''); setIntermediate('');
    setIsRunning(true);
    setFhirActive(false); setLlmActive(false); setLlmWorking(false);
    eventQueue.current = [];
    if (timerRef.current) clearTimeout(timerRef.current);
    processing.current = false;

    let url = `run_agent?patient_id=${encodeURIComponent(patientId)}`;
    if (questionId != null) url += `&question_id=${questionId}`;
    else                    url += `&prompt=${encodeURIComponent(prompt)}`;

    esRef.current = new EventSource(new URL(url, document.baseURI));
    esRef.current.onmessage = e => {
      eventQueue.current.push(e);
      if (!processing.current) processQueue();
    };
    esRef.current.onerror = () => {
      const hasFinal = eventQueue.current.some(e => JSON.parse(e.data).final);
      if (hasFinal) {
        esRef.current.close();
        if (!processing.current && eventQueue.current.length) processQueue();
        return;
      }
      pushEvent('Connection error.');
      esRef.current.close();
      setIsRunning(false);
      eventQueue.current = [];
      if (timerRef.current) clearTimeout(timerRef.current);
      processing.current = false; setLlmWorking(false);
    };
  };

  const questionLabel = typeof selectedId === 'string'
    ? selectedId
    : questions.find(q => q.id === selectedId)?.question;

  return (
    <div className='agent-page-container'>
      {showDetails && <Dialog onClose={() => setShowDetails(false)} />}
      <div className='demo-header'>
        <button className='back-button' onClick={onBack}>&lt; Back</button>
        <button className='details-button' onClick={() => setShowDetails(true)}>
          <span className='material-symbols-outlined'>code</span>
          Details about this Demo
        </button>
      </div>

      <div className='demo-frame'>
        <div className='agent-container'>

          {/* ── Left panel ── */}
          <div className='left-panel'>
            <h4>Clinician</h4>
            <img src='static/clinician.avif' alt='Clinician' className='clinician-image' />

            <div style={{ margin: '16px 0 4px' }}>
              <label style={{ fontSize: '0.78em', color: '#5f6368', display: 'block', marginBottom: '4px' }}>
                Patient ID
              </label>
              <input
                type='text'
                value={patientId}
                onChange={e => setPatientId(e.target.value)}
                disabled={isRunning}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '8px',
                         border: '1px solid #dadce0', fontSize: '0.9em', boxSizing: 'border-box' }}
              />
            </div>

            <h5>Select a task</h5>
            <div className='task-list'>
              {questions.map(q => (
                <button
                  key={q.id}
                  className={`task-button ${selectedId === q.id && isRunning ? 'running' : ''}`}
                  onClick={() => startRun(q.id, null)}
                  disabled={isRunning}
                >
                  {q.question}
                </button>
              ))}
            </div>

            <h5 style={{ marginTop: '20px' }}>Or ask a custom question</h5>
            <textarea
              placeholder='Type your clinical question…'
              value={customPrompt}
              onChange={e => setCustomPrompt(e.target.value)}
              disabled={isRunning}
              style={{ width: '100%', minHeight: '72px', padding: '8px 10px', borderRadius: '8px',
                       border: '1px solid #dadce0', fontSize: '0.85em', resize: 'vertical',
                       boxSizing: 'border-box', fontFamily: 'inherit', marginTop: '8px' }}
            />
            <button
              className={`task-button ${typeof selectedId === 'string' && isRunning ? 'running' : ''}`}
              style={{ marginTop: '8px', width: '100%', textAlign: 'center',
                       ...(customPrompt.trim() && !isRunning
                         ? { background: '#202124', color: 'white', borderColor: '#202124' }
                         : {}) }}
              onClick={() => startRun(null, customPrompt)}
              disabled={isRunning || !customPrompt.trim()}
            >
              Submit
            </button>
          </div>

          {/* ── Right panel ── */}
          <div className='right-panel'>
            <div className='agent-header'>EHR Navigator Agent</div>

            <div className='agent-vertex-arrow'>
              {llmActive && <ArrowFlow reverseFlow={llmReversed} speed={ANIM.gsapSpeed} />}
            </div>

            <img src='static/agent.svg' alt='Agent' className='agent agent-image' />

            <div className='agent-fhir-arrow'>
              {fhirActive && <ArrowFlow direction='ltr' reverseFlow={fhirReversed} speed={ANIM.gsapSpeed} />}
            </div>

            <div className={`vertex ${llmWorking ? 'working' : ''}`}>
              <div className='gcp-resource-frame'>
                <img src='static/molnlycke-medgemma.svg' alt='MedGemma' />
                <div>MedGemma 4B</div>
                <div>(or Mölnlycke LLM)</div>
              </div>
            </div>

            <div className='event-log'>
              {output.map(e => (
                <div key={e.id} className='event-item'>{e.text}</div>
              ))}
            </div>

            <div className='fhir'>
              <div className='gcp-resource-frame'>
                <img src='static/1-intellicare-foundation.svg' alt='FHIR' className='fhir-image' />
                <div>Electronic Health Record</div>
                <div>(IRIS FHIR R4)</div>
              </div>
            </div>

            {isRunning && intermediate && (
              <div className='answer'><Markdown content={intermediate} /></div>
            )}
            {answer && (
              <div className='answer'>
                <em>{questionLabel}</em><br /><br />
                <strong>Answer: </strong><Markdown content={answer} />
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}

function Introduction({ onStart }) {
  return (
    <div className='intro-page'>
      <header className='intro-header'>
        <img src='static/molnlycke-medgemma.svg' className='logo' alt='MedGemma' />
      </header>
      <main className='intro-content'>
        <section className='diagram-section'>
          <img src='static/intro.svg' alt='Agent Diagram' />
        </section>
        <section className='text-section'>
          <h1>EHR Navigator Agent</h1>
          <p>
            An agent that answers clinical questions by navigating a patient's full FHIR record.
            It discovers available resources, plans which ones to retrieve, extracts key facts,
            and synthesises a final answer.
          </p>
          <p>
            This instance uses <strong>MedGemma 4B</strong> running locally via LM Studio and
            the <strong>IRIS FHIR R4</strong> server as the data source.
            All patient data is synthetic, generated by Synthea.
          </p>
          <div className='disclaimer'>
            <p>
              <span className='disclaimer-badge'>Disclaimer</span>
              {' '}For demonstration purposes only. Not a clinical tool.
            </p>
          </div>
          <button onClick={onStart} className='view-demo-button'>View Demo</button>
        </section>
      </main>
    </div>
  );
}

function App() {
  const [showIntro, setShowIntro] = useState(true);
  useEffect(() => {
    document.body.classList.toggle('intro-active', showIntro);
  }, [showIntro]);
  return showIntro
    ? <Introduction onStart={() => setShowIntro(false)} />
    : <AgentRunner onBack={() => setShowIntro(true)} />;
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
