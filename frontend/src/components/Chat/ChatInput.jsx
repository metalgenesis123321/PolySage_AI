// src/components/Chat/ChatInput.jsx
import React, { useRef, useEffect } from 'react';
import { Send, Loader2, Mic, MicOff } from 'lucide-react';

const ChatInput = ({ 
  input, 
  setInput, 
  onSend, 
  loading, 
  isListening,
  onToggleVoice,
  marketId,
  setMarketId,
  darkMode 
}) => {
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [input]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className={`relative backdrop-blur-xl ${
      darkMode 
        ? 'bg-gray-900/80 border-gray-700/50' 
        : 'bg-white/80 border-blue-200/50'
    } border-t px-6 py-6`}>
      <div className="max-w-4xl mx-auto">
        {/* Market ID Input */}
        {/* <div className="mb-3">
          <input
            type="text"
            value={marketId}
            onChange={(e) => setMarketId(e.target.value)}
            placeholder="Market ID (optional - for dashboard generation)"
            className={`w-full px-4 py-2 text-sm placeholder-lg overflow-hidden ${
              darkMode 
                ? 'bg-gray-800/50 border-gray-600 text-gray-200 placeholder-gray-500' 
                : 'bg-blue-50/50 border-blue-200 text-gray-800 placeholder-gray-400'
            } border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400/50 transition-all`}
          />
        </div> */}

        {/* Main Input Area */}
        <div className="relative">
          <div className="flex gap-3 items-end">
            {/* Voice Input Button */}
            <button
              onClick={onToggleVoice}
              className={`group p-4 rounded-2xl font-semibold flex items-center justify-center transition-all shadow-lg ${
                isListening
                  ? 'bg-gradient-to-br from-red-400 to-pink-500 hover:from-red-500 hover:to-pink-600 text-white shadow-red-300/50 animate-pulse'
                  : darkMode 
                    ? 'bg-gray-700 hover:bg-gray-600 border border-gray-600 text-gray-300'
                    : 'bg-blue-100 hover:bg-blue-200 border border-blue-200 text-blue-700 hover:text-blue-800'
              }`}
              title={isListening ? 'Stop listening' : 'Start voice input'}
            >
              {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>

            {/* Text Input */}
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about Polymarket or request market analysis..."
                className={`w-full px-4 py-2.5 ${
                  darkMode 
                    ? 'bg-gray-800/90 border-gray-600 text-gray-200 placeholder-gray-500' 
                    : 'bg-white/90 border-blue-200 text-gray-800 placeholder-gray-400'
                } backdrop-blur-sm border focus:border-blue-400 text-lg rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400/50 resize-none transition-all shadow-md`}
                rows="1"
                style={{
                  height: '60px',    // fixed height, adjust as needed
    maxHeight: '150px',
    overflow: 'hidden',
                }}
              />
              <div className={`absolute bottom-2 right-2 text-sm ${
                darkMode ? 'text-gray-500' : 'text-gray-400'
              }`}>
                {input.length}
              </div>
            </div>

            {/* Send Button */}
            <button
              onClick={onSend}
              disabled={loading || !input.trim()}
              className={`group p-4 ${
                darkMode 
                  ? 'bg-gradient-to-br from-blue-600 via-cyan-600 to-sky-700 hover:from-blue-700 hover:via-cyan-700 hover:to-sky-800' 
                  : 'bg-gradient-to-br from-blue-400 via-cyan-400 to-sky-500 hover:from-blue-500 hover:via-cyan-500 hover:to-sky-600'
              } disabled:from-gray-300 disabled:to-gray-400 text-white rounded-2xl font-semibold flex items-center justify-center transition-all shadow-lg shadow-blue-300/50 hover:shadow-blue-400/60 disabled:shadow-none disabled:cursor-not-allowed`}
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              )}
            </button>
          </div>
        </div>

        {/* Status Bar */}
        <div className={`flex items-center justify-between mt-4 text-xs ${
          darkMode ? 'text-gray-500' : 'text-gray-500'
        }`}>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              Connected
            </span>
            {marketId && (
              <>
                <span>•</span>
                <span className={`${
                  darkMode ? 'text-blue-400' : 'text-blue-600'
                } font-medium`}>
                  Market ID Set
                </span>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span>Press Enter to send</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInput;