import { useState, useEffect, useMemo } from 'react'

const STATUS_OPTIONS = [
  "📥 Backlog", "🔥 Playing", "⏸️ On Hold", 
  "✅ Story Complete", "🏆 Platinumed", 
  "♾️ Ongoing", "🛑 Dropped", "🚫 Not Interested"
];

function App() {
  const [activeTab, setActiveTab] = useState('library'); // 'library' or 'agent'
  const [stats, setStats] = useState(null)
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Filter States
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTier, setSelectedTier] = useState('All')

  // AI Agent States
  const [agentInput, setAgentInput] = useState('')
  const [agentResponse, setAgentResponse] = useState(null)
  const [agentLoading, setAgentLoading] = useState(false)
  const [lastQuery, setLastQuery] = useState('')

  useEffect(() => {
    Promise.all([
      fetch('http://127.0.0.1:8000/api/stats').then(res => res.json()),
      fetch('http://127.0.0.1:8000/api/games?status=active').then(res => res.json())
    ])
      .then(([statsData, gamesData]) => {
        setStats(statsData)
        setGames(gamesData)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  // Handle Dropdown Saves
  const handleStatusChange = async (gameName, newStatus) => {
    setGames(prevGames => 
      prevGames.map(g => g.game === gameName ? { ...g, personal_status: newStatus } : g)
    );
    try {
      await fetch(`http://127.0.0.1:8000/api/games/${encodeURIComponent(gameName)}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
    } catch (err) {
      console.error("Save error:", err);
    }
  };

  // Handle AI Agent Query
  const askAgent = async () => {
    if (!agentInput.trim()) return;
    setAgentLoading(true);
    setLastQuery(agentInput);
    setAgentResponse(null);
    
    try {
      const res = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: agentInput })
      });
      const data = await res.json();
      setAgentResponse(data.response);
    } catch (err) {
      setAgentResponse("❌ Error communicating with the AI Agent. Is the backend running?");
    } finally {
      setAgentLoading(false);
      setAgentInput('');
    }
  };

  // --- FILTERING LOGIC ---
  // Extract unique tiers for the dropdown
  const availableTiers = useMemo(() => {
    const tiers = new Set(games.map(g => g.tier).filter(Boolean));
    return ['All', ...Array.from(tiers).sort()];
  }, [games]);

  // Apply Search and Tier Filters
  const filteredGames = useMemo(() => {
    return games.filter(game => {
      const matchesSearch = game.game.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesTier = selectedTier === 'All' || game.tier === selectedTier;
      return matchesSearch && matchesTier;
    });
  }, [games, searchQuery, selectedTier]);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-4 md:p-8 font-sans">
      <div className="max-w-7xl mx-auto">
        
        <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-b border-gray-800 pb-6">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight mb-2">🎮 Smart PS+ Backlog</h1>
            <p className="text-gray-400">Manage your library and track your playtime.</p>
          </div>
          
          {/* Tab Navigation */}
          <div className="flex bg-gray-900 rounded-lg p-1 border border-gray-800">
            <button 
              onClick={() => setActiveTab('library')}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${activeTab === 'library' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}`}
            >
              📋 My Library
            </button>
            <button 
              onClick={() => setActiveTab('agent')}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${activeTab === 'agent' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}`}
            >
              💬 AI Agent
            </button>
          </div>
        </header>

        {error && (
          <div className="bg-red-500/10 border border-red-500 text-red-400 p-4 rounded-lg mb-8">
            ⚠️ Failed to connect to API: {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-pulse flex flex-col items-center">
              <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
            </div>
          </div>
        ) : activeTab === 'library' ? (
          /* --- LIBRARY TAB --- */
          <>
            {/* Stats Dashboard */}
            {stats && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <div className="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-lg">
                  <div className="text-gray-400 text-sm font-medium mb-1">Total Hours</div>
                  <div className="text-3xl font-bold text-blue-400">{stats.total_hours_played}</div>
                </div>
                <div className="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-lg">
                  <div className="text-gray-400 text-sm font-medium mb-1">Avg Playtime</div>
                  <div className="text-3xl font-bold text-green-400">{stats.average_playtime}h</div>
                </div>
                <div className="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-lg">
                  <div className="text-gray-400 text-sm font-medium mb-1">Available Games</div>
                  <div className="text-3xl font-bold text-purple-400">{stats.total_games_available}</div>
                </div>
                <div className="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-lg">
                  <div className="text-gray-400 text-sm font-medium mb-1">Leaving Soon</div>
                  <div className="text-3xl font-bold text-orange-400">{stats.games_leaving_soon}</div>
                </div>
              </div>
            )}

            {/* Filters Bar */}
            <div className="flex flex-col md:flex-row gap-4 mb-6 items-center">
              <input 
                type="text" 
                placeholder="Search games..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-grow bg-gray-900 border border-gray-700 text-white rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none w-full md:w-auto"
              />
              <select 
                value={selectedTier}
                onChange={(e) => setSelectedTier(e.target.value)}
                className="bg-gray-900 border border-gray-700 text-white rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none w-full md:w-48 appearance-none cursor-pointer"
              >
                {availableTiers.map(tier => (
                  <option key={tier} value={tier}>{tier === 'All' ? 'All PS+ Tiers' : tier}</option>
                ))}
              </select>
            </div>

            <div className="mb-6">
              <span className="text-sm text-gray-500">Showing {filteredGames.length} games</span>
            </div>

            {/* Game Grid */}
            {filteredGames.length === 0 ? (
              <div className="text-center py-20 text-gray-500">No games found matching your filters.</div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
                {filteredGames.map((game, index) => (
                  <div key={index} className="bg-gray-900 flex flex-col rounded-xl overflow-hidden border border-gray-800 hover:border-gray-600 transition-all duration-300 hover:-translate-y-1 shadow-lg group">
                    <div className="relative aspect-[3/4] overflow-hidden bg-gray-800 flex-shrink-0">
                      <img src={game.cover_image_url} alt={game.game} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy" />
                      <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-md px-2 py-1 rounded text-xs font-semibold">
                        {game.tier || "Unknown"}
                      </div>
                    </div>
                    <div className="p-4 flex flex-col flex-grow">
                      <h3 className="font-bold text-sm line-clamp-2 leading-tight mb-3" title={game.game}>{game.game}</h3>
                      <div className="flex justify-between items-end text-xs text-gray-400 mt-auto mb-3">
                        <span>⭐ {game.metacritic || "N/A"}</span>
                        <div className="flex flex-col items-end gap-1">
                          {game.my_hours > 0 && <span className="text-blue-400 font-medium bg-blue-900/30 px-1.5 py-0.5 rounded">🔥 {game.my_hours}h</span>}
                          {game.completion && game.completion !== "Unknown" && <span className="text-gray-500">⏱️ {game.completion}h</span>}
                        </div>
                      </div>
                      <div className="mt-auto pt-3 border-t border-gray-800">
                        <select
                          value={game.personal_status || "📥 Backlog"}
                          onChange={(e) => handleStatusChange(game.game, e.target.value)}
                          className="w-full bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded p-2 focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer appearance-none text-center"
                        >
                          {STATUS_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                        </select>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          /* --- AI AGENT TAB --- */
          <div className="max-w-3xl mx-auto mt-8">
            <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6 shadow-xl">
              <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">🤖 Your Backlog Agent</h2>
              <p className="text-gray-400 mb-6">Ask for recommendations, stats, or filter your library using natural language.</p>
              
              <div className="flex gap-4 mb-8">
                <input 
                  type="text" 
                  value={agentInput}
                  onChange={(e) => setAgentInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && askAgent()}
                  placeholder="e.g., What are 3 short RPGs I can play this weekend?" 
                  className="flex-grow bg-gray-950 border border-gray-700 text-white rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none"
                  disabled={agentLoading}
                />
                <button 
                  onClick={askAgent}
                  disabled={agentLoading || !agentInput.trim()}
                  className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-bold py-3 px-8 rounded-lg transition-colors"
                >
                  {agentLoading ? "Thinking..." : "Ask"}
                </button>
              </div>

              {agentLoading && (
                <div className="p-4 bg-gray-950 rounded-lg border border-gray-800 animate-pulse text-blue-400">
                  Agent is analyzing your database...
                </div>
              )}

              {agentResponse && (
                <div className="flex flex-col gap-4">
                  <div className="self-end bg-blue-900/40 border border-blue-800/50 rounded-2xl rounded-tr-sm px-6 py-4 max-w-[80%]">
                    <p className="text-blue-200">{lastQuery}</p>
                  </div>
                  <div className="self-start bg-gray-800 border border-gray-700 rounded-2xl rounded-tl-sm px-6 py-4 max-w-[90%]">
                    <p className="text-gray-200 whitespace-pre-wrap">{agentResponse}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App