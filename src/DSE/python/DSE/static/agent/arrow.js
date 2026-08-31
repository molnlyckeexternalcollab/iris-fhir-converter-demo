const {useEffect, useRef} = React;

function ArrowFlow({direction = 'rtl', reverseFlow = false, speed = 1.0}) {
  const stemPathRef = useRef(null);
  const circlePathRef = useRef(null);
  const arrowRef = useRef(null);
  const circleRefs = useRef([]);
  circleRefs.current = [];

  const circleRadii = [5, 6, 8, 10, 13];  // ascending sizes matching Mölnlycke logo proportions

  const midY = 35;  // vertical centre of the horizontal run; half the SVG/row height (150px)

  const stemPaths = {
    'rtl': `M 300,${midY} L 125,${midY} A 50 50 0 0 0 75,${midY+50} L 75,${midY+57}`,
    'ltr': `M 0,${midY} L 175,${midY} A 50 50 0 0 1 225,${midY+50} L 225,${midY+57}`,
  };
  const circlePaths = {
    'rtl': `M 350,${midY} L 125,${midY} A 50 50 0 0 0 75,${midY+50} L 75,${midY+107}`,
    'ltr': `M -50,${midY} L 175,${midY} A 50 50 0 0 1 225,${midY+50} L 225,${midY+107}`,
  };

  const stemPathD = stemPaths[direction];
  const circlePathD = circlePaths[direction];

  const addToCircleRefs = el => {
    if (el && !circleRefs.current.includes(el)) {
      circleRefs.current.push(el);
    }
  };

  useEffect(() => {
    gsap.registerPlugin(MotionPathPlugin);
    gsap.set(arrowRef.current, {opacity: 0});
    gsap.set(circleRefs.current, {opacity: 0});

    const len = stemPathRef.current.getTotalLength();
    let pathTween, arrowTween, circlesTl;

    // All GSAP timings derived from the speed prop — restore originals here, not in script.js
    const dur     = 1.6 * speed;
    const stagger = 0.3 * speed;
    const fadeAt  = 2.8 * speed;  // = (4 * stagger + dur) for 5 circles

    if (reverseFlow) {
      gsap.set(
          stemPathRef.current, {strokeDasharray: len, strokeDashoffset: -len});
      pathTween = gsap.to(
          stemPathRef.current,
          {strokeDashoffset: 0, duration: dur, delay: 0, ease: 'power1.inOut'});
    } else {
      gsap.set(
          stemPathRef.current, {strokeDasharray: len, strokeDashoffset: len});
      pathTween = gsap.to(
          stemPathRef.current,
          {strokeDashoffset: 0, duration: dur, delay: 0, ease: 'power1.inOut'});
    }

    const motionPathConfig = {
      path: stemPathRef.current,
      align: stemPathRef.current,
      alignOrigin: [0.5, 0.5],
      autoRotate: true,
      start: reverseFlow ? 1 : 0,
      end: reverseFlow ? 0 : 1,
    };

    arrowTween = gsap.to(arrowRef.current, {
      opacity: 1,
      duration: dur,
      delay: 0,
      motionPath: motionPathConfig,
      ease: 'power1.inOut',
    });

    const circleMotionPathConfig = {
      path: circlePathRef.current,
      align: circlePathRef.current,
      alignOrigin: [0.5, 0.5],
      start: reverseFlow ? 1 : 0,
      end: reverseFlow ? 0 : 1,
    };

    circlesTl = gsap.timeline({delay: 0});
    circleRefs.current.forEach((circle, index) => {
      circlesTl.fromTo(
          circle, {opacity: 0}, {opacity: 1, duration: 0.2 * speed},
          index * stagger);  // stagger start time
      circlesTl.to(
          circle, {
            motionPath: circleMotionPathConfig,
            duration: dur,
            ease: 'power1.inOut',
          },
          index * stagger);  // same start time as opacity fade in
      circlesTl.to(
          circle, {opacity: 0, duration: 0.2 * speed},
          index * stagger + (dur - 0.2 * speed));  // fade out just before travel ends
    });
    circlesTl.to(arrowRef.current, {opacity: 0, duration: 0.2 * speed}, fadeAt);
    circlesTl.to(stemPathRef.current, {opacity: 0, duration: 0.2 * speed}, fadeAt);

    return () => {
      pathTween.kill();
      arrowTween.kill();
      circlesTl.kill();
    }
  }, [direction, reverseFlow]);

    return (
        <div>
            <svg width='300px' height='150px' viewBox='0 0 300 150' version='1.1' style={{
    overflow: 'visible' }}>
                <defs>
                    <filter id='glow' x='-100%' y='-100%' width='300%' height='300%'>
                        <feGaussianBlur in='SourceAlpha' stdDeviation='3' result='blur'/>
                        <feFlood floodColor='#14AF28' floodOpacity='1' result='color'/>
                        <feComposite in='color' in2='blur' operator='in' result='glow'/>
                        <feMerge>
                            <feMergeNode in='glow'/>
                            <feMergeNode in='SourceGraphic'/>
                        </feMerge>
                    </filter>
                </defs>
                <g id="Page-1" stroke="none" strokeWidth="1" fill="none" fillRule="evenodd">
                    <path ref={stemPathRef} id="Path-1" className="path" fill="none" stroke="#b6b4aa" strokeWidth="3" strokeLinejoin="round" strokeMiterlimit="10" d={stemPathD} />
                    <path ref={circlePathRef} id='Path-Circles' stroke='none' d={
    circlePathD} />
                    {[...Array(5)].map((_, i) => (
                        <circle key={i} ref={addToCircleRefs} r={circleRadii[i]} fill="#14AF28" filter="url(#glow)" />
                    ))
}
<polyline ref = {arrowRef} id = 'arrow' points = '0,-9 18,0 0,9 5,0' fill =
     '#484135' /></g>
            </svg>< /div>
    );
}
