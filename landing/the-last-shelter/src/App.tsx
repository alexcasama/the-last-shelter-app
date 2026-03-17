import React, { useEffect, useState } from 'react';
import { motion, useScroll, useTransform } from 'motion/react';
import { Play, ChevronRight, ChevronLeft, X, Mail, Instagram, Twitter, Youtube } from 'lucide-react';

const GALLERY_IMAGES = [
  "https://thelastshelter.s3.us-east-2.amazonaws.com/1.png",
  "https://thelastshelter.s3.us-east-2.amazonaws.com/2.png",
  "https://thelastshelter.s3.us-east-2.amazonaws.com/3.png",
  "https://thelastshelter.s3.us-east-2.amazonaws.com/4.png",
  "https://thelastshelter.s3.us-east-2.amazonaws.com/5.png",
  "https://thelastshelter.s3.us-east-2.amazonaws.com/6.png"
];

// Particles Background Component
const Particles = () => {
  const [particles, setParticles] = useState<{ id: number; left: string; size: string; duration: string; delay: string }[]>([]);

  useEffect(() => {
    const newParticles = Array.from({ length: 30 }).map((_, i) => ({
      id: i,
      left: `${Math.random() * 100}%`,
      size: `${Math.random() * 4 + 2}px`,
      duration: `${Math.random() * 5 + 5}s`,
      delay: `${Math.random() * 5}s`,
    }));
    setParticles(newParticles);
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-30">
      {particles.map((particle) => (
        <div
          key={particle.id}
          className="particle"
          style={{
            left: particle.left,
            width: particle.size,
            height: particle.size,
            animationDuration: particle.duration,
            animationDelay: particle.delay,
          }}
        />
      ))}
    </div>
  );
};

// Section Header Component
const SectionHeader = ({ title, subtitle }: { title: string; subtitle?: string }) => (
  <div className="text-center mb-6 md:mb-12 relative z-10">
    {subtitle && (
      <motion.p
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="text-frost-500 font-display tracking-[0.1em] text-sm uppercase mb-2 md:mb-4"
      >
        {subtitle}
      </motion.p>
    )}
    <motion.h2
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      className="text-4xl md:text-5xl lg:text-6xl font-display text-gradient-action uppercase tracking-tight"
    >
      {title}
    </motion.h2>
    <div className="mt-4 flex justify-center">
      <div className="h-1 w-24 bg-gradient-to-r from-transparent via-frost-500/50 to-transparent" />
    </div>
  </div>
);

// Venn Diagram Component
const VennDiagram = () => (
  <div className="relative w-full h-72 flex justify-center items-center scale-105 md:scale-110">
    {/* Survival */}
    <div className="absolute w-[150px] h-[150px] rounded-full border border-white/10 bg-frost-500/5 flex items-center justify-center transition-transform group-hover:scale-105 z-0 -translate-x-12 -translate-y-7">
      <span className="absolute top-8 text-[9px] sm:text-[10px] font-display tracking-widest text-frost-400 uppercase">Survival</span>
    </div>
    {/* Construction */}
    <div className="absolute w-[150px] h-[150px] rounded-full border border-white/10 bg-frost-500/5 flex items-center justify-center transition-transform group-hover:scale-105 z-0 translate-x-12 -translate-y-7">
      <span className="absolute top-8 text-[9px] sm:text-[10px] font-display tracking-widest text-frost-400 uppercase">Construction</span>
    </div>
    {/* Storytelling */}
    <div className="absolute w-[150px] h-[150px] rounded-full border border-white/10 bg-frost-500/5 flex items-center justify-center transition-transform group-hover:scale-105 z-0 translate-y-12">
      <span className="absolute bottom-8 text-[9px] sm:text-[10px] font-display tracking-widest text-frost-400 uppercase">Storytelling</span>
    </div>
    {/* Intersection Highlight */}
    <div className="absolute w-16 h-16 rounded-full border-2 border-dashed border-frost-500/60 bg-frost-500/10 backdrop-blur-md flex items-center justify-center z-10 shadow-[0_0_15px_rgba(93,173,226,0.3)]">
      <span className="text-white font-display text-base sm:text-lg font-bold tracking-widest drop-shadow-md">TLS</span>
    </div>
  </div>
);

// Format Flow Component
const FormatFlow = () => {
  const [hoveredStep, setHoveredStep] = useState<string | null>(null);
  const steps = [
    { name: 'Intro', desc: 'Setting the stage' },
    { name: 'Host', desc: 'Jack Harlan briefing' },
    { name: 'Arc', desc: 'Survival challenge' },
    { name: 'Outro', desc: 'Resolution & next' }
  ];

  return (
    <div className="flex flex-col items-center w-full">
      <div className="flex items-center justify-between w-full relative px-2">
        {/* Connecting Line */}
        <div className="absolute left-6 right-6 top-4 h-px bg-gradient-to-r from-transparent via-frost-500/50 to-transparent" />

        {steps.map((step, index) => (
          <div
            key={step.name}
            className="relative flex flex-col items-center gap-2 group/step cursor-pointer"
            onMouseEnter={() => setHoveredStep(step.name)}
            onMouseLeave={() => setHoveredStep(null)}
          >
            <span className="text-[10px] sm:text-xs font-display text-frost-500 font-bold mb-1 group-hover/step:text-white transition-colors">
              {index + 1}
            </span>
            <div className="w-8 h-8 rounded-full bg-[#0a0a0a] border border-frost-500/50 flex items-center justify-center z-10 group-hover/step:border-frost-500 group-hover/step:shadow-[0_0_15px_rgba(93,173,226,0.5)] transition-all">
              <div className="w-2 h-2 rounded-full bg-frost-500" />
            </div>
            <span className="text-xs font-display tracking-widest text-gray-400 uppercase group-hover/step:text-white transition-colors">{step.name}</span>
          </div>
        ))}
      </div>
      <div className="h-8 mt-8 text-center">
        <p className={`text-xs text-frost-400 font-display tracking-widest uppercase transition-opacity duration-300 ${hoveredStep ? 'opacity-100' : 'opacity-0'}`}>
          {hoveredStep ? steps.find(s => s.name === hoveredStep)?.desc : 'Hover a phase'}
        </p>
      </div>
    </div>
  );
};

// Circular Flow Component for AI Technology
const CircularFlow = () => {
  const [hoveredNode, setHoveredNode] = useState<number | null>(null);

  const nodes = [
    { id: 1, title: 'Original Stories', desc: 'Creative concepts' },
    { id: 2, title: 'Scripting', desc: 'Survival experts' },
    { id: 3, title: 'AI Engine', desc: 'Tech docs generation' },
    { id: 4, title: 'Production', desc: 'Voice & Cinematics' },
    { id: 5, title: 'Launch', desc: 'Episode release' }
  ];

  return (
    <div className="relative w-full h-64 flex flex-col items-center justify-center mt-5 scale-105 md:scale-110">
      <div className="relative w-52 h-52 flex items-center justify-center">
        {/* Center glowing orb */}
        <div className="absolute w-16 h-16 rounded-full bg-frost-500/20 blur-xl" />
        <div className="absolute w-12 h-12 rounded-full border border-frost-500/50 flex items-center justify-center bg-[#0a0a0a] z-10">
          <div className="w-4 h-4 rounded-full bg-frost-500 shadow-[0_0_15px_rgba(93,173,226,0.8)]" />
        </div>

        {/* Circular path */}
        <div className="absolute w-44 h-44 rounded-full border border-dashed border-white/10 animate-[spin_40s_linear_infinite]" />

        {/* Nodes */}
        {nodes.map((node, i) => {
          const angle = (i * (360 / nodes.length)) * (Math.PI / 180) - Math.PI / 2;
          const radius = 88; // 44 * 2
          const x = Math.cos(angle) * radius;
          const y = Math.sin(angle) * radius;

          return (
            <div
              key={node.id}
              className="absolute flex flex-col items-center justify-center group cursor-pointer z-20"
              style={{ transform: `translate(${x}px, ${y}px)` }}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
            >
              <div className={`w-9 h-9 rounded-full border flex items-center justify-center bg-[#0a0a0a] transition-all duration-300 ${hoveredNode === node.id ? 'border-frost-500 shadow-[0_0_15px_rgba(93,173,226,0.5)] scale-110' : 'border-white/20'}`}>
                <span className={`text-[11px] font-display ${hoveredNode === node.id ? 'text-frost-500' : 'text-gray-500'}`}>{node.id}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Description text */}
      <div className="absolute bottom-[-15px] left-0 right-0 text-center h-12">
        <p className={`text-xs font-display tracking-widest uppercase text-frost-400 transition-opacity duration-300 ${hoveredNode ? 'opacity-100' : 'opacity-0'}`}>
          {hoveredNode ? nodes.find(n => n.id === hoveredNode)?.title : 'Hover a phase'}
        </p>
        <p className={`text-[10px] text-gray-400 transition-opacity duration-300 mt-1 ${hoveredNode ? 'opacity-100' : 'opacity-0'}`}>
          {hoveredNode ? nodes.find(n => n.id === hoveredNode)?.desc : ''}
        </p>
      </div>
    </div>
  );
};

export default function App() {
  const { scrollYProgress } = useScroll();
  const y = useTransform(scrollYProgress, [0, 1], ['0%', '50%']);
  const opacity = useTransform(scrollYProgress, [0, 0.2], [1, 0]);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [trailerOpen, setTrailerOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setLightboxIndex(null);
        setTrailerOpen(false);
      }
      if (lightboxIndex === null) return;
      if (e.key === 'ArrowLeft') setLightboxIndex((prev) => (prev !== null && prev > 0 ? prev - 1 : GALLERY_IMAGES.length - 1));
      if (e.key === 'ArrowRight') setLightboxIndex((prev) => (prev !== null && prev < GALLERY_IMAGES.length - 1 ? prev + 1 : 0));
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [lightboxIndex]);

  return (
    <div className="min-h-screen bg-[#050505] text-white selection:bg-frost-900 selection:text-white font-sans">
      <Particles />

      {/* Navigation (Action/Centered) */}
      <nav className="fixed top-0 left-0 right-0 z-50 px-4 md:px-8 pt-4 pb-4 md:pt-12 md:pb-6 flex items-center justify-center md:justify-between bg-gradient-to-b from-black/90 via-black/50 to-transparent backdrop-blur-sm">
        {/* Left spacer for flex balance */}
        <div className="w-48 hidden lg:block"></div>

        {/* Center Group */}
        <div className="md:absolute md:left-1/2 md:-translate-x-1/2 flex items-center gap-4 md:gap-8 lg:gap-12 w-max md:mt-6">
          <div className="hidden md:flex items-center space-x-6 lg:space-x-8 font-display text-lg lg:text-xl tracking-widest uppercase text-gray-400">
            <a href="#concept" className="hover:text-frost-500 transition-colors">Concept</a>
            <a href="#host" className="hover:text-frost-500 transition-colors">The Host</a>
          </div>

          <div
            className="flex-shrink-0 z-10 cursor-pointer hover:scale-105 transition-transform duration-300"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          >
            <img src="https://thelastshelter.s3.us-east-2.amazonaws.com/logo-tls.png" alt="The Last Shelter" className="w-32 md:w-64 lg:w-[380px] h-auto object-contain drop-shadow-2xl md:translate-y-4" />
          </div>

          <div className="hidden md:flex items-center space-x-6 lg:space-x-8 font-display text-lg lg:text-xl tracking-widest uppercase text-gray-400">
            <a href="#partnerships" className="hover:text-frost-500 transition-colors">Partnerships</a>
            <a href="#gallery" className="hover:text-frost-500 transition-colors">Gallery</a>
          </div>
        </div>

        {/* Right Button */}
        <div className="hidden xl:block z-10 md:mt-6">
          <a href="https://www.youtube.com/@thelastsheltertv" target="_blank" rel="noopener noreferrer" className="btn-cinematic text-lg lg:text-xl py-2 px-6">
            Watch Now
          </a>
        </div>
      </nav>

      {/* 1. HERO SECTION */}
      <section id="hero" className="relative min-h-screen snap-start flex flex-col justify-center pt-32 md:pt-48 lg:pt-56 pb-12 overflow-hidden">
        {/* Background Video with Parallax */}
        <motion.div
          style={{ y, opacity }}
          className="absolute inset-0 z-0"
        >
          {/* Reduced black overlay: gradient on the left for text, and bottom for blending */}
          <div className="absolute inset-0 bg-gradient-to-t lg:bg-gradient-to-r from-[#050505] via-[#050505]/80 lg:via-[#050505]/60 to-transparent w-full lg:w-3/4 z-10" />
          <div className="absolute bottom-0 left-0 right-0 h-1/3 bg-gradient-to-t from-[#050505] to-transparent z-10" />
          <video
            autoPlay
            loop
            muted
            playsInline
            className="w-full h-full object-cover opacity-90"
          >
            <source src="https://thelastshelter.s3.us-east-2.amazonaws.com/video-web-test.mp4" type="video/mp4" />
          </video>
        </motion.div>

        <div className="container mx-auto px-6 relative z-20 -mt-4 md:-mt-10 lg:-mt-20">
          <div className="flex flex-col-reverse lg:grid lg:grid-cols-2 gap-8 lg:gap-12 items-center">

            {/* Left: Headline & Manifesto */}
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 1, delay: 0.2 }}
              className="flex flex-col space-y-6 lg:space-y-8 text-center lg:text-left"
            >
              <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-display text-white uppercase tracking-tight leading-[0.9]">
                THE WORLD’S FIRST <br />
                <span className="text-frost-500">AI-BUILT</span><br />
                SURVIVAL SHOW
              </h1>

              <div className="space-y-2 font-display text-lg sm:text-xl md:text-2xl text-white uppercase tracking-wide">
                <p className="text-frost-500">A NEW ERA OF SURVIVAL STORYTELLING</p>
              </div>

              <p className="text-sm sm:text-base md:text-lg text-white font-light leading-relaxed max-w-lg mx-auto lg:mx-0">
                A new kind of filmmaking powered by AI.<br />
                No cameras. No crew. No limits.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 pt-2 lg:pt-4 justify-center lg:justify-start">
                <a href="https://www.youtube.com/@thelastsheltertv" target="_blank" rel="noopener noreferrer" className="btn-cinematic btn-cinematic-primary btn-diamond text-sm sm:text-base inline-flex items-center justify-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="w-5 h-5 flex-shrink-0">
                    <path fill="#FF0000" d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814z" />
                    <path fill="#ffffff" d="M9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                  </svg>
                  Watch on YouTube
                </a>
                <a href="mailto:info@origostudios.ai" className="btn-cinematic btn-diamond inline-flex items-center justify-center text-sm sm:text-base">
                  Become a Partner
                </a>
              </div>
            </motion.div>

            {/* Right: Trailer Embed */}
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 1, delay: 0.6 }}
              className="relative group w-full max-w-2xl mx-auto"
            >
              <div className="absolute -inset-1 bg-gradient-to-r from-frost-900 to-frost-600 opacity-40 blur-xl group-hover:opacity-60 transition-opacity duration-500"></div>
              <div className="relative aspect-video bg-black border border-white/10 flex items-center justify-center overflow-hidden cursor-pointer" onClick={() => setTrailerOpen(true)}>
                <img src="https://thelastshelter.s3.us-east-2.amazonaws.com/cover-video-landing.png" alt="Trailer Thumbnail" className="absolute inset-0 w-full h-full object-cover opacity-90 group-hover:scale-105 transition-transform duration-700" />
                <div className="absolute inset-0 bg-black/20 group-hover:bg-transparent transition-colors duration-500" />
                <div className="relative z-10 flex flex-col items-center gap-4">
                  <button className="w-20 h-20 md:w-24 md:h-24 rounded-full bg-black/60 border-2 border-frost-500 flex items-center justify-center backdrop-blur-sm group-hover:bg-frost-500/40 transition-colors shadow-[0_0_30px_rgba(93,173,226,0.3)]">
                    <Play className="w-8 h-8 md:w-10 md:h-10 text-frost-500 ml-2" />
                  </button>
                  <span className="font-display tracking-[0.2em] text-white uppercase text-sm drop-shadow-md">Play Trailer</span>
                </div>
              </div>
            </motion.div>

          </div>
        </div>
      </section>

      {/* 2. THE CONCEPT / SYNOPSIS */}
      <section id="concept" className="min-h-screen snap-start relative z-10 bg-[#050505] overflow-hidden flex flex-col justify-center py-20">
        {/* Background Video */}
        <div className="absolute inset-0 z-0">
          {/* Reduced overlay: only top and bottom gradients for blending, center is mostly clear */}
          <div className="absolute top-0 left-0 right-0 h-32 bg-gradient-to-b from-[#050505] to-transparent z-10" />
          <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#050505] to-transparent z-10" />
          <div className="absolute inset-0 bg-[#050505]/30 z-10" /> {/* Light overall tint */}
          <video
            autoPlay
            loop
            muted
            playsInline
            className="w-full h-full object-cover opacity-90"
          >
            <source src="https://thelastshelter.s3.us-east-2.amazonaws.com/web-the-concept-video.mp4" type="video/mp4" />
          </video>
        </div>

        <div className="container mx-auto px-6 max-w-5xl relative z-20">
          <SectionHeader title="What is The Last Shelter?" subtitle="The Concept" />

          <div className="text-center max-w-3xl mx-auto mb-16">
            <p className="text-sm sm:text-base md:text-lg leading-relaxed text-white font-light mb-4 md:mb-8">
              A cinematic survival series where each episode follows a new protagonist pushed to the edge of nature.<br />
              Freezing winters. Abandoned cabins. Total isolation.
            </p>
            <p className="text-sm sm:text-base md:text-lg leading-relaxed text-white font-light">
              Crafted with artificial intelligence, The Last Shelter redefines survival storytelling blending hyperrealism and documentary-style narration into a new era of shows.
            </p>
          </div>
        </div>

        {/* Marquee Slider (Full Width) */}
        <div className="w-full relative pb-8 z-20">
          {/* Fade edges */}
          <div className="absolute top-0 bottom-0 left-0 w-16 md:w-48 bg-gradient-to-r from-[#050505] to-transparent z-10 pointer-events-none" />
          <div className="absolute top-0 bottom-0 right-0 w-16 md:w-48 bg-gradient-to-l from-[#050505] to-transparent z-10 pointer-events-none" />

          <div className="animate-marquee flex w-max">
            {[...Array(2)].map((_, arrayIndex) => (
              <div key={arrayIndex} className="flex gap-6 pr-6">
                {/* Card 1: Audience */}
                <div className="w-[280px] md:w-[380px] h-[380px] md:h-[450px] flex-shrink-0 bg-[#0a0a0a] border border-white/10 rounded-3xl p-6 md:p-8 flex flex-col items-center relative overflow-hidden group hover:border-frost-500/30 transition-colors">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-frost-500/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 group-hover:bg-frost-500/10 transition-colors" />
                  <div className="h-20 md:h-24 flex flex-col items-center justify-start w-full text-center">
                    <h3 className="text-xl md:text-2xl font-display text-white mb-2 uppercase tracking-wide">The Audience</h3>
                    <p className="text-gray-400 text-xs md:text-sm">The perfect intersection of three massive YouTube audiences.</p>
                  </div>
                  <div className="flex-1 w-full flex items-center justify-center scale-90 md:scale-100">
                    <VennDiagram />
                  </div>
                </div>

                {/* Card 2: TV Show Format */}
                <div className="w-[280px] md:w-[380px] h-[380px] md:h-[450px] flex-shrink-0 bg-[#0a0a0a] border border-white/10 rounded-3xl p-6 md:p-8 flex flex-col items-center relative overflow-hidden group hover:border-frost-500/30 transition-colors">
                  <div className="h-20 md:h-24 flex flex-col items-center justify-start w-full text-center">
                    <h3 className="text-xl md:text-2xl font-display text-white mb-2 uppercase tracking-wide">TV Show Format</h3>
                    <p className="text-gray-400 text-xs md:text-sm">Structured for maximum retention and narrative payoff.</p>
                  </div>
                  <div className="flex-1 w-full flex items-center justify-center scale-90 md:scale-100">
                    <FormatFlow />
                  </div>
                </div>

                {/* Card 3: Weekly Episodes */}
                <div className="w-[280px] md:w-[380px] h-[380px] md:h-[450px] flex-shrink-0 bg-[#0a0a0a] border border-white/10 rounded-3xl p-6 md:p-8 flex flex-col items-center relative overflow-hidden group hover:border-frost-500/30 transition-colors">
                  <div className="h-20 md:h-24 flex flex-col items-center justify-start w-full text-center">
                    <h3 className="text-xl md:text-2xl font-display text-white mb-2 uppercase tracking-wide">Weekly Episodes</h3>
                    <p className="text-gray-400 text-xs md:text-sm">Consistent, high-quality delivery.</p>
                  </div>
                  <div className="flex-1 w-full flex items-center justify-center scale-90 md:scale-100">
                    <div className="flex flex-col items-center gap-2 md:gap-4">
                      <div className="text-8xl md:text-9xl font-display text-transparent bg-clip-text bg-gradient-to-b from-white to-gray-500 leading-none drop-shadow-[0_0_15px_rgba(93,173,226,0.3)]">1</div>
                      <div className="text-center mt-2">
                        <div className="text-2xl font-display text-frost-500 uppercase tracking-wider">Episode / Week</div>
                        <div className="text-gray-400 mt-1">30-40 Minutes</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card 4: AI Technology */}
                <div className="w-[280px] md:w-[380px] h-[380px] md:h-[450px] flex-shrink-0 bg-[#0a0a0a] border border-white/10 rounded-3xl p-6 md:p-8 flex flex-col items-center relative overflow-hidden group hover:border-frost-500/30 transition-colors">
                  <div className="h-20 md:h-24 flex flex-col items-center justify-start w-full text-center">
                    <h3 className="text-xl md:text-2xl font-display text-white mb-2 uppercase tracking-wide">AI Technology</h3>
                    <p className="text-gray-400 text-xs md:text-sm">A new era of production pipeline.</p>
                  </div>
                  <div className="flex-1 w-full flex items-center justify-center scale-90 md:scale-100">
                    <CircularFlow />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 4. MEET THE HOST */}
      <section id="host" className="min-h-screen snap-start relative z-10 overflow-hidden flex flex-col justify-center py-20 bg-[#050505]">
        {/* Background Video */}
        <div className="absolute inset-0 z-0">
          <div className="absolute top-0 left-0 right-0 h-32 bg-gradient-to-b from-[#050505] to-transparent z-10" />
          <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#050505] to-transparent z-10" />
          <div className="absolute inset-0 bg-[#050505]/30 z-10" />
          <video
            autoPlay
            loop
            muted
            playsInline
            className="w-full h-full object-cover opacity-60"
          >
            <source src="https://thelastshelter.s3.us-east-2.amazonaws.com/jack-web.mp4" type="video/mp4" />
          </video>
        </div>

        <div className="container mx-auto px-6 max-w-6xl relative z-20">
          <div className="flex flex-col lg:flex-row items-center gap-16">
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="w-full lg:w-1/2 relative flex"
            >
              <div className="absolute inset-0 border-2 border-frost-500/20 z-0 translate-x-4 translate-y-4" />
              <img
                src="https://thelastshelter.s3.us-east-2.amazonaws.com/jack-website.png"
                alt="Jack Harlan"
                className="w-full h-auto object-cover object-top relative z-10 shadow-[0_0_30px_rgba(0,0,0,0.8)]"
              />
              <div className="absolute bottom-0 left-0 right-0 h-1/2 bg-gradient-to-t from-[#050505] to-transparent z-20" />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="w-full lg:w-1/2 space-y-8"
            >
              <div>
                <p className="text-frost-500 font-display tracking-[0.1em] text-sm uppercase mb-2 md:mb-4 drop-shadow-md">The Host</p>
                <h2 className="text-4xl md:text-5xl lg:text-6xl font-display text-gradient-action uppercase tracking-tight mb-4 md:mb-8 drop-shadow-lg">
                  Meet Jack Harlan
                </h2>
              </div>

              <div className="space-y-4 md:space-y-6 text-sm sm:text-base md:text-lg text-white font-light leading-relaxed drop-shadow-md">
                <p className="font-display text-base sm:text-lg md:text-xl text-white uppercase tracking-wide">
                  More than a host, Jack is the voice that guides you through the unknown.
                </p>
                <p>
                  A survival expert who has spent years studying extreme environments and advising elite operators on wilderness survival strategies. In each episode, Jack breaks down the decisions that mean the difference between life and death — helping the audience understand not just what happens, but why it matters.
                </p>
                <p>
                  He introduces the challenge, decodes every survival choice and reveals the human instinct behind the wilderness.
                </p>
                <div className="pt-4 md:pt-6 border-t border-white/10">
                  <p className="font-display text-gray-300 uppercase tracking-wide text-xs sm:text-sm">
                    The first AI-generated host in cinematic survival television.
                  </p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* 5. PARTNERSHIPS */}
      <section id="partnerships" className="min-h-screen snap-start flex flex-col pt-32 md:pt-64 lg:pt-80 pb-20 relative z-10 bg-[#0a0a0a] border-y border-white/5">
        <div className="container mx-auto px-6 max-w-6xl">
          <SectionHeader title="PARTNER THE FUTURE OF CONTENT" subtitle="Partnerships" />

          <div className="text-center max-w-3xl mx-auto mb-12 md:mb-20">
            <p className="text-sm sm:text-base md:text-lg leading-relaxed text-white font-light mb-4 md:mb-6">
              The Last Shelter offers premium brand integrations inside a cinematic survival universe.
            </p>
            <p className="text-sm sm:text-base md:text-lg leading-relaxed text-white font-light">
              From organic product placements to season-level partnerships, we build collaborations that feel real, immersive and unforgettable.
            </p>
          </div>

          <div className="space-y-24 mb-20">
            {/* Block 1 */}
            <div className="flex flex-col md:flex-row items-center gap-12">
              <div className="flex-1 space-y-6">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-frost-500/20 text-frost-400 font-display text-xl mb-4">1</div>
                <h3 className="text-2xl md:text-3xl font-display text-white uppercase tracking-wide">INTEGRATED PRODUCT PLACEMENT</h3>
                <p className="text-sm sm:text-base md:text-lg text-gray-300 font-light leading-relaxed">
                  Organic integration of jackets, outdoor gear, tools, survival equipment and apparel directly into the storyline.
                </p>
                <p className="text-sm sm:text-base md:text-lg text-gray-300 font-light leading-relaxed">
                  Visible in real-use survival scenarios.<br />
                  No forced advertising. Pure immersion.
                </p>
              </div>
              <div className="flex-1 w-full">
                <div className="aspect-video bg-black border border-white/10 rounded-2xl overflow-hidden relative shadow-[0_0_40px_rgba(93,173,226,0.1)]">
                  <img src="https://thelastshelter.s3.us-east-2.amazonaws.com/product-placement-sample.png" alt="Integrated Product Placement" className="w-full h-full object-cover opacity-80" />
                </div>
              </div>
            </div>

            {/* Block 2 */}
            <div className="flex flex-col md:flex-row-reverse items-center gap-12">
              <div className="flex-1 space-y-6">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-frost-500/20 text-frost-400 font-display text-xl mb-4">2</div>
                <h3 className="text-2xl md:text-3xl font-display text-white uppercase tracking-wide">EPISODE SPONSORSHIP</h3>
                <p className="text-sm sm:text-base md:text-lg text-gray-300 font-light leading-relaxed">
                  Sponsor a single episode or character journey.
                </p>
                <div className="space-y-2">
                  <p className="text-sm sm:text-base md:text-lg text-white font-medium">Includes:</p>
                  <ul className="space-y-2 text-gray-300 font-light text-sm sm:text-base md:text-lg">
                    <li className="flex items-center gap-3"><div className="w-1.5 h-1.5 bg-frost-500 rounded-full" />Host mention</li>
                    <li className="flex items-center gap-3"><div className="w-1.5 h-1.5 bg-frost-500 rounded-full" />Visual branding integration</li>
                    <li className="flex items-center gap-3"><div className="w-1.5 h-1.5 bg-frost-500 rounded-full" />Description + pinned comment placement</li>
                    <li className="flex items-center gap-3"><div className="w-1.5 h-1.5 bg-frost-500 rounded-full" />Cross-platform amplification</li>
                  </ul>
                </div>
              </div>
              <div className="flex-1 w-full">
                <div className="aspect-video bg-black border border-white/10 rounded-2xl overflow-hidden relative shadow-[0_0_40px_rgba(93,173,226,0.1)]">
                  <img src="https://thelastshelter.s3.us-east-2.amazonaws.com/episode-sponsored.png" alt="Episode Sponsorship" className="w-full h-full object-cover opacity-80" />
                </div>
              </div>
            </div>

            {/* Block 3 */}
            <div className="flex flex-col md:flex-row items-center gap-12">
              <div className="flex-1 space-y-6">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-frost-500/20 text-frost-400 font-display text-xl mb-4">3</div>
                <h3 className="text-2xl md:text-3xl font-display text-white uppercase tracking-wide">TECHNOLOGY PARTNER</h3>
                <p className="text-sm sm:text-base md:text-lg text-gray-300 font-light leading-relaxed">
                  Power the future of AI-driven filmmaking.
                </p>
                <div className="space-y-2">
                  <p className="text-sm sm:text-base md:text-lg text-white font-medium">Ideal for:</p>
                  <ul className="space-y-2 text-gray-300 font-light text-sm sm:text-base md:text-lg">
                    <li className="flex items-center gap-3"><div className="w-1.5 h-1.5 bg-frost-500 rounded-full" />AI companies</li>
                    <li className="flex items-center gap-3"><div className="w-1.5 h-1.5 bg-frost-500 rounded-full" />Software platforms</li>
                    <li className="flex items-center gap-3"><div className="w-1.5 h-1.5 bg-frost-500 rounded-full" />Hardware partners</li>
                    <li className="flex items-center gap-3"><div className="w-1.5 h-1.5 bg-frost-500 rounded-full" />Cloud / GPU providers</li>
                  </ul>
                </div>
                <p className="text-sm sm:text-base md:text-lg text-frost-500 font-medium leading-relaxed pt-2">
                  Be credited as the technological backbone behind the world’s first AI-built survival series.
                </p>
              </div>
              <div className="flex-1 w-full">
                <div className="aspect-video bg-black border border-white/10 rounded-2xl overflow-hidden relative shadow-[0_0_40px_rgba(93,173,226,0.1)]">
                  <img src="https://thelastshelter.s3.us-east-2.amazonaws.com/sponsors.jpeg" alt="Technology Partner" className="w-full h-full object-cover opacity-80" />
                </div>
              </div>
            </div>
          </div>

          <div className="text-center">
            <a href="mailto:info@origostudios.ai" className="btn-cinematic btn-cinematic-primary btn-diamond inline-flex items-center justify-center">
              Become a Partner
            </a>
          </div>
        </div>
      </section>

      {/* 6. GALLERY */}
      <section id="gallery" className="min-h-screen snap-start flex flex-col justify-center py-20 relative z-10">
        <div className="container mx-auto px-6">
          <SectionHeader title="Cinematic Frames" subtitle="Gallery" />

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-16">
            {GALLERY_IMAGES.map((src, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="relative aspect-video overflow-hidden group border border-white/10 cursor-pointer"
                onClick={() => setLightboxIndex(i)}
              >
                <img
                  src={src}
                  alt={`Cinematic Frame ${i + 1}`}
                  className="w-full h-full object-cover group-hover:scale-110 transition-all duration-700"
                />
                <div className="absolute inset-0 bg-black/10 group-hover:bg-transparent transition-colors duration-500" />
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* 8. FINAL CTA */}
      <section id="cta" className="min-h-screen snap-start flex flex-col justify-center py-20 relative z-10 bg-black overflow-hidden">
        {/* Background Video */}
        <div className="absolute inset-0 z-0 opacity-40">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(93,173,226,0.15)_0%,transparent_70%)] z-10" />
          <video
            autoPlay
            loop
            muted
            playsInline
            className="w-full h-full object-cover"
          >
            <source src="https://thelastshelter.s3.us-east-2.amazonaws.com/wilderness.mp4" type="video/mp4" />
          </video>
        </div>

        <div className="container mx-auto px-6 text-center relative z-10">
          <motion.h2
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="text-4xl sm:text-5xl md:text-7xl lg:text-8xl font-display text-white uppercase tracking-tighter mb-10 md:mb-16 leading-[0.9]"
          >
            The Wilderness<br />
            <span className="text-gradient-action">Is Waiting.</span>
          </motion.h2>

          <div className="flex flex-col sm:flex-row justify-center gap-6">
            <a href="https://www.youtube.com/@thelastsheltertv" target="_blank" rel="noopener noreferrer" className="btn-cinematic btn-cinematic-primary btn-diamond text-lg">
              WATCH THE EPISODES
            </a>
            <a href="mailto:info@origostudios.ai" className="btn-cinematic btn-diamond text-lg inline-flex items-center justify-center">
              Become a Partner
            </a>
          </div>
        </div>
      </section>

      {/* 9. FOOTER */}
      <footer className="snap-start py-12 bg-black border-t border-white/10 relative z-10">
        <div className="container mx-auto px-6 flex flex-col items-center">
          <button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <img src="https://thelastshelter.s3.us-east-2.amazonaws.com/logo-tls.png" alt="The Last Shelter" className="w-48 mb-8 opacity-50 hover:opacity-100 transition-opacity" />
          </button>

          <div className="flex space-x-8 mb-8 items-center justify-center">
            <a href="https://www.youtube.com/@thelastsheltertv" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-frost-500 transition-colors"><Youtube className="w-6 h-6" /></a>
            <a href="https://x.com/JackHarlanTLS" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-frost-500 transition-colors">
              <svg viewBox="0 0 24 24" className="w-[22px] h-[22px] fill-current" aria-hidden="true">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
              </svg>
            </a>
            <a href="mailto:info@origostudios.ai" className="text-gray-500 hover:text-frost-500 transition-colors"><Mail className="w-6 h-6" /></a>
          </div>

          <div className="text-center space-y-2 text-xs text-gray-600 font-display tracking-widest uppercase">
            <p>Produced by <a href="https://origostudios.ai" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-frost-500 transition-colors">Origo Studios</a></p>
            <p>&copy; {new Date().getFullYear()} The Last Shelter. All rights reserved.</p>
          </div>
        </div>
      </footer>

      {/* Lightbox */}
      {lightboxIndex !== null && (
        <div
          className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-sm flex items-center justify-center"
          onClick={() => setLightboxIndex(null)}
        >
          <button
            className="absolute top-6 right-6 text-white/70 hover:text-white transition-colors"
            onClick={() => setLightboxIndex(null)}
          >
            <X className="w-8 h-8" />
          </button>

          <button
            className="absolute left-6 top-1/2 -translate-y-1/2 text-white/50 hover:text-white transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              setLightboxIndex((prev) => (prev !== null && prev > 0 ? prev - 1 : GALLERY_IMAGES.length - 1));
            }}
          >
            <ChevronLeft className="w-12 h-12" />
          </button>

          <img
            src={GALLERY_IMAGES[lightboxIndex]}
            alt={`Gallery image ${lightboxIndex + 1}`}
            className="max-w-[90vw] max-h-[90vh] object-contain"
            onClick={(e) => e.stopPropagation()}
          />

          <button
            className="absolute right-6 top-1/2 -translate-y-1/2 text-white/50 hover:text-white transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              setLightboxIndex((prev) => (prev !== null && prev < GALLERY_IMAGES.length - 1 ? prev + 1 : 0));
            }}
          >
            <ChevronRight className="w-12 h-12" />
          </button>
        </div>
      )}

      {/* Trailer Modal */}
      {trailerOpen && (
        <div
          className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-sm flex items-center justify-center"
          onClick={() => setTrailerOpen(false)}
        >
          <button
            className="absolute top-6 right-6 text-white/70 hover:text-white transition-colors z-20"
            onClick={() => setTrailerOpen(false)}
          >
            <X className="w-8 h-8" />
          </button>
          <div
            className="relative w-[90vw] max-w-5xl aspect-video"
            onClick={(e) => e.stopPropagation()}
          >
            <iframe
              src="https://www.youtube.com/embed/pp7UDvFRlxg?autoplay=1&rel=0"
              title="The Last Shelter Trailer"
              className="w-full h-full rounded-lg"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        </div>
      )}
    </div>
  );
}
