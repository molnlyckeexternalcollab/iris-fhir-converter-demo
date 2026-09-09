// EHR Navigator Agent — script.js
// Connects to the /agent/* endpoints of the DSE service.
// Requires arrow.js and dialog.js from the HF space in the same static folder.

const { useState, useEffect, useRef, useCallback } = React;

// ── Animation configuration ───────────────────────────────────────────────
// SPEED: 1.0 = original HF Space pace, 0.5 = twice as fast, 0.25 = four times.
const SPEED = 0.33;
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

function AgentLogo({ isRunning, className }) {
  const svgRef        = useRef(null);
  const waveRef        = useRef(null);
  const twinkleActive  = useRef(false);

  // Circles wave + corner twinkles share the same isRunning gate
  useEffect(() => {
    const sel     = gsap.utils.selector(svgRef.current);
    const circles = sel('#circ1, #circ2, #circ3, #circ4, #circ5');
    const corners = ['#tl', '#tr', '#bl', '#br'];

    if (isRunning) {
      // --- circles ---
      gsap.set(circles, { scale: 0, transformOrigin: '50% 50%' });
      waveRef.current = gsap.timeline({ repeat: -1, repeatDelay: 0.15 })
        .to(circles, { scale: 1, duration: 0.28, ease: 'back.out(2.2)', stagger: 0.1 })
        .to({},       { duration: 0.2 })
        .to(circles, { scale: 0, duration: 0.14, ease: 'power2.in',     stagger: 0.07 });

      // --- corner twinkles ---
      twinkleActive.current = true;
      gsap.set(corners.map(id => sel(id)), { opacity: 0 });
      function scheduleTwinkle(id) {
        if (!twinkleActive.current) return;
        gsap.delayedCall(Math.random() * 0.4, () => {
          if (!twinkleActive.current) return;
          gsap.timeline({ onComplete: () => scheduleTwinkle(id) })
            .to(sel(id), { opacity: 1, duration: 0.3,  ease: 'power2.in' })
            .to({},       { duration: 0.15 })
            .to(sel(id), { opacity: 0, duration: 1.0,  ease: 'power1.out' });
        });
      }
      corners.forEach(id =>
        gsap.delayedCall(Math.random() * 1.45, () => scheduleTwinkle(id))
      );
    } else {
      // --- stop circles ---
      if (waveRef.current) {
        waveRef.current.repeat(0);  // let current wave finish then stop
        waveRef.current = null;
      }
      // --- stop corners: flag kills recursive chain, then fade out ---
      twinkleActive.current = false;
      corners.forEach(id => gsap.killTweensOf(sel(id)));
      gsap.to(corners.map(id => sel(id)), { opacity: 0, duration: 0.3 });
    }
  }, [isRunning]);

  return (
    <svg ref={svgRef} id='agent-logo' className={className} viewBox='0 0 27.322496 24.474658' fill='none'
         xmlns='http://www.w3.org/2000/svg' style={{ width: '100%', height: 'auto', overflow: 'visible' }}>
      <path id='e' fillRule='evenodd' clipRule='evenodd' fill='#14af28'
        d='m 1.8291521,19.017597 c 0.0167,-0.55233 0.0514,-0.81985 0.2276,-1.22964 0.2816,-0.67756 0.9348,-1.14195 1.7832,-1.14343 0.8483,-0.0015 1.4854,0.46068 1.7693,1.13701 0.1774,0.409301 0.2307,0.68373 0.2495,1.23606 z m 2.0081,-3.88726 c -2.3223,0.0042 -3.838,1.71724 -3.833,4.67029 0.0058,3.47502 1.8123,4.67822 4.0808,4.67402 1.2395,-0.0022 2.0441,-0.3001 2.778,-0.8754 0.0422,-0.0331 0.0462,-0.0979 0.0076,-0.135599 0,0 -0.8336,-0.8191 -1.0305,-1.0098 -0.0285,-0.0275 -0.0704,-0.0294 -0.1028,-0.0072 -0.4387,0.3023 -0.9127,0.4422 -1.6192,0.4434 -1.4828,0.0027 -2.3059,-0.9861 -2.3085,-2.552661 h 5.7923 c 0.0469,0 0.0845,-0.03927 0.0845,-0.08794 l -0.0012,-0.732641 c -0.0043,-2.592659 -1.4185,-4.39092 -3.848,-4.386469 z' />
      <path id='h' fill='#14af28'
        d='m 9.1855336,11.383855 c -0.04272,0.0047 -0.07813,0.0425 -0.07813,0.08789 l 0.002,12.865234 c 0,0.0487 0.03884,0.08789 0.08594,0.08789 h 1.6347654 c 0.0469,0 0.08398,-0.03899 0.08398,-0.08789 -6.4e-5,-1.428993 -3e-5,-2.748435 0,-3.941406 h 3.724609 c 1.31e-4,2.078021 0,3.825563 0,3.941406 0,0.0489 0.03709,0.08789 0.08399,0.08789 h 1.634765 c 0.0471,0 0.08594,-0.03919 0.08594,-0.08789 V 11.471745 c 0,-0.04842 -0.03739,-0.08764 -0.08398,-0.08789 -0.9596,-0.0015 -1.720703,0.805065 -1.720703,1.800781 0,0 -1.83e-4,3.002556 0,5.892579 h -3.724609 c 1.84e-4,-3.711087 0,-5.892579 0,-5.892579 -0.0016,-0.995715 -0.761103,-1.802263 -1.7207034,-1.800781 -0.0029,1.6e-5 -0.005,-3.13e-4 -0.0078,0 z' />
      <path id='r' fillRule='evenodd' clipRule='evenodd' fill='#14af28'
        d='m 22.063501,15.186553 c -0.8413,0.0015 -1.6197,0.25813 -2.225699,0.852451 -0.056,0.05483 -0.1479,0.01309 -0.1479,-0.0667 l 6.99e-4,-0.475249 c 0,-0.04866 -0.038,-0.08819 -0.0849,-0.08794 h -1.6549 c -0.0469,0 -0.0848,0.03952 -0.0848,0.08818 v 8.832451 c 0,0.0487 0.0381,0.088 0.085,0.088 l 1.6549,5e-4 c 0.0469,0 0.0847,-0.0396 0.0847,-0.0882 v -5.03318 c -0.0023,-1.445771 0.8572,-2.42073 1.8754,-2.422711 0.217862,-0.750326 0.270034,-0.959325 0.4975,-1.6876 z' />
      <path id='green' fill='#14af28'
        d='m 24.995804,14.653203 h -2.8e-4 c -0.07526,-1.46e-4 -0.142916,-0.04588 -0.170895,-0.115765 -0.0025,-0.0061 -0.25338,-0.621295 -0.728633,-1.09429 -0.47554,-0.47327 -1.08703,-0.72235 -1.093148,-0.724816 -0.0699,-0.02809 -0.115766,-0.09593 -0.115673,-0.17129 7.3e-5,-0.07532 0.0459,-0.143056 0.115844,-0.171022 0.01116,-0.0045 0.616524,-0.252158 1.092999,-0.726362 0.477924,-0.475645 0.725946,-1.091188 0.7284,-1.097343 0.02791,-0.07019 0.09582,-0.116355 0.171357,-0.116355 h 2.19e-4 c 0.07561,7.4e-5 0.143537,0.04624 0.171312,0.116541 0.0023,0.0061 0.250232,0.621364 0.728319,1.097169 0.478641,0.476372 1.086995,0.723955 1.09308,0.726397 0.06987,0.02806 0.11575,0.09582 0.11575,0.171138 0,0.07531 -0.04573,0.143071 -0.115611,0.171127 -0.0061,0.0025 -0.619208,0.253103 -1.093228,0.724841 -0.473707,0.471473 -0.726281,1.088492 -0.728769,1.09467 -0.02816,0.06969 -0.09584,0.115377 -0.170978,0.115377 h -2.4e-5 z m -1.504113,-2.106108 c 0.242775,0.133271 0.572829,0.344526 0.864406,0.634708 0.29267,0.291277 0.505695,0.623311 0.6398,0.867298 0.134341,-0.244263 0.347554,-0.576678 0.639547,-0.867298 0.290977,-0.289583 0.621536,-0.501064 0.864625,-0.634558 -0.242225,-0.13324 -0.571665,-0.344664 -0.864625,-0.636216 -0.293489,-0.292097 -0.505938,-0.623855 -0.639686,-0.868232 -0.133752,0.244401 -0.346242,0.576205 -0.639661,0.868232 -0.292788,0.291392 -0.622195,0.502803 -0.864419,0.636066 v 0 z' />
      <path id='tl' fill='#14af28'
        d='m 23.398918,11.680764 c -0.04719,0 -0.09437,-0.018 -0.130356,-0.054 l -0.54734,-0.54734 c -0.07201,-0.07199 -0.07201,-0.188735 0,-0.260731 l 0.54734,-0.547341 c 0.07199,-0.07201 0.188735,-0.07201 0.26073,0 l 0.547341,0.547341 c 0.07201,0.07199 0.07201,0.188734 0,0.260731 l -0.547341,0.54734 c -0.036,0.036 -0.08319,0.054 -0.130357,0.054 v 0 z m -0.286611,-0.731707 0.286611,0.286611 0.286611,-0.286611 -0.286611,-0.286611 z' />
      <path id='tr' fill='#9aa0a6'
        d='m 26.590777,11.680764 c -0.04719,0 -0.09437,-0.018 -0.130356,-0.054 l -0.547343,-0.54734 c -0.07201,-0.07199 -0.07201,-0.188735 0,-0.260731 l 0.547339,-0.547341 c 0.07199,-0.07201 0.188736,-0.07201 0.26073,0 l 0.547342,0.547341 c 0.07201,0.07199 0.07201,0.188734 0,0.260731 l -0.547342,0.54734 c -0.036,0.036 -0.08319,0.054 -0.130356,0.054 z m -0.286611,-0.731707 0.286611,0.286611 0.28661,-0.286611 -0.28661,-0.286611 z' />
      <path id='br' fill='#14af28'
        d='m 26.590777,14.872623 c -0.04719,0 -0.09437,-0.018 -0.130356,-0.054 l -0.547343,-0.547344 c -0.07201,-0.07199 -0.07201,-0.188735 0,-0.260731 l 0.547339,-0.54734 c 0.07199,-0.07199 0.188736,-0.07199 0.26073,0 l 0.547342,0.54734 c 0.07201,0.07199 0.07201,0.188735 0,0.260731 l -0.547342,0.547339 c -0.036,0.036 -0.08319,0.054 -0.130356,0.054 z m -0.286611,-0.731706 0.286611,0.28661 0.28661,-0.28661 -0.28661,-0.286611 z' />
      <path id='bl' fill='#9aa0a6'
        d='m 23.398918,14.872623 c -0.04719,0 -0.09437,-0.018 -0.130356,-0.054 l -0.54734,-0.547339 c -0.07201,-0.07199 -0.07201,-0.188736 0,-0.260732 l 0.54734,-0.547339 c 0.07199,-0.07199 0.188735,-0.07199 0.26073,0 l 0.547341,0.547339 c 0.07201,0.07199 0.07201,0.188735 0,0.260732 l -0.547341,0.547339 c -0.036,0.036 -0.08319,0.054 -0.130357,0.054 v 0 z m -0.286611,-0.731706 0.286611,0.28661 0.286611,-0.28661 -0.286611,-0.286611 z' />
      <path id='grey' fill='#9aa0a6'
        d='m 25.89555,13.443155 c 0.474021,-0.47175 1.087238,-0.722432 1.093229,-0.72484 0.06987,-0.02807 0.115596,-0.09581 0.115611,-0.171127 0,-0.0753 -0.04586,-0.143072 -0.11575,-0.171127 -0.0061,-0.0025 -0.614439,-0.250025 -1.093079,-0.726397 -8.4e-4,-8.12e-4 -0.0017,-0.0015 -0.0026,-0.0023 l -0.260465,0.260465 c 0.001,0.001 0.0019,0.0021 0.0029,0.0032 0.292961,0.291554 0.622414,0.502965 0.864625,0.636216 -0.243087,0.133489 -0.573646,0.344987 -0.864625,0.634558 -0.29199,0.29062 -0.505201,0.623024 -0.639545,0.867298 -0.133923,-0.243639 -0.346542,-0.575076 -0.638581,-0.866065 l -0.260739,0.260742 c 0.474859,0.472913 0.725611,1.087675 0.72803,1.093679 0.02798,0.06987 0.09564,0.115626 0.170896,0.115765 h 2.81e-4 c 0.07514,0 0.142807,-0.04569 0.170976,-0.115377 0.0025,-0.0062 0.255062,-0.623197 0.728771,-1.09467 h 1.3e-5 z' />
      <path id='circ1' fillRule='evenodd' clipRule='evenodd' fill='#14af28'
        d='m 0.97783337,5.4187968 c 0.53999643,0 0.97771683,-0.4348183 0.97771683,-0.9711453 0,-0.5363085 -0.4377204,-0.9710436 -0.97771683,-0.9710436 C 0.43772187,3.4766079 0,3.911343 0,4.4476515 0,4.9839785 0.43772187,5.4187968 0.97783337,5.4187968 Z' />
      <path id='circ2' fillRule='evenodd' clipRule='evenodd' fill='#14af28'
        d='m 2.6002448,3.8809611 c 0.6675492,0 1.2085844,-0.537458 1.2085844,-1.2004458 0,-0.6628801 -0.5410352,-1.2003331 -1.2085844,-1.2003331 -0.6675494,0 -1.2087009,0.537453 -1.2087009,1.2003331 0,0.6629878 0.5411515,1.2004458 1.2087009,1.2004458 z' />
      <path id='circ3' fillRule='evenodd' clipRule='evenodd' fill='#14af28'
        d='m 4.8425301,3.1699351 c -0.8737128,0 -1.5820114,0.7034591 -1.5820114,1.5712076 0,0.8678594 0.7082986,1.571314 1.5820114,1.571314 0.8738296,0 1.5821381,-0.7034546 1.5821381,-1.571314 0,-0.8677485 -0.7083085,-1.5712076 -1.5821381,-1.5712076 z' />
      <path id='circ4' fillRule='evenodd' clipRule='evenodd' fill='#14af28'
        d='m 7.4530601,3.8847414 c 1.0800803,0 1.9556371,-0.8696938 1.9556371,-1.9424266 C 9.4086972,0.8696948 8.5331398,0 7.4530595,0 6.3729305,0 5.497276,0.8696948 5.497276,1.9423148 c 0,1.0727328 0.8756545,1.9424266 1.9557841,1.9424266 z' />
      <path id='circ5' fillRule='evenodd' clipRule='evenodd' fill='#14af28'
        d='m 11.029741,2.6805153 c -1.4139479,0 -2.5599381,1.1383076 -2.5599381,2.5424946 0,1.4041423 1.1459902,2.5424654 2.5599381,2.5424654 1.413801,0 2.559839,-1.1383231 2.559839,-2.5424654 0,-1.404187 -1.146038,-2.5424946 -2.559839,-2.5424946 z' />
    </svg>
  );
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
  const [patientId, setPatientId]               = useState('3887');
  const [customPrompt, setCustomPrompt]         = useState('');
  const [, setTick]                             = useState(0); // drives elapsed-timer re-renders
  const [agentLogoPulse, setAgentLogoPulse]     = useState(false);

  useEffect(() => {
    fetch('questions').then(r => r.json()).then(setQuestions);
  }, []);

  // Tick every 200ms while any FHIR task is still running so elapsed times update live
  useEffect(() => {
    const hasRunning = output.some(e => e.type === 'tracked' && e.status === 'running');
    if (!hasRunning) return;
    const id = setInterval(() => setTick(t => t + 1), 200);
    return () => clearInterval(id);
  }, [output]);

  const eventQueue    = useRef([]);
  const processing    = useRef(false);
  const esRef         = useRef(null);
  const timerRef      = useRef(null);
  const eventCounter  = useRef(0);
  const logoPulseTimer = useRef(null);

  const pushEvent = text => {
    setOutput(prev => [{ id: eventCounter.current++, type: 'plain', text }, ...prev]);
  };

  const pushTrackedStart = (task_id, label, kind = 'fhir') => {
    setOutput(prev => [{ id: eventCounter.current++, type: 'tracked', task_id, label, kind, startTime: Date.now(), status: 'running' }, ...prev]);
  };

  const updateTrackedDone = (task_id) => {
    setOutput(prev => prev.map(e =>
      e.type === 'tracked' && e.task_id === task_id && e.status === 'running'
        ? { ...e, status: 'done', elapsed: Date.now() - e.startTime }
        : e
    ));
  };

  const triggerLogoPulse = () => {
    clearTimeout(logoPulseTimer.current);
    setAgentLogoPulse(true);
    logoPulseTimer.current = setTimeout(() => setAgentLogoPulse(false), 800);
  };

  const processQueue = useCallback(() => {
    if (!eventQueue.current.length) { processing.current = false; return; }
    processing.current = true;
    const raw   = eventQueue.current.shift();
    const msg   = JSON.parse(raw.data);
    console.log('[SSE]', msg);

    // If the final answer is already waiting in the queue the backend has finished —
    // drain remaining events immediately instead of running the full animation replay.
    const finalPending = msg.final || eventQueue.current.some(e => JSON.parse(e.data).final);
    const delay = finalPending
      ? 50
      : msg.destination === 'LLM' && msg.request
        ? ANIM.queueDelayLlm
        : 50;

    if (msg.destination === 'FHIR') {
      setFhirReversed(!msg.request); setFhirActive(true);
      setLlmActive(false); setLlmWorking(false);
    } else if (msg.destination === 'LLM') {
      setLlmReversed(!msg.request); setLlmActive(true);
      setFhirActive(false); setLlmWorking(msg.request);
      triggerLogoPulse();
    } else {
      setFhirActive(false); setLlmActive(false); setLlmWorking(false);
    }

    if (msg.final) {
      pushEvent(msg.event);
      setOutput(prev => prev.map(e =>
        e.type === 'tracked' && e.status === 'running'
          ? { ...e, status: 'done', elapsed: Date.now() - e.startTime }
          : e
      ));
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

    if (msg.task_id) {
      if (msg.status === 'running') pushTrackedStart(msg.task_id, msg.event);
      else updateTrackedDone(msg.task_id);
    } else if (msg.destination === 'LLM' && msg.request) {
      pushTrackedStart('llm', msg.event, 'llm');
    } else if (msg.destination === 'LLM' && !msg.request) {
      updateTrackedDone('llm');
      const suffix = msg.data && typeof msg.data === 'string' && msg.data.length < 30 ? `: ${msg.data}` : '';
      pushEvent(`${msg.event}${suffix}`);
    } else if (msg.data && typeof msg.data !== 'string') {
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


          </div>

          {/* ── Right panel ── */}
          <div className='right-panel'>
            <div className='agent-header'>EHR Navigator Agent</div>

            <div className='agent-vertex-arrow'>
              {llmActive && <ArrowFlow reverseFlow={llmReversed} speed={ANIM.gsapSpeed} />}
            </div>

            <AgentLogo isRunning={agentLogoPulse || output.some(e => e.type === 'tracked' && e.task_id && e.task_id.startsWith('fhir-') && e.status === 'running')} className='agent agent-image' />

            <div className='agent-fhir-arrow'>
              {fhirActive && <ArrowFlow direction='ltr' reverseFlow={fhirReversed} speed={ANIM.gsapSpeed} />}
            </div>

            <div id='llm' className={`vertex ${llmWorking ? 'working' : ''}`}>
              <div className='gcp-resource-frame'>
                <img src='static/Molnlycke-logo-individual-circles.svg' alt='Molnycke-logo' />
                <div>LLM</div>
                <img src='static/molnlycke-medgemma.svg' alt='MedGemma' />
              </div>
            </div>

            <div id='event-log' className='event-log'>
              {output.map(e => {
                if (e.type === 'tracked') {
                  const secs = e.status === 'running'
                    ? ((Date.now() - e.startTime) / 1000).toFixed(1)
                    : (e.elapsed / 1000).toFixed(1);
                  return (
                    <div key={e.id} className={`event-item tracked ${e.status} ${e.kind || 'fhir'}`}>
                      <span className='tracked-label'>{e.label}</span>
                      <span className='tracked-timer'>{secs}s</span>
                    </div>
                  );
                }
                return <div key={e.id} className='event-item'>{e.text}</div>;
              })}
            </div>

            <div id='fhir-server' className={`fhir ${fhirActive ? 'active' : ''}`}>
              <div className='gcp-resource-frame'>
                <img src='static/1-intellicare-foundation.svg' alt='FHIR' className='fhir-image' />
                <div>Electronic Health Record</div>
                <div>(IRIS FHIR R4)</div>
              </div>
            </div>

            {isRunning && intermediate && (
              <div id='answer' className='answer'><Markdown content={intermediate} /></div>
            )}
            {answer && (
              <div id='answer' className='answer'>
                <em>{questionLabel}</em><br /><br />
                <strong>Answer: </strong><Markdown content={answer} />
              </div>
            )}

            <div className='question-input'>
              <textarea
                placeholder='Type your clinical question…'
                value={customPrompt}
                onChange={e => setCustomPrompt(e.target.value)}
                disabled={isRunning}
              />
              <button
                className={`task-button ${typeof selectedId === 'string' && isRunning ? 'running' : ''}`}
                style={customPrompt.trim() && !isRunning
                  ? { background: '#202124', color: 'white', borderColor: '#202124' }
                  : {}}
                onClick={() => startRun(null, customPrompt)}
                disabled={isRunning || !customPrompt.trim()}
              >
                Submit
              </button>
            </div>
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
