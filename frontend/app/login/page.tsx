'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { BrainCircuit, Lock, Mail, ArrowRight } from 'lucide-react'
import clsx from 'clsx'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    // Simulate network request
    setTimeout(() => {
      if (email === 'admin@marketintel.ai' && password === 'admin') {
        router.push('/')
      } else {
        setError('Invalid credentials. (Hint: admin@marketintel.ai / admin)')
        setLoading(false)
      }
    }, 800)
  }

  return (
    <div className="flex flex-col h-screen bg-terminal-bg items-center justify-center text-text-primary px-4">
      {/* ── Background decoration ── */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-accent-primary/5 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-accent-primary/5 blur-[120px]" />
      </div>

      <div className="w-full max-w-sm z-10 animate-slide-up">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 flex items-center justify-center border border-terminal-border bg-terminal-surface rounded-lg mb-4 shadow-card">
            <BrainCircuit size={24} className="text-accent-primary" />
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-text-primary">Market Intelligence AI</h1>
          <p className="text-text-muted text-xs tracking-widest mt-1 uppercase">Secure Access Terminal</p>
        </div>

        <div className="card p-6">
          <form onSubmit={handleLogin} className="space-y-4">
            
            {error && (
              <div className="bg-fin-neg/10 border border-fin-neg/20 text-fin-neg text-[11px] font-mono px-3 py-2 rounded">
                {error}
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-[11px] text-text-secondary uppercase tracking-wider font-semibold block">Email Address</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-text-muted">
                  <Mail size={14} />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="admin@marketintel.ai"
                  className="w-full bg-terminal-surface border border-terminal-border text-text-primary text-[13px] rounded-[6px] pl-9 pr-3 py-2 focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary transition-all placeholder:text-text-muted/50"
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-[11px] text-text-secondary uppercase tracking-wider font-semibold block">Master Password</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-text-muted">
                  <Lock size={14} />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-terminal-surface border border-terminal-border text-text-primary text-[13px] rounded-[6px] pl-9 pr-3 py-2 focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary transition-all placeholder:text-text-muted/50"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary py-2.5 mt-2 flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="font-mono text-xs tracking-wider animate-pulse">AUTHENTICATING...</span>
              ) : (
                <>
                  <span className="tracking-wide">Access Terminal</span>
                  <ArrowRight size={14} />
                </>
              )}
            </button>

            {/* Quick Login for Testing */}
            <div className="pt-3 border-t border-terminal-border mt-4">
              <button
                type="button"
                onClick={() => {
                  setEmail('admin@marketintel.ai')
                  setPassword('admin')
                  setError('')
                  setLoading(true)
                  setTimeout(() => {
                    router.push('/')
                  }, 800)
                }}
                disabled={loading}
                className="w-full btn-ghost py-2 text-xs font-mono tracking-wide flex items-center justify-center gap-2"
              >
                <Lock size={12} className="text-accent-primary" />
                AUTO LOGIN AS ADMIN
              </button>
            </div>
          </form>
        </div>

        <div className="text-center mt-6 text-[10px] font-mono text-text-muted">
          RESTRICTED INSTITUTIONAL SYSTEM
          <br/>
          UNAUTHORIZED ACCESS STRICTLY PROHIBITED
        </div>
      </div>
    </div>
  )
}
