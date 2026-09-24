import { useState } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

const API_BASE_URL = 'http://127.0.0.1:8000';

export default function App() {
  const [url, setUrl] = useState('');
  const [videoId, setVideoId] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);

  // Handle Video Analysis
  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!url) return;

    setIsAnalyzing(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/analyze`, { url });
      setVideoId(response.data.video_id);
      setMessages([
        {
          sender: 'system',
          text: `Video analyzed successfully! Extracted ${response.data.chunks_count} chunks. Ask me anything about the video!`,
        },
      ]);
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to analyze video URL.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle Asking Questions
  const handleQuery = async (e) => {
    e.preventDefault();
    if (!query || !videoId) return;

    const userMessage = query;
    setQuery('');
    setMessages((prev) => [...prev, { sender: 'user', text: userMessage }]);
    setIsQuerying(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/query`, {
        video_id: videoId,
        query: userMessage,
      });

      setMessages((prev) => [
        ...prev,
        { sender: 'assistant', text: response.data.answer },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { sender: 'assistant', text: 'Error fetching response from server.' },
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100 font-sans">
      {/* Sidebar: Video Input & Embedded Player */}
      <div className="w-1/3 border-r border-slate-800 p-6 flex flex-col gap-6 bg-slate-950">
        <div>
          <h1 className="text-2xl font-bold text-indigo-400 flex items-center gap-2">
            🎬 QueryClip
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Time-Aware YouTube RAG Search Assistant
          </p>
        </div>

        <form onSubmit={handleAnalyze} className="flex flex-col gap-3">
          <label className="text-sm font-medium text-slate-300">
            YouTube Video Link
          </label>
          <input
            type="text"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={isAnalyzing}
            className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 font-medium text-sm rounded-lg transition"
          >
            {isAnalyzing ? 'Indexing Video...' : 'Analyze Video'}
          </button>
        </form>

        {videoId && (
          <div className="flex-1 flex flex-col gap-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Active Video
            </span>
            <div className="aspect-video w-full rounded-lg overflow-hidden border border-slate-800">
              <iframe
                src={`https://www.youtube.com/embed/${videoId}`}
                title="YouTube Video"
                className="w-full h-full"
                allowFullScreen
              />
            </div>
          </div>
        )}
      </div>

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col justify-between p-6">
        {/* Messages Window */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-2">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-500">
              <p className="text-lg">No video loaded yet.</p>
              <p className="text-sm">Paste a YouTube link in the sidebar to start.</p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex flex-col ${
                  msg.sender === 'user' ? 'items-end' : 'items-start'
                }`}
              >
                <div
                  className={`max-w-2xl px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                    msg.sender === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-none'
                      : msg.sender === 'system'
                      ? 'bg-slate-800 text-slate-300 italic'
                      : 'bg-slate-800 text-slate-100 border border-slate-700 rounded-bl-none'
                  }`}
                >
                  <ReactMarkdown
                    components={{
                      a: ({ node, ...props }) => (
                        <a
                          {...props}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-400 underline font-semibold hover:text-indigo-300"
                        />
                      ),
                    }}
                  >
                    {msg.text}
                  </ReactMarkdown>
                </div>
              </div>
            ))
          )}
          {isQuerying && (
            <div className="text-xs text-slate-400 italic">
              QueryClip is searching transcript & generating answer...
            </div>
          )}
        </div>

        {/* Question Input Bar */}
        <form onSubmit={handleQuery} className="mt-4 flex gap-3">
          <input
            type="text"
            placeholder={
              videoId
                ? 'Ask a question about the video...'
                : 'Please analyze a video first...'
            }
            disabled={!videoId || isQuerying}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!videoId || isQuerying || !query}
            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 font-medium text-sm rounded-xl transition"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}