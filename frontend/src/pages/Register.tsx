import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { navigateTo } from '../services/router';
import { AlertCircle, CheckCircle, Navigation, MapPin } from 'lucide-react';

export const Register: React.FC = () => {
  const { register } = useAuth();
  
  // Tab selector: 'restaurant' or 'ngo'
  const [role, setRole] = useState<'restaurant' | 'ngo'>('restaurant');
  
  // User Credentials
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  // Organization details
  const [orgName, setOrgName] = useState('');
  const [orgAddress, setOrgAddress] = useState('');
  const [orgDesc, setOrgDesc] = useState('');
  const [orgWeb, setOrgWeb] = useState('');
  const [lat, setLat] = useState<number | ''>('');
  const [lon, setLon] = useState<number | ''>('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [locLoading, setLocLoading] = useState(false);

  const fetchLocation = () => {
    setLocLoading(true);
    setError(null);
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");
      setLocLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLat(position.coords.latitude);
        setLon(position.coords.longitude);
        setLocLoading(false);
      },
      (_err) => {
        setError("Unable to retrieve location. Please input coordinates manually.");
        setLocLoading(false);
      }
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    const regData = {
      email,
      password,
      full_name: fullName,
      phone: phone || undefined,
      role,
      organization: {
        name: orgName,
        address: orgAddress,
        description: orgDesc || undefined,
        website: orgWeb || undefined,
        latitude: lat !== '' ? lat : undefined,
        longitude: lon !== '' ? lon : undefined
      }
    };

    try {
      await register(regData);
      setSuccess("Registered. You stay pending until an admin approves you. Redirecting to login…");
      setTimeout(() => {
        navigateTo('/login');
      }, 3000);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Registration failed. Please check inputs.";
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center px-6 py-12 font-sans">
      <div className="w-full max-w-xl flex flex-col gap-6">
        
        <div className="flex flex-col items-center gap-2 cursor-pointer" onClick={() => navigateTo('/')}>
          <div className="w-11 h-11 rounded-2xl bg-brand-pine flex items-center justify-center text-brand-ivory font-display font-bold text-xl">
            H
          </div>
          <h2 className="font-display font-bold text-2xl tracking-tight text-brand-charcoal">
            Join Harvest Link
          </h2>
          <p className="text-xs text-brand-charcoal/55">
            New kitchens and NGOs stay pending until an admin verifies them
          </p>
        </div>

        <div className="card-tactile">
          
          {/* Role selector Tabs */}
          <div className="flex border-b border-brand-stone-dark mb-6">
            <button
              type="button"
              onClick={() => setRole('restaurant')}
              className={`flex-1 py-3 text-xs uppercase tracking-wider font-bold border-b-2 text-center transition-all duration-150 cursor-pointer ${
                role === 'restaurant'
                  ? 'border-brand-green text-brand-green'
                  : 'border-transparent text-brand-stone-dark hover:text-brand-charcoal'
              }`}
            >
              Restaurant / Food Donor
            </button>
            <button
              type="button"
              onClick={() => setRole('ngo')}
              className={`flex-1 py-3 text-xs uppercase tracking-wider font-bold border-b-2 text-center transition-all duration-150 cursor-pointer ${
                role === 'ngo'
                  ? 'border-brand-green text-brand-green'
                  : 'border-transparent text-brand-stone-dark hover:text-brand-charcoal'
              }`}
            >
              NGO / Food Recipient
            </button>
          </div>

          {success && (
            <div className="mb-6 bg-brand-green/10 border border-brand-green/30 text-brand-green text-xs rounded p-4 font-semibold flex items-center gap-2">
              <CheckCircle className="w-5 h-5 flex-shrink-0" />
              <span>{success}</span>
            </div>
          )}

          {error && (
            <div className="mb-6 bg-brand-red/10 border border-brand-red/30 text-brand-red text-xs rounded p-4 font-semibold flex items-center gap-2">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-6">
            
            {/* Section 1: User details */}
            <div className="flex flex-col gap-4">
              <h3 className="font-display font-bold text-xs uppercase tracking-wider text-brand-green border-b border-brand-stone-dark/40 pb-1.5 text-left">
                1. User Credentials
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex flex-col gap-1 text-left">
                  <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/80">
                    Full Name
                  </label>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="John Doe"
                    className="input-tactile text-xs"
                  />
                </div>
                <div className="flex flex-col gap-1 text-left">
                  <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/80">
                    Email Address
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="john@diner.com"
                    className="input-tactile text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex flex-col gap-1 text-left">
                  <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/80">
                    Phone (Optional)
                  </label>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+1 555-0199"
                    className="input-tactile text-xs"
                  />
                </div>
                <div></div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex flex-col gap-1 text-left">
                  <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/80">
                    Password
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Min. 8 characters"
                    className="input-tactile text-xs"
                  />
                </div>
                <div className="flex flex-col gap-1 text-left">
                  <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/80">
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter password"
                    className="input-tactile text-xs"
                  />
                </div>
              </div>
            </div>

            {/* Section 2: Org Details */}
            <div className="flex flex-col gap-4 mt-2">
              <h3 className="font-display font-bold text-xs uppercase tracking-wider text-brand-green border-b border-brand-stone-dark/40 pb-1.5 text-left">
                2. Organization Information
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex flex-col gap-1 text-left">
                  <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/80">
                    Organization Name
                  </label>
                  <input
                    type="text"
                    required
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder={role === 'restaurant' ? "Happy Diner" : "Harvest NGO"}
                    className="input-tactile text-xs"
                  />
                </div>
                <div className="flex flex-col gap-1 text-left">
                  <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/80">
                    Website Address (Optional)
                  </label>
                  <input
                    type="url"
                    value={orgWeb}
                    onChange={(e) => setOrgWeb(e.target.value)}
                    placeholder="https://www.yourorg.com"
                    className="input-tactile text-xs"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1 text-left">
                <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/80">
                  Street Address
                </label>
                <input
                  type="text"
                  required
                  value={orgAddress}
                  onChange={(e) => setOrgAddress(e.target.value)}
                  placeholder="123 Food Share Lane, City Center"
                  className="input-tactile text-xs"
                />
              </div>

              {/* Coordinates Geolocation */}
              <div className="flex flex-col gap-2">
                <div className="flex justify-between items-center">
                  <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/80">
                    Map Location Coordinates (Optional)
                  </label>
                  <button
                    type="button"
                    onClick={fetchLocation}
                    disabled={locLoading}
                    className="text-[10px] font-bold text-brand-green hover:text-brand-green-dark flex items-center gap-1 cursor-pointer disabled:opacity-50"
                  >
                    <Navigation className="w-3 h-3 animate-pulse" />
                    <span>{locLoading ? "Fetching..." : "Auto-detect Coordinates"}</span>
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center border border-brand-stone-dark rounded px-3 py-1.5 bg-brand-stone-light">
                    <MapPin className="w-3.5 h-3.5 text-brand-stone-dark mr-2" />
                    <input
                      type="number"
                      step="any"
                      value={lat}
                      onChange={(e) => setLat(e.target.value === '' ? '' : parseFloat(e.target.value))}
                      placeholder="Latitude (e.g. 40.7128)"
                      className="w-full bg-transparent text-xs outline-none focus:ring-0"
                    />
                  </div>
                  <div className="flex items-center border border-brand-stone-dark rounded px-3 py-1.5 bg-brand-stone-light">
                    <MapPin className="w-3.5 h-3.5 text-brand-stone-dark mr-2" />
                    <input
                      type="number"
                      step="any"
                      value={lon}
                      onChange={(e) => setLon(e.target.value === '' ? '' : parseFloat(e.target.value))}
                      placeholder="Longitude (e.g. -74.0060)"
                      className="w-full bg-transparent text-xs outline-none focus:ring-0"
                    />
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-1 text-left">
                <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/80">
                  Description / Mission Details
                </label>
                <textarea
                  value={orgDesc}
                  onChange={(e) => setOrgDesc(e.target.value)}
                  placeholder={role === 'restaurant' ? "We are a local family diner committed to reducing prepared food waste..." : "A local charity kitchen serving low-income families..."}
                  rows={3}
                  className="input-tactile text-xs"
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="btn-tactile-green w-full py-3 text-sm font-semibold flex items-center justify-center mt-2 disabled:opacity-50"
            >
              {loading ? 'Creating Partner Account...' : `Register as ${role === 'restaurant' ? 'Restaurant' : 'NGO'}`}
            </button>
          </form>
        </div>

        {/* Footer Navigation */}
        <div className="text-xs text-brand-stone-dark font-medium text-center">
          Already have an account?{' '}
          <button
            onClick={() => navigateTo('/login')}
            className="text-brand-green font-bold hover:underline cursor-pointer"
          >
            Log In
          </button>
        </div>

      </div>
    </div>
  );
};
