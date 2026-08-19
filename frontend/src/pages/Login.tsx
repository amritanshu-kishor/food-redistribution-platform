import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { navigateTo } from '../services/router';
import { AlertCircle, Eye, EyeOff } from 'lucide-react';

const demos = [
  { label: 'Admin', email: 'admin@foodshare.io', password: 'Admin@1234' },
  { label: 'Top kitchen', email: 'contact@spicegarden.com', password: 'Demo@1234' },
  { label: 'Top NGO', email: 'info@hungerrelief.org', password: 'Demo@1234' },
  { label: 'Pending kitchen', email: 'pending.kitchen@foodshare.io', password: 'Demo@1234' },
];

export const Login: React.FC = () => {
  const { login, user } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) navigateTo(`/${user.role}`);
    const params = new URLSearchParams(window.location.search);
    if (params.get('expired') === 'true') setSessionExpired(true);
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSessionExpired(false);
    setLoading(true);
    try {
      const loggedUser = await login(email, password);
      navigateTo(`/${loggedUser.role}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to authenticate. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-4xl grid md:grid-cols-[1.05fr_0.95fr] gap-8 items-center">
        <div className="hidden md:flex flex-col gap-6 rounded-[2.2rem] bg-brand-pine text-brand-ivory p-10 min-h-[520px] justify-between">
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-brand-gold">Harvest Link</p>
            <h1 className="font-display text-4xl font-bold mt-4 leading-tight">Come back to the table.</h1>
            <p className="text-sm text-brand-ivory/70 mt-3 leading-relaxed">
              Kitchens post surplus. NGOs claim it. Admins keep the network trusted.
            </p>
          </div>
          <div className="space-y-3">
            {demos.map((d) => (
              <button
                key={d.email}
                type="button"
                onClick={() => { setEmail(d.email); setPassword(d.password); }}
                className="w-full text-left rounded-2xl bg-white/8 hover:bg-white/14 border border-white/10 px-4 py-3 cursor-pointer"
              >
                <p className="text-[10px] uppercase tracking-widest text-brand-gold">{d.label}</p>
                <p className="text-sm font-medium mt-0.5">{d.email}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-6">
          <div className="cursor-pointer" onClick={() => navigateTo('/')}>
            <h2 className="font-display font-bold text-3xl">Welcome back</h2>
            <p className="text-sm text-brand-charcoal/60 mt-1">Log in to manage donations and claims</p>
          </div>

          <div className="card-tactile">
            {sessionExpired && (
              <div className="mb-4 bg-brand-amber/10 border border-brand-amber/30 text-brand-amber text-xs rounded-2xl p-3 font-semibold flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>Your session has expired. Please log in again.</span>
              </div>
            )}
            {error && (
              <div className="mb-4 bg-brand-red/10 border border-brand-red/30 text-brand-red text-xs rounded-2xl p-3 font-semibold flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1 text-left">
                <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Email</label>
                <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@organization.org" className="input-tactile text-sm" />
              </div>
              <div className="flex flex-col gap-1 text-left">
                <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input-tactile text-sm pr-10"
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-brand-charcoal/40 cursor-pointer">
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <button type="submit" disabled={loading} className="btn-tactile-green w-full py-3 text-sm font-semibold mt-1 disabled:opacity-50">
                {loading ? 'Signing in…' : 'Enter Harvest Link'}
              </button>
            </form>
          </div>

          <p className="text-sm text-center text-brand-charcoal/60">
            New partner?{' '}
            <button onClick={() => navigateTo('/register')} className="text-brand-amber font-bold cursor-pointer">Create an account</button>
          </p>
        </div>
      </div>
    </div>
  );
};
