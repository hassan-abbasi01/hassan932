import { Scissors, Github, Twitter, Youtube, Mail } from 'lucide-react';

const Footer = () => {
  return (
    <footer className="bg-gray-900 text-white py-12 px-4">
      <div className="container mx-auto max-w-6xl">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="md:col-span-1">
            <div className="flex items-center mb-4">
              <Scissors className="text-purple-400 mr-2" size={24} />
              <span className="text-xl font-bold">
                Snip<span className="text-teal-400">X</span>
              </span>
            </div>
            <p className="text-gray-400 mb-6">
              Your gateway to simplified video editing, subtitling, and summarization.
            </p>
            <div className="flex space-x-4">
              <a href="#" className="text-gray-400 hover:text-white transition-colors">
                <Twitter size={20} />
              </a>
              <a href="#" className="text-gray-400 hover:text-white transition-colors">
                <Github size={20} />
              </a>
              <a
                href="https://www.youtube.com/@HaseenVlogs"
                className="text-gray-400 hover:text-white transition-colors"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="YouTube"
              >
                <Youtube size={20} />
              </a>
              <a
                href="mailto:JAWADMANZOOR777@GMAIL.COM"
                className="text-gray-400 hover:text-white transition-colors"
                aria-label="Email"
              >
                <Mail size={20} />
              </a>
            </div>
          </div>
          
          <div className="md:col-span-1">
            <h3 className="text-lg font-semibold mb-4">Features</h3>
            <ul className="space-y-2">
              <li>
                <a 
                  href="/features?tab=audio" 
                  className="text-gray-400 hover:text-white transition-colors hover:text-purple-400"
                >
                  Voice Cutting
                </a>
              </li>
              <li>
                <a 
                  href="/features?tab=subtitles" 
                  className="text-gray-400 hover:text-white transition-colors hover:text-teal-400"
                >
                  Urdu Subtitling
                </a>
              </li>
              <li>
                <a 
                  href="/features?tab=summarization" 
                  className="text-gray-400 hover:text-white transition-colors hover:text-orange-400"
                >
                  Video Summarization
                </a>
              </li>
              <li>
                <a 
                  href="/features?tab=thumbnail" 
                  className="text-gray-400 hover:text-white transition-colors hover:text-red-400"
                >
                  Thumbnail Generation
                </a>
              </li>
              <li>
                <a 
                  href="/features?tab=enhancement" 
                  className="text-gray-400 hover:text-white transition-colors hover:text-green-400"
                >
                  Audio Enhancement
                </a>
              </li>
            </ul>
          </div>
          
          <div className="md:col-span-1">
            <h3 className="text-lg font-semibold mb-4">Resources</h3>
            <ul className="space-y-2">
              <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Documentation</a></li>
              <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Tutorials</a></li>
              <li><a href="#" className="text-gray-400 hover:text-white transition-colors">API Reference</a></li>
              <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Community</a></li>
              <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Support</a></li>
              <li><a href="/admin/login" className="text-purple-400 hover:text-purple-300 transition-colors font-medium">🔐 Admin Login</a></li>
            </ul>
          </div>
          
          <div className="md:col-span-1">
            <h3 className="text-lg font-semibold mb-4">Company</h3>
            <ul className="space-y-2">
              <li><a href="https://www.linkedin.com/in/jawadahmadfahad/" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-white transition-colors">About Us</a></li>
              <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Careers</a></li>
              <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Blog</a></li>
              <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Privacy Policy</a></li>
              <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Terms of Service</a></li>
            </ul>
          </div>
        </div>
        
        <div className="border-t border-gray-800 mt-12 pt-8 flex flex-col md:flex-row justify-between items-center">
          <p className="text-gray-500 text-sm">
            &copy; {new Date().getFullYear()} SnipX. All rights reserved.
          </p>
          <div className="mt-4 md:mt-0">
            <a href="#" className="text-gray-500 hover:text-white transition-colors text-sm">
              Privacy Policy
            </a>
            <span className="mx-2 text-gray-700">|</span>
            <a href="#" className="text-gray-500 hover:text-white transition-colors text-sm">
              Terms of Service
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;