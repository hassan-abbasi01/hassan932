import { ArrowRight, Play, Sparkles } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';

const Hero = () => {
  const navigate = useNavigate();
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
    
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({
        x: (e.clientX / window.innerWidth) * 100,
        y: (e.clientY / window.innerHeight) * 100,
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <section className="relative py-12 md:py-20 px-4 overflow-hidden bg-gradient-to-br from-slate-50 via-white to-purple-50">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Floating Orbs */}
        <div 
          className="absolute w-96 h-96 bg-gradient-to-r from-purple-400/20 to-pink-400/20 rounded-full blur-3xl animate-float"
          style={{
            top: '10%',
            left: '10%',
            transform: `translate(${mousePosition.x * 0.02}px, ${mousePosition.y * 0.02}px)`,
            transition: 'transform 0.3s ease-out'
          }}
        />
        <div 
          className="absolute w-80 h-80 bg-gradient-to-r from-blue-400/20 to-cyan-400/20 rounded-full blur-3xl animate-float-delayed"
          style={{
            top: '60%',
            right: '10%',
            transform: `translate(${mousePosition.x * -0.015}px, ${mousePosition.y * -0.015}px)`,
            transition: 'transform 0.3s ease-out'
          }}
        />
        <div 
          className="absolute w-64 h-64 bg-gradient-to-r from-indigo-400/20 to-purple-400/20 rounded-full blur-3xl animate-pulse-slow"
          style={{
            top: '30%',
            right: '30%',
            transform: `translate(${mousePosition.x * 0.01}px, ${mousePosition.y * 0.01}px)`,
            transition: 'transform 0.3s ease-out'
          }}
        />

        {/* Grid Pattern */}
        <div className="absolute inset-0 bg-grid-pattern opacity-5" />
        
        {/* Sparkle Elements */}
        <div className="absolute top-20 left-1/4 animate-sparkle">
          <Sparkles className="text-purple-400 w-6 h-6" />
        </div>
        <div className="absolute top-40 right-1/3 animate-sparkle-delayed">
          <Sparkles className="text-pink-400 w-4 h-4" />
        </div>
        <div className="absolute bottom-32 left-1/3 animate-sparkle-slow">
          <Sparkles className="text-blue-400 w-5 h-5" />
        </div>
      </div>

      <div className="container mx-auto max-w-6xl relative z-10">
        <div className="flex flex-col md:flex-row md:items-center md:gap-12">
          <div className={`md:w-1/2 mb-10 md:mb-0 transition-all duration-1000 ${
            isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
          }`}>
            {/* Badge */}
            <div className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-purple-100 to-pink-100 rounded-full text-purple-700 text-sm font-medium mb-6 animate-slide-in-left">
              <Sparkles className="w-4 h-4 mr-2" />
              AI-Powered Video Editing
            </div>

            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 mb-4 leading-tight">
              <span className="animate-text-reveal inline-block">Simplify Your</span>{' '}
              <span className="bg-gradient-to-r from-purple-600 via-pink-600 to-blue-600 bg-clip-text text-transparent animate-gradient-x">
                Video Editing
              </span>{' '}
              <span className="animate-text-reveal-delayed inline-block">Experience</span>
            </h1>
            
            <p className={`text-xl text-gray-600 mb-8 max-w-lg transition-all duration-1000 delay-300 ${
              isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
            }`}>
              Automated voice cutting, subtitling, and video summarization - all in one platform.
              Save time and create professional videos with ease.
            </p>
            
            <div className={`flex flex-col sm:flex-row gap-4 transition-all duration-1000 delay-500 ${
              isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
            }`}>
              <Link 
                to="/features" 
                className="group bg-gradient-to-r from-purple-600 to-pink-600 text-white px-8 py-4 rounded-xl hover:from-purple-700 hover:to-pink-700 transition-all duration-300 flex items-center justify-center gap-3 font-medium shadow-lg hover:shadow-xl transform hover:-translate-y-1 hover:scale-105"
              >
                <Play size={20} className="group-hover:scale-110 transition-transform duration-300" />
                Try Editor Now
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform duration-300" />
              </Link>
              
              <button 
                className="group border-2 border-purple-200 text-purple-700 px-8 py-4 rounded-xl hover:border-purple-300 hover:bg-purple-50 transition-all duration-300 font-medium transform hover:-translate-y-1"
                onClick={() => navigate('/Help')}
              >
                <span className="group-hover:scale-105 inline-block transition-transform duration-300">
                  Learn More
                </span>
              </button>
            </div>

            {/* Stats */}
            <div className={`flex items-center gap-8 mt-12 transition-all duration-1000 delay-700 ${
              isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
            }`}>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 animate-count-up">10K+</div>
                <div className="text-sm text-gray-600">Videos Processed</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 animate-count-up-delayed">50+</div>
                <div className="text-sm text-gray-600">Languages</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 animate-count-up-slow">99%</div>
                <div className="text-sm text-gray-600">Accuracy</div>
              </div>
            </div>
          </div>
          
          <div className={`md:w-1/2 transition-all duration-1000 delay-300 ${
            isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-8'
          }`}>
            <div className="relative group">
              {/* Main Image Container */}
              <div className="relative rounded-3xl overflow-hidden shadow-2xl transform group-hover:scale-105 transition-all duration-500 bg-gradient-to-br from-purple-100 to-pink-100">
                <img 
                  src="https://images.pexels.com/photos/2399840/pexels-photo-2399840.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=750&w=1260" 
                  alt="Video editing interface" 
                  className="w-full h-auto transform group-hover:scale-110 transition-transform duration-700"
                />
                
                {/* Overlay Gradient */}
                <div className="absolute inset-0 bg-gradient-to-tr from-purple-900/40 via-transparent to-pink-900/20"></div>
                
                {/* Floating UI Elements */}
                <div className="absolute top-6 left-6 bg-white/95 backdrop-blur-sm rounded-2xl p-4 shadow-lg animate-float-up">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
                    <span className="text-sm font-medium text-gray-800">AI Processing</span>
                  </div>
                  <div className="mt-2 text-xs text-gray-600">Analyzing audio patterns...</div>
                </div>

                <div className="absolute top-6 right-6 bg-white/95 backdrop-blur-sm rounded-2xl p-4 shadow-lg animate-float-up-delayed">
                  <div className="text-2xl font-bold text-purple-600">85%</div>
                  <div className="text-xs text-gray-600">Complete</div>
                </div>

                <div className="absolute bottom-6 left-6 right-6 bg-white/95 backdrop-blur-sm rounded-2xl p-4 shadow-lg animate-slide-up">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-purple-600 animate-pulse"></div>
                    <p className="text-sm font-medium text-purple-900">Processing Complete</p>
                  </div>
                  <p className="text-xs text-gray-600">
                    Video enhanced with AI subtitles and audio optimization
                  </p>
                  <div className="mt-3 flex gap-2">
                    <div className="h-1 bg-purple-200 rounded-full flex-1">
                      <div className="h-1 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full w-4/5 animate-progress"></div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Decorative Elements */}
              <div className="absolute -top-4 -right-4 w-24 h-24 bg-gradient-to-r from-yellow-400 to-orange-400 rounded-full opacity-20 animate-bounce-slow"></div>
              <div className="absolute -bottom-6 -left-6 w-32 h-32 bg-gradient-to-r from-blue-400 to-cyan-400 rounded-full opacity-20 animate-pulse-slow"></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;