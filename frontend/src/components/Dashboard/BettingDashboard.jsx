// src/components/Dashboard/BettingDashboard.jsx
import React, { useState } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, AlertCircle, ExternalLink } from 'lucide-react';


const BettingDashboard = ({ data,onBack }) => {
  const [volumePeriod, setVolumePeriod] = useState('24h');
  const [selectedBet, setSelectedBet] = useState(data.betOptions?.[0] || 'yes');
  const [strategy, setStrategy] = useState('safe');
  
  // All dataset access uses the `data` prop
  const volumeData = data.volumeData || {};
  const oddsComparison = data.oddsComparison || {};
  const shiftTimeline = data.shiftTimeline || [];
  const news = data.news || [];
  const largeBets = data.largeBets || [];
  const sentimentTimeline = data.sentimentTimeline || [];
  const healthScore = data.healthScore ?? 0;
  const liquidityScore = data.liquidityScore ?? 0;
  const gapAnalysis = Math.abs((oddsComparison[selectedBet]?.polymarket ?? 0) - (oddsComparison[selectedBet]?.news ?? 0));
  const recommendations = data.recommendations || {};
  const aiSummary = data.aiSummary || [];
  const betOptions = ['yes', 'no', 'maybe'];
  
  const HealthGauge = ({ score }) => {
      const rotation = (score / 100) * 180 - 90;
      let color = '#ef4444';
      if (score >= 70) color = '#22c55e';
      else if (score >= 40) color = '#f97316';
  
      return (
        <div className="relative w-48 h-24 mx-auto">
          <svg viewBox="0 0 200 100" className="w-full h-full">
            <path d="M 20 80 A 80 80 0 0 1 180 80" fill="none" stroke="#fee2e2" strokeWidth="20" />
            <path d="M 20 80 A 80 80 0 0 1 100 20" fill="none" stroke="#fed7aa" strokeWidth="20" />
            <path d="M 100 20 A 80 80 0 0 1 180 80" fill="none" stroke="#dcfce7" strokeWidth="20" />
            <line x1="100" y1="80" x2="100" y2="30" stroke={color} strokeWidth="3" 
                  transform={`rotate(${rotation} 100 80)`} strokeLinecap="round" />
            <circle cx="100" cy="80" r="5" fill={color} />
          </svg>
          <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 text-3xl font-bold">{score}</div>
        </div>
      );
    };
  
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6">
        <div className="max-w-7xl mx-auto">

            {/* Back Button */}
        <button
          onClick={onBack}
          className="mb-4 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-all"
        >
          ← Back to Chat
        </button>
        

          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">Betting Analysis Dashboard</h1>
            <p className="text-slate-400">Will the S&P 500 reach 6000 by end of 2025?</p>
          </div>
  
          {/* Health Score & Liquidity */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4">Health Score</h2>
              <HealthGauge score={healthScore} />
              <p className="text-center mt-4 text-slate-300">Market health is <span className="text-green-400 font-semibold">Good</span></p>
            </div>
  
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4">Liquidity Score</h2>
              <div className="flex items-center justify-center h-32">
                <div className="text-center">
                  <div className="text-5xl font-bold text-green-400">{liquidityScore}</div>
                  <div className="text-xl mt-2">/ 10</div>
                  <div className="mt-4 px-4 py-2 bg-green-900/30 border border-green-700 rounded-full inline-block">
                    <span className="text-green-400 font-semibold">HIGH LIQUIDITY</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
  
          {/* Recent News & Trading Volume */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4">Recent News</h2>
              <div className="space-y-3">
                {news.map((item, idx) => (
                  <div key={idx} className="flex items-start justify-between p-4 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition-colors">
                    <div className="flex-1">
                      <h3 className="font-medium mb-1">{item.title}</h3>
                      <p className="text-sm text-slate-400">{item.source} • {item.date}</p>
                    </div>
                    <ExternalLink className="w-5 h-5 text-slate-400 hover:text-blue-400 cursor-pointer" />
                  </div>
                ))}
              </div>
            </div>
  
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">Trading Volume</h2>
                <div className="flex gap-2">
                  {['24h', '7d', '1m'].map(period => (
                    <button
                      key={period}
                      onClick={() => setVolumePeriod(period)}
                      className={`px-4 py-2 rounded-lg transition-all ${
                        volumePeriod === period
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                    >
                      {period === '24h' ? '24 Hours' : period === '7d' ? '7 Days' : '1 Month'}
                    </button>
                  ))}
                </div>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={volumeData[volumePeriod]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                  <XAxis dataKey="time" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip cursor={false} contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
                  <Bar dataKey="volume" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
  
          {/* Odds Comparison & Market Shift Timeline */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4">Odds Comparison</h2>
  
              <div className="flex gap-2 mb-6">
                {betOptions.map(option => (
                  <button
                    key={option}
                    onClick={() => setSelectedBet(option)}
                    className={`px-6 py-3 rounded-lg font-medium capitalize transition-all ${
                      selectedBet === option
                        ? 'bg-blue-600 text-white shadow-lg'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    {option}
                  </button>
                ))}
              </div>
  
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={[
                  { source: 'Polymarket', value: oddsComparison[selectedBet].polymarket },
                  { source: 'News Analysis', value: oddsComparison[selectedBet].news },
                  { source: 'Expert Average', value: oddsComparison[selectedBet].expert }
                ]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                  <XAxis dataKey="source" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip cursor={false} contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
                  <Bar dataKey="value" fill="#8b5cf6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
  
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4">Market Shift Timeline</h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={shiftTimeline}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                  <XAxis dataKey="date" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip cursor={false} contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
                  <Legend />
                  <Line type="monotone" dataKey="polymarket" stroke="#3b82f6" strokeWidth={2} />
                  <Line type="monotone" dataKey="news" stroke="#8b5cf6" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
  
          {/* Recent Large Bets & News Sentiment Timeline */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4">Recent Large Bets</h2>
              <div className="space-y-3">
                {largeBets.map((bet, idx) => (
                  <div key={idx} className="flex items-center justify-between p-4 bg-slate-700/50 rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                        bet.option === 'Yes' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
                      }`}>
                        {bet.option === 'Yes' ? <TrendingUp /> : <TrendingDown />}
                      </div>
                      <div>
                        <div className="font-bold text-lg">{bet.amount}</div>
                        <div className="text-sm text-slate-400">{bet.option} • {bet.time}</div>
                      </div>
                    </div>
                    <div className={`text-lg font-semibold ${
                      bet.impact.startsWith('+') ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {bet.impact}
                    </div>
                  </div>
                ))}
              </div>
            </div>
  
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4">News Sentiment Timeline</h2>
              <div className="space-y-4">
                {sentimentTimeline.map((item, idx) => (
                  <div key={idx} className="flex items-center gap-4">
                    <div className="text-slate-400 w-16">{item.date}</div>
                    <div className="flex-1 bg-slate-700/50 rounded-lg p-4">
                      <div className="flex items-center gap-4">
                        <div className="flex-1">
                          <div className="text-sm text-slate-400 mb-1">{item.events}</div>
                          <div className="w-full bg-slate-600 rounded-full h-2">
                            <div 
                              className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full"
                              style={{ width: `${item.sentiment}%` }}
                            />
                          </div>
                        </div>
                        <div className="text-xl font-bold">{item.sentiment}%</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
  
          {/* Gap Analysis & Market Manipulation */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4">Gap Analysis</h2>
              <div className="flex items-center justify-center h-32">
                <div className="text-center">
                  <div className="text-5xl font-bold text-yellow-400">{gapAnalysis}%</div>
                  <p className="text-slate-300 mt-4">Difference between Polymarket and News sources</p>
                </div>
              </div>
            </div>
  
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-yellow-400" />
                Market Manipulation Analysis
              </h2>
              <p className="text-slate-300 leading-relaxed">
                Moderate divergence detected between prediction markets and news sentiment. Recent large bets may indicate coordinated activity. Volume spikes align with major news events, suggesting organic market movement with some whale influence.
              </p>
            </div>
          </div>
  
          {/* Recommendations */}
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 mb-6">
            <h2 className="text-xl font-semibold mb-4">Betting Recommendations</h2>
            <div className="flex gap-4 mb-6">
              <button
                onClick={() => setStrategy('safe')}
                className={`flex-1 py-3 rounded-lg font-medium transition-all ${
                  strategy === 'safe'
                    ? 'bg-green-600 text-white shadow-lg'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                Safe Strategy
              </button>
              <button
                onClick={() => setStrategy('aggressive')}
                className={`flex-1 py-3 rounded-lg font-medium transition-all ${
                  strategy === 'aggressive'
                    ? 'bg-red-600 text-white shadow-lg'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                Aggressive Strategy
              </button>
            </div>
  
            <div className="p-6 bg-slate-700/50 rounded-lg">
              {strategy === 'safe' ? (
                <div>
                  <h3 className="text-2xl font-bold text-green-400 mb-2">Recommended: YES</h3>
                  <p className="text-slate-300">
                    Based on expert consensus (62%) and strong liquidity, betting YES offers the best risk-reward ratio. 
                    Market health is good and sentiment is positive with minimal manipulation risk.
                  </p>
                </div>
              ) : (
                <div>
                  <h3 className="text-2xl font-bold text-red-400 mb-2">Recommended: YES (High Stakes)</h3>
                  <p className="text-slate-300">
                    Polymarket shows 65% probability with upward momentum. Recent whale activity supports this position. 
                    Gap analysis suggests potential for further price movement. Higher risk but maximum reward potential.
                  </p>
                </div>
              )}
            </div>
          </div>
  
          {/* AI Analysis Summary */}
          <div className="bg-gradient-to-r from-blue-900/30 to-purple-900/30 rounded-lg p-6 border border-blue-700/50">
            <h2 className="text-xl font-semibold mb-4">AI Analysis Summary</h2>
            <div className="space-y-4 text-slate-200 leading-relaxed">
              <p>
                <strong className="text-blue-400">Market Confidence:</strong> High. The betting market shows strong conviction with 78/100 health score and excellent liquidity (8.5/10). This indicates robust participation and reliable price discovery.
              </p>
              <p>
                <strong className="text-blue-400">Trend Analysis:</strong> Bullish momentum detected. Polymarket odds have increased from 45% to 65% over the past week, supported by positive news sentiment and expert consensus around 62%.
              </p>
              <p>
                <strong className="text-blue-400">Risk Assessment:</strong> Moderate. The 7% gap between Polymarket and news sources suggests some speculative positioning, but recent large bets show institutional confidence. Volume patterns indicate organic growth rather than manipulation.
              </p>
              <p>
                <strong className="text-blue-400">Strategic Recommendation:</strong> The data supports a YES position for both conservative and aggressive strategies. Safe players should enter at current odds, while aggressive traders may benefit from the upward momentum and whale activity.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
};
export default BettingDashboard;
