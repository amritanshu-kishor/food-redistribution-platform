import React from 'react';
import { navigateTo } from '../services/router';
import { useAuth } from '../context/AuthContext';
import { ArrowRight, Utensils, Heart, ShieldCheck, Sparkles, Leaf } from 'lucide-react';

const partners = [
  'Spice Garden', 'Golden Ladle', 'Hunger Relief', 'Annadan Seva',
  'Green Plate', 'Feed The City', 'Coastal Table', 'Plate for Hope',
];

export const Landing: React.FC = () => {
  const { user } = useAuth();

  const handleStart = () => {
    navigateTo(user ? `/${user.role}` : '/login');
  };

  return (
    <div className="min-h-screen flex flex-col font-sans text-brand-charcoal">
      <header className="px-6 py-5 flex justify-between items-center max-w-6xl mx-auto w-full">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigateTo('/')}>
          <div className="w-10 h-10 rounded-2xl bg-brand-pine text-brand-ivory font-display font-bold text-lg flex items-center justify-center shadow-md">
            H
          </div>
          <div className="leading-tight">
            <span className="font-display font-bold text-lg">Harvest Link</span>
            <p className="text-[10px] uppercase tracking-[0.2em] text-brand-amber font-semibold">surplus, shared</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {user ? (
            <button onClick={() => navigateTo(`/${user.role}`)} className="btn-tactile text-xs px-5 py-2.5 flex items-center gap-2">
              Open dashboard <ArrowRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <>
              <button onClick={() => navigateTo('/login')} className="text-sm font-semibold hover:text-brand-amber cursor-pointer">
                Log in
              </button>
              <button onClick={() => navigateTo('/register')} className="btn-tactile-green text-xs px-5 py-2.5">
                Join the table
              </button>
            </>
          )}
        </div>
      </header>

      <main className="flex-grow max-w-6xl mx-auto w-full px-6 pb-16">
        <section className="relative overflow-hidden rounded-[2.5rem] bg-brand-pine text-brand-ivory px-8 md:px-14 py-16 md:py-20 mt-2 shadow-[0_40px_80px_-40px_rgba(15,46,36,0.7)]">
          <div className="absolute -right-10 -top-16 w-72 h-72 rounded-full bg-brand-amber/30 blur-3xl" />
          <div className="absolute left-1/3 bottom-0 w-80 h-80 rounded-full bg-brand-gold/20 blur-3xl" />
          <div className="relative grid md:grid-cols-2 gap-12 items-center">
            <div className="flex flex-col gap-6">
              <span className="w-max text-[11px] uppercase tracking-[0.22em] font-semibold bg-white/10 border border-white/15 px-3 py-1 rounded-full">
                kitchens · NGOs · one table
              </span>
              <h1 className="font-display text-4xl md:text-6xl font-bold leading-[1.05]">
                Beautiful food deserves a second life.
              </h1>
              <p className="text-sm md:text-base text-brand-ivory/75 leading-relaxed max-w-md">
                Harvest Link moves surplus from verified restaurants to NGOs who can use it today — with QR handovers, partial claims, and an admin who keeps every partner honest.
              </p>
              <div className="flex flex-wrap gap-3">
                <button onClick={handleStart} className="btn-tactile-green px-6 py-3 text-sm flex items-center gap-2">
                  Start sharing <ArrowRight className="w-4 h-4" />
                </button>
                <button onClick={() => navigateTo('/register')} className="px-6 py-3 text-sm rounded-full border border-white/25 hover:bg-white/10 cursor-pointer">
                  Register as NGO
                </button>
              </div>
            </div>

            <div className="relative min-h-[280px]">
              <div className="animate-float card-tactile bg-white text-brand-charcoal max-w-sm ml-auto">
                <div className="flex justify-between items-start">
                  <div className="p-2.5 rounded-2xl bg-brand-green/10 text-brand-green">
                    <Utensils className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] bg-brand-green-light text-brand-green font-bold px-2 py-0.5 rounded-full uppercase">Live</span>
                </div>
                <h3 className="font-display font-bold text-xl mt-4">Wedding catering surplus</h3>
                <p className="text-sm text-brand-charcoal/65 mt-1">80 portions of dal, rice & paneer — Golden Ladle, Pune</p>
                <div className="flex justify-between items-center text-xs mt-5 pt-4 border-t border-brand-stone">
                  <span className="font-semibold">Expires in 5 hours</span>
                  <span className="text-brand-amber font-bold">Claim now</span>
                </div>
              </div>
              <div className="absolute -bottom-4 left-0 card-tactile py-4 px-5 flex items-center gap-3 max-w-[220px] rotate-[-4deg]">
                <div className="w-10 h-10 rounded-full bg-brand-gold/20 text-brand-green flex items-center justify-center font-display font-bold">98</div>
                <div>
                  <p className="text-xs font-bold">Acceptance score</p>
                  <p className="text-[11px] text-brand-charcoal/60">Hunger Relief Society</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="mt-10 overflow-hidden rounded-full border border-brand-stone-dark/50 bg-white/50 py-3">
          <div className="flex gap-10 whitespace-nowrap text-xs uppercase tracking-[0.18em] font-semibold text-brand-charcoal/50 px-6">
            {partners.concat(partners).map((p, i) => (
              <span key={`${p}-${i}`} className="flex items-center gap-2">
                <Leaf className="w-3 h-3 text-brand-amber" /> {p}
              </span>
            ))}
          </div>
        </div>

        <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-10">
          {[
            ['1.2k+', 'Portions completed in demo'],
            ['5', 'Verified kitchens'],
            ['5', 'Active NGO partners'],
            ['2', 'Awaiting admin review'],
          ].map(([n, l]) => (
            <div key={l} className="card-tactile text-center py-8">
              <p className="font-display text-3xl font-bold text-brand-green">{n}</p>
              <p className="text-[11px] uppercase tracking-wider text-brand-charcoal/55 mt-1">{l}</p>
            </div>
          ))}
        </section>

        <section className="mt-16 grid md:grid-cols-2 gap-6">
          <div className="rounded-[2rem] bg-white/70 border border-white p-8">
            <Sparkles className="w-6 h-6 text-brand-amber" />
            <h2 className="font-display text-2xl mt-4">Partners with great donations</h2>
            <p className="text-sm text-brand-charcoal/65 mt-2">Spice Garden Kitchen and The Golden Ladle lead completed volume in the seed data — log in to see their history.</p>
            <ul className="mt-5 space-y-2 text-sm">
              <li className="flex justify-between border-b border-brand-stone pb-2"><span>Spice Garden Kitchen</span><span className="font-semibold">320+ portions</span></li>
              <li className="flex justify-between border-b border-brand-stone pb-2"><span>The Golden Ladle</span><span className="font-semibold">340+ portions</span></li>
              <li className="flex justify-between"><span>Bakers Corner</span><span className="font-semibold">134 pieces</span></li>
            </ul>
          </div>
          <div className="rounded-[2rem] bg-brand-green text-brand-ivory p-8">
            <Heart className="w-6 h-6 text-brand-gold" />
            <h2 className="font-display text-2xl mt-4">NGOs with great acceptance</h2>
            <p className="text-sm text-brand-ivory/70 mt-2">Hunger Relief and Annadan Seva complete handovers quickly and keep claims flowing.</p>
            <ul className="mt-5 space-y-2 text-sm">
              <li className="flex justify-between border-b border-white/15 pb-2"><span>Hunger Relief Society</span><span className="font-semibold">High volume</span></li>
              <li className="flex justify-between border-b border-white/15 pb-2"><span>Annadan Seva Trust</span><span className="font-semibold">Reliable bakery pickups</span></li>
              <li className="flex justify-between"><span>Plate for Hope</span><span className="font-semibold">Event surplus specialist</span></li>
            </ul>
          </div>
        </section>

        <section className="mt-16 grid md:grid-cols-3 gap-6">
          {[
            { icon: <Utensils className="w-5 h-5" />, t: 'Post surplus in minutes', d: 'Kitchens list quantity, expiry, and a map pin. NGOs see it live.' },
            { icon: <Heart className="w-5 h-5" />, t: 'Claim only what you can move', d: 'Partial claims mean one tray can feed more than one organisation.' },
            { icon: <ShieldCheck className="w-5 h-5" />, t: 'Admin verifies every partner', d: 'New restaurants and NGOs stay pending until an admin approves them.' },
          ].map((f) => (
            <div key={f.t} className="card-tactile">
              <div className="w-11 h-11 rounded-2xl bg-brand-green/10 text-brand-green flex items-center justify-center">{f.icon}</div>
              <h3 className="font-display text-lg mt-4">{f.t}</h3>
              <p className="text-sm text-brand-charcoal/65 mt-2 leading-relaxed">{f.d}</p>
            </div>
          ))}
        </section>
      </main>

      <footer className="border-t border-brand-stone-dark/40 py-8">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row justify-between gap-3 text-xs text-brand-charcoal/50">
          <span>© {new Date().getFullYear()} Harvest Link. Food with a second chance.</span>
          <span>Admin verifies partners · QR confirms handovers</span>
        </div>
      </footer>
    </div>
  );
};
