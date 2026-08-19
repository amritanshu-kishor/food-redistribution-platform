import React, { useEffect, useState } from 'react';
import { api, mediaUrl } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { navigateTo } from '../services/router';
import { Layout } from '../components/Layout';
import { DonutChart, AreaChart } from '../components/SVGCharts';
import { QRScanner } from '../components/QRScanner';
import { DonationsMap } from '../components/DonationsMap';
import { 
  AlertCircle, CheckCircle, Clock, Search, X, ShieldCheck, 
  Heart, ArrowRight, Navigation, Upload, LayoutGrid, Map
} from 'lucide-react';

interface Donation {
  id: number;
  title: string;
  description?: string;
  image_path?: string;
  category: string;
  quantity: number;
  unit: string;
  prepared_at: string;
  expires_at: string;
  pickup_start: string;
  pickup_end: string;
  status: string;
  address: string;
  latitude?: number;
  longitude?: number;
  created_at: string;
  donor_name?: string;
}

interface Allocation {
  id: number;
  donation_id: number;
  receiver_id: number;
  requested_quantity: number;
  allocated_quantity: number;
  status: 'REQUESTED' | 'ACCEPTED' | 'PICKED_UP' | 'COMPLETED' | 'CANCELLED' | 'REJECTED' | 'FAILED';
  qr_token?: string;
  created_at: string;
  receiver_name: string;
  donation?: Donation;
}

export const NGOPortal: React.FC<{ path: string }> = ({ path }) => {
  const { user, refreshProfile } = useAuth();
  
  // Data States
  const [donations, setDonations] = useState<Donation[]>([]);
  const [myClaims, setMyClaims] = useState<Allocation[]>([]);
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Browse Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [onlyUrgent, setOnlyUrgent] = useState(false);
  const [maxDistance, setMaxDistance] = useState<number | ''>('');
  
  // Active Browse Details Modal
  const [selectedDonation, setSelectedDonation] = useState<Donation | null>(null);
  const [requestedQty, setRequestedQty] = useState(1);

  // QR Scanning Delivery Modal
  const [verifyingClaim, setVerifyingClaim] = useState<Allocation | null>(null);

  // Browse view mode: 'grid' | 'map'
  const [browseView, setBrowseView] = useState<'grid' | 'map'>('grid');

  // File upload state for verification documents
  const [docType, setDocType] = useState('tax_exemption');
  const [docFile, setDocFile] = useState<File | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (path === '/ngo') {
        const claimsResp = await api.get('/allocations/my/claims');
        setMyClaims(claimsResp.data);

        // Metrics calculations
        const completed = claimsResp.data.filter((c: Allocation) => c.status === 'COMPLETED');
        const active = claimsResp.data.filter((c: Allocation) => ['REQUESTED', 'ACCEPTED', 'PICKED_UP'].includes(c.status));
        const totalMeals = completed.reduce((acc: number, curr: Allocation) => acc + curr.allocated_quantity, 0);

        setAnalyticsData({
          totalClaims: claimsResp.data.length,
          completedClaims: completed.length,
          activeClaims: active.length,
          totalMeals
        });
      } else if (path === '/ngo/browse') {
        // Get user geolocation to enable distance filtering
        const getLocation = (): Promise<{ lat: number; lon: number } | null> =>
          new Promise((resolve) => {
            if (!navigator.geolocation) { resolve(null); return; }
            navigator.geolocation.getCurrentPosition(
              (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
              () => resolve(null),
              { timeout: 3000 }
            );
          });
        const loc = await getLocation();
        const params: Record<string, any> = { limit: 50 };
        if (loc) { params.user_lat = loc.lat; params.user_lon = loc.lon; }
        const listResp = await api.get('/donations/browse', { params });
        setDonations(listResp.data);
      } else if (path === '/ngo/claims' || path === '/ngo/history') {
        const claimsResp = await api.get('/allocations/my/claims');
        setMyClaims(claimsResp.data);
      } else if (path === '/ngo/analytics') {
        const claimsResp = await api.get('/allocations/my/claims');
        const completed = claimsResp.data.filter((c: Allocation) => c.status === 'COMPLETED');
        
        const categories = completed.reduce((acc: any, curr: Allocation) => {
          if (curr.donation) {
            acc[curr.donation.category] = (acc[curr.donation.category] || 0) + curr.allocated_quantity;
          }
          return acc;
        }, {});
        const categoryPoints = Object.keys(categories).map(k => ({ label: k, value: categories[k] }));

        const timeline = completed.map((c: Allocation) => ({
          label: new Date(c.created_at).toLocaleDateString(),
          value: c.allocated_quantity
        })).slice(-10);

        setAnalyticsData({ categoryPoints, timeline });
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load NGO data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    setSelectedDonation(null);
    setRequestedQty(1);
  }, [path]);

  // Haversine distance formula to calculate distance between NGO and Donation
  const calculateDistance = (lat1: number, lon1: number, lat2?: number, lon2?: number) => {
    if (!lat2 || !lon2) return null;
    const R = 6371; // Radius of earth in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
      Math.sin(dLat/2) * Math.sin(dLat/2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
      Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    const d = R * c;
    return Math.round(d * 10) / 10; // returns km rounded to 1 decimal place
  };

  // Filter available donations
  const getFilteredDonations = () => {
    return donations.filter((d) => {
      // Must be available for claims
      if (d.status !== 'AVAILABLE' && d.status !== 'REQUESTED') return false;

      // Text search
      if (searchTerm && !d.title.toLowerCase().includes(searchTerm.toLowerCase())) return false;

      // Category filter
      if (filterCategory && d.category !== filterCategory) return false;

      // Expiry filter (Urgent = expiring within 6 hours)
      if (onlyUrgent) {
        const timeDiff = new Date(d.expires_at).getTime() - new Date().getTime();
        const hoursLeft = timeDiff / (1000 * 60 * 60);
        if (hoursLeft > 6 || hoursLeft < 0) return false;
      }

      // Distance radius filter
      if (maxDistance !== '' && user?.organization?.latitude && user?.organization?.longitude) {
        const distance = calculateDistance(
          user.organization.latitude,
          user.organization.longitude,
          d.latitude,
          d.longitude
        );
        if (distance === null || distance > maxDistance) return false;
      }

      return true;
    });
  };

  // Submit Claim Request
  const handleClaimSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDonation) return;
    setActionLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await api.post('/allocations/', {
        donation_id: selectedDonation.id,
        requested_quantity: requestedQty
      });
      setSuccess(`Claim for ${requestedQty} ${selectedDonation.unit} submitted successfully!`);
      setSelectedDonation(null);
      navigateTo('/ngo/claims');
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to claim food. Check available quantities.");
    } finally {
      setActionLoading(false);
    }
  };

  // Verify Delivery Handover (NGO scanner verifying DELIVERY)
  const handleDeliveryVerify = async (code: string) => {
    if (!verifyingClaim) return;
    setActionLoading(true);
    setError(null);
    try {
      const response = await api.post('/qr/verify', {
        scanned_code: code,
        event_type: 'DELIVERY' // NGO completes handover to community
      });
      if (response.data.status === 'SUCCESS') {
        setSuccess("Delivery completion successfully verified!");
        setVerifyingClaim(null);
        loadData();
      } else {
        setError(response.data.message || "Delivery verification failed.");
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Verification error.");
    } finally {
      setActionLoading(false);
    }
  };

  // Document Upload
  const handleDocUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docFile) return;
    setActionLoading(true);
    setError(null);
    setSuccess(null);

    const docForm = new FormData();
    docForm.append('doc_type', docType);
    docForm.append('file', docFile);

    try {
      await api.post('/users/documents', docForm, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setSuccess("Verification credentials uploaded successfully.");
      setDocFile(null);
      refreshProfile();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to upload document.");
    } finally {
      setActionLoading(false);
    }
  };

  const filteredDonations = getFilteredDonations();

  if (loading) {
    return (
      <Layout activePath={path}>
        <div className="flex justify-center items-center h-64">
          <div className="w-8 h-8 rounded-full border-2 border-brand-stone-dark border-t-brand-green animate-spin"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout activePath={path}>
      {/* Alert boxes */}
      {success && (
        <div className="bg-brand-green/10 border border-brand-green/30 text-brand-green text-xs rounded p-4 font-semibold flex items-center gap-2">
          <CheckCircle className="w-5 h-5" />
          <span>{success}</span>
        </div>
      )}

      {error && (
        <div className="bg-brand-red/10 border border-brand-red/30 text-brand-red text-xs rounded p-4 font-semibold flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      )}

      {/* ==========================================================
          VIEW: DASHBOARD
          ========================================================== */}
      {path === '/ngo' && (
        <>
          {/* Dashboard Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="card-tactile flex items-center gap-4">
              <div className="p-3 bg-brand-green/10 text-brand-green rounded">
                <Heart className="w-6 h-6" />
              </div>
              <div className="flex flex-col text-left">
                <span className="text-[10px] text-brand-stone-dark uppercase tracking-wider font-bold">Total Portions Received</span>
                <span className="text-2xl font-bold">{analyticsData?.totalMeals || 0} Portions</span>
              </div>
            </div>
            <div className="card-tactile flex items-center gap-4">
              <div className="p-3 bg-brand-green/10 text-brand-green rounded">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div className="flex flex-col text-left">
                <span className="text-[10px] text-brand-stone-dark uppercase tracking-wider font-bold">Completed Distributions</span>
                <span className="text-2xl font-bold">{analyticsData?.completedClaims || 0} Claims</span>
              </div>
            </div>
            <div className="card-tactile flex items-center gap-4">
              <div className="p-3 bg-brand-green/10 text-brand-green rounded">
                <Clock className="w-6 h-6" />
              </div>
              <div className="flex flex-col text-left">
                <span className="text-[10px] text-brand-stone-dark uppercase tracking-wider font-bold">Active Deliveries</span>
                <span className="text-2xl font-bold">{analyticsData?.activeClaims || 0} In-Flight</span>
              </div>
            </div>
          </div>

          {/* Quick actions & browse nudge */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-start text-left">
            <div className="md:col-span-2 flex flex-col gap-4">
              <h2 className="font-display font-bold text-lg">My Active Claims & Pickups</h2>
              <div className="flex flex-col gap-4">
                {myClaims.filter(c => ['REQUESTED', 'ACCEPTED', 'PICKED_UP'].includes(c.status)).length === 0 ? (
                  <div className="card-tactile text-center text-xs text-brand-stone-dark py-12 flex flex-col gap-3 items-center">
                    <span>No active claims registered. Browse local excess food to claim.</span>
                    <button
                      onClick={() => navigateTo('/ngo/browse')}
                      className="btn-tactile-green text-xs flex items-center gap-1"
                    >
                      <span>Browse Foods</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  myClaims.filter(c => ['REQUESTED', 'ACCEPTED', 'PICKED_UP'].includes(c.status)).map((claim) => (
                    <div key={claim.id} className="card-tactile flex flex-col sm:flex-row justify-between gap-4 items-start sm:items-center">
                      <div className="flex flex-col gap-1">
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase w-max ${
                          claim.status === 'ACCEPTED' ? 'bg-brand-green/10 text-brand-green' : 'bg-brand-amber/15 text-brand-amber'
                        }`}>
                          {claim.status}
                        </span>
                        <h4 className="font-display font-bold text-sm text-brand-charcoal">{claim.donation?.title}</h4>
                        <p className="text-xs text-brand-charcoal/70">
                          Donor: <strong>{claim.donation?.address}</strong> | Qty: {claim.requested_quantity} portions
                        </p>
                      </div>

                      <button
                        onClick={() => navigateTo('/ngo/claims')}
                        className="btn-tactile text-xs flex items-center gap-1"
                      >
                        View QR Instructions
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="card-tactile flex flex-col gap-4">
              <h3 className="font-display font-bold text-xs uppercase tracking-wider text-brand-stone-dark">Redistribution Impact</h3>
              <div className="h-48 flex items-center justify-center">
                {analyticsData?.totalMeals > 0 ? (
                  <div className="text-center flex flex-col gap-1">
                    <span className="text-4xl font-extrabold text-brand-green">{analyticsData.totalMeals}</span>
                    <span className="text-xs text-brand-charcoal/70 font-semibold">Meals delivered to date</span>
                  </div>
                ) : (
                  <span className="text-xs text-brand-stone-dark">Claims data unavailable.</span>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* ==========================================================
          VIEW: BROWSE FOODS
          ========================================================== */}
      {path === '/ngo/browse' && (
        <div className="flex flex-col gap-6 text-left">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <h2 className="font-display font-bold text-lg">Browse Available Excess Foods</h2>
            {/* View Mode Toggle */}
            <div className="flex bg-brand-stone border border-brand-stone-dark rounded overflow-hidden text-xs font-bold">
              <button
                onClick={() => setBrowseView('grid')}
                className={`flex items-center gap-1.5 px-3 py-2 transition-all ${browseView === 'grid' ? 'bg-brand-charcoal text-white' : 'text-brand-charcoal/70 hover:bg-brand-stone-dark/20'}`}
              >
                <LayoutGrid className="w-3.5 h-3.5" /> Grid View
              </button>
              <button
                onClick={() => setBrowseView('map')}
                className={`flex items-center gap-1.5 px-3 py-2 transition-all ${browseView === 'map' ? 'bg-brand-charcoal text-white' : 'text-brand-charcoal/70 hover:bg-brand-stone-dark/20'}`}
              >
                <Map className="w-3.5 h-3.5" /> Map View
              </button>
            </div>
          </div>

          {/* Advanced Filter panel — only show in grid view */}
          {browseView === 'grid' && (
            <div className="card-tactile grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 bg-white">
              <div className="flex flex-col gap-1">
                <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/70">Search Title</label>
                <div className="relative">
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Stew, bread, salad..."
                    className="input-tactile text-xs pr-8"
                  />
                  <Search className="w-3.5 h-3.5 absolute right-3 top-1/2 -translate-y-1/2 text-brand-stone-dark" />
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/70">Category</label>
                <select
                  value={filterCategory}
                  onChange={(e) => setFilterCategory(e.target.value)}
                  className="input-tactile text-xs"
                >
                  <option value="">All Categories</option>
                  <option value="Prepared Meals">Prepared Meals</option>
                  <option value="Produce">Produce / Veggies</option>
                  <option value="Bakery">Bakery & Grains</option>
                  <option value="Dairy">Dairy Products</option>
                  <option value="Meat & Poultry">Meat & Poultry</option>
                  <option value="Beverages">Beverages</option>
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/70">Distance Radius (km)</label>
                <input
                  type="number"
                  value={maxDistance}
                  onChange={(e) => setMaxDistance(e.target.value === '' ? '' : parseFloat(e.target.value))}
                  placeholder="Maximum km distance..."
                  className="input-tactile text-xs"
                />
              </div>

              <div className="flex items-center gap-2 mt-4 sm:mt-6 pl-2">
                <input
                  type="checkbox"
                  id="urgent-check"
                  checked={onlyUrgent}
                  onChange={(e) => setOnlyUrgent(e.target.checked)}
                  className="w-4 h-4 text-brand-green border-brand-stone-dark rounded focus:ring-brand-green/20"
                />
                <label htmlFor="urgent-check" className="text-xs font-semibold text-brand-charcoal select-none cursor-pointer">
                  Expiring soon (&lt; 6 hrs)
                </label>
              </div>
            </div>
          )}

          {/* Map View */}
          {browseView === 'map' && (
            <DonationsMap
              donations={filteredDonations}
              onClaimClick={(donation) => setSelectedDonation(donation)}
            />
          )}

          {/* Results Grid */}
          {browseView === 'grid' && (

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredDonations.length === 0 ? (
              <div className="col-span-full card-tactile text-center text-xs text-brand-stone-dark py-16">
                No matching food listings found in your area.
              </div>
            ) : (
              filteredDonations.map((donation) => {
                const distance = user?.organization?.latitude && user?.organization?.longitude
                  ? calculateDistance(
                      user.organization.latitude,
                      user.organization.longitude,
                      donation.latitude,
                      donation.longitude
                    )
                  : null;

                const timeDiff = new Date(donation.expires_at).getTime() - new Date().getTime();
                const hoursLeft = Math.max(0, Math.round(timeDiff / (1000 * 60 * 60) * 10) / 10);
                const isUrgent = hoursLeft <= 6;

                return (
                  <div key={donation.id} className="card-tactile flex flex-col h-full justify-between gap-4 hover:shadow-md transition-shadow">
                    <div className="flex flex-col gap-2">
                      {donation.image_path ? (
                        <img
                          src={mediaUrl(donation.image_path)}
                          alt={donation.title}
                          className="w-full h-36 rounded object-cover border border-brand-stone-dark"
                        />
                      ) : (
                        <div className="w-full h-36 rounded bg-brand-green/5 text-brand-green flex items-center justify-center border border-brand-stone-dark/30">
                          <Heart className="w-8 h-8" />
                        </div>
                      )}
                      
                      <div className="flex justify-between items-center mt-1">
                        <span className="text-[9px] uppercase tracking-wider font-bold text-brand-stone-dark">
                          {donation.category}
                        </span>
                        {distance !== null && (
                          <span className="text-[10px] font-bold text-brand-green flex items-center gap-0.5">
                            <Navigation className="w-3 h-3" /> {distance} km away
                          </span>
                        )}
                      </div>

                      <h3 className="font-display font-bold text-base text-brand-charcoal -mt-1 leading-tight">
                        {donation.title}
                      </h3>
                      
                      <p className="text-xs text-brand-charcoal/70 line-clamp-2">
                        {donation.description || 'No description provided.'}
                      </p>
                    </div>

                    <div className="flex flex-col gap-3 border-t border-brand-stone/40 pt-3">
                      <div className="flex justify-between text-[11px] font-bold">
                        <span className="text-brand-charcoal">Qty: {donation.quantity} {donation.unit}</span>
                        <span className={isUrgent ? 'text-brand-red animate-pulse' : 'text-brand-charcoal/80'}>
                          Expires in {hoursLeft} hrs
                        </span>
                      </div>
                      
                      <button
                        onClick={() => setSelectedDonation(donation)}
                        className="btn-tactile-green text-xs w-full py-2 flex justify-center items-center gap-1.5"
                      >
                        Claim portions
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
          )} {/* end browseView === 'grid' results grid */}
        </div>
      )}


      {/* ==========================================================
          VIEW: MY CLAIMS / REQUESTS
          ========================================================== */}
      {path === '/ngo/claims' && (
        <div className="flex flex-col gap-6 text-left">
          <h2 className="font-display font-bold text-lg">My Claims & Pickup QR Codes</h2>
          
          <div className="flex flex-col gap-4">
            {myClaims.filter(c => ['REQUESTED', 'ACCEPTED', 'PICKED_UP'].includes(c.status)).length === 0 ? (
              <div className="card-tactile text-center text-xs text-brand-stone-dark py-12">
                No active claims found.
              </div>
            ) : (
              myClaims.filter(c => ['REQUESTED', 'ACCEPTED', 'PICKED_UP'].includes(c.status)).map((claim) => (
                <div key={claim.id} className="card-tactile flex flex-col lg:flex-row justify-between gap-6">
                  
                  {/* Claim Metadata */}
                  <div className="flex-1 flex flex-col gap-2 text-left">
                    <div className="flex items-center gap-2">
                      <span className={`text-[9px] font-bold px-2.5 py-0.5 rounded-full uppercase ${
                        claim.status === 'ACCEPTED' ? 'bg-brand-green/10 text-brand-green' : 'bg-brand-amber/15 text-brand-amber'
                      }`}>
                        {claim.status}
                      </span>
                      <span className="text-xs font-bold text-brand-stone-dark">Claim #{claim.id}</span>
                    </div>

                    <h3 className="font-display font-bold text-base text-brand-charcoal">
                      {claim.donation?.title}
                    </h3>

                    <p className="text-xs text-brand-charcoal/80 leading-relaxed">
                      Donor Address: <strong>{claim.donation?.address}</strong> <br />
                      Claimed: <strong>{claim.requested_quantity} portions</strong>
                    </p>

                    <div className="flex items-center gap-2 mt-2 bg-brand-stone-light border border-brand-stone-dark/40 rounded p-3 text-[11px] text-brand-charcoal/70">
                      <Clock className="w-4 h-4 text-brand-green" />
                      <span>
                        Pickup window: {claim.donation?.pickup_start ? new Date(claim.donation.pickup_start).toLocaleString() : ''} - {claim.donation?.pickup_end ? new Date(claim.donation.pickup_end).toLocaleString() : ''}
                      </span>
                    </div>
                  </div>

                  {/* QR code renderer & completion control */}
                  <div className="w-full lg:w-72 flex flex-col items-center gap-4 bg-brand-stone-light border border-brand-stone-dark rounded p-6">
                    {claim.status === 'ACCEPTED' && claim.qr_token && (
                      <>
                        <span className="text-[10px] text-brand-stone-dark uppercase tracking-wider font-bold">Secure Pickup QR</span>
                        <img
                          src={`https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${claim.qr_token}`}
                          alt="Secure Pickup QR"
                          className="w-36 h-36 border border-brand-stone-dark rounded p-1 bg-white"
                        />
                        <div className="text-center flex flex-col gap-0.5">
                          <span className="text-[9px] text-brand-stone-dark uppercase tracking-wider font-semibold">Verification Code</span>
                          <span className="text-xs font-mono font-bold text-brand-charcoal">{claim.qr_token}</span>
                        </div>
                      </>
                    )}

                    {claim.status === 'PICKED_UP' && (
                      <div className="flex flex-col items-center gap-3 text-center w-full">
                        <span className="text-xs font-bold text-brand-charcoal">Food Picked Up!</span>
                        <p className="text-[11px] text-brand-charcoal/70">
                          Confirm that delivery to local shelters or families has been successfully completed.
                        </p>
                        <button
                          onClick={() => setVerifyingClaim(claim)}
                          className="btn-tactile-green text-xs w-full py-2 flex items-center justify-center gap-1.5"
                        >
                          Verify Delivery Completion
                        </button>
                      </div>
                    )}

                    {claim.status === 'REQUESTED' && (
                      <span className="text-xs font-bold text-brand-amber text-center my-auto">
                        Waiting for donor approval...
                      </span>
                    )}
                  </div>
                  
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ==========================================================
          VIEW: CLAIM HISTORY
          ========================================================== */}
      {path === '/ngo/history' && (
        <div className="flex flex-col gap-4 text-left">
          <h2 className="font-display font-bold text-lg">My Historical Claims Log</h2>
          <div className="card-tactile overflow-x-auto p-0">
            <table className="w-full text-xs font-semibold">
              <thead>
                <tr className="bg-brand-stone border-b border-brand-stone-dark/80 text-brand-stone-dark text-left">
                  <th className="p-4">Claim ID</th>
                  <th className="p-4">Food Item</th>
                  <th className="p-4">Claimed Quantity</th>
                  <th className="p-4">Final Status</th>
                  <th className="p-4">Date Claimed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-stone-dark/30 font-medium">
                {myClaims.filter(c => ['COMPLETED', 'CANCELLED', 'REJECTED', 'FAILED'].includes(c.status)).length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-6 text-center text-brand-stone-dark text-xs">
                      No historical claims logged.
                    </td>
                  </tr>
                ) : (
                  myClaims.filter(c => ['COMPLETED', 'CANCELLED', 'REJECTED', 'FAILED'].includes(c.status)).map((c) => (
                    <tr key={c.id} className="hover:bg-brand-stone/20">
                      <td className="p-4 font-bold">#{c.id}</td>
                      <td className="p-4">{c.donation?.title}</td>
                      <td className="p-4">{c.allocated_quantity || c.requested_quantity} portions</td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          c.status === 'COMPLETED' ? 'bg-brand-green/10 text-brand-green' : 'bg-brand-red/10 text-brand-red'
                        }`}>
                          {c.status}
                        </span>
                      </td>
                      <td className="p-4">{new Date(c.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ==========================================================
          VIEW: IMPACT & ANALYTICS
          ========================================================== */}
      {path === '/ngo/analytics' && (
        <div className="flex flex-col gap-8 text-left">
          <h2 className="font-display font-bold text-lg">My Social Redistribution Impact</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="card-tactile flex flex-col gap-4">
              <h3 className="font-display font-bold text-xs uppercase tracking-wider text-brand-stone-dark">Redistributed Food Timeline</h3>
              <div className="h-64 flex justify-center items-center">
                {analyticsData?.timeline && analyticsData.timeline.length > 0 ? (
                  <AreaChart data={analyticsData.timeline} />
                ) : (
                  <span className="text-xs text-brand-stone-dark">No timeline activity to display.</span>
                )}
              </div>
            </div>

            <div className="card-tactile flex flex-col gap-4">
              <h3 className="font-display font-bold text-xs uppercase tracking-wider text-brand-stone-dark">Category Distributions</h3>
              <div className="h-64 flex justify-center items-center">
                {analyticsData?.categoryPoints && analyticsData.categoryPoints.length > 0 ? (
                  <DonutChart data={analyticsData.categoryPoints} />
                ) : (
                  <span className="text-xs text-brand-stone-dark">No category distribution data.</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==========================================================
          VIEW: PROFILE / DOCUMENTS
          ========================================================== */}
      {path === '/ngo/profile' && (
        <div className="max-w-2xl mx-auto w-full flex flex-col gap-6 text-left">
          <h2 className="font-display font-bold text-xl border-b border-brand-stone-dark pb-2">
            Verification Credentials & Documents
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Upload form */}
            <form onSubmit={handleDocUpload} className="card-tactile flex flex-col gap-4">
              <h3 className="font-display font-bold text-sm text-brand-green">Submit Verification Document</h3>
              
              <div className="flex flex-col gap-1">
                <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/80">Document Type</label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="input-tactile text-xs"
                >
                  <option value="tax_exemption">Tax Exemption Certification (501c3)</option>
                  <option value="ngo_license">NGO Operating License</option>
                  <option value="audit_statement">Recent Audit Statement</option>
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[9px] uppercase tracking-wider font-bold text-brand-charcoal/80">Document File (PDF / Image)</label>
                <div className="flex items-center gap-2">
                  <input
                    type="file"
                    required
                    accept=".pdf,image/*"
                    onChange={(e) => setDocFile(e.target.files ? e.target.files[0] : null)}
                    className="hidden"
                    id="ngo-doc-file-input"
                  />
                  <label
                    htmlFor="ngo-doc-file-input"
                    className="btn-tactile-secondary text-xs flex items-center gap-1.5 cursor-pointer"
                  >
                    <Upload className="w-3.5 h-3.5" /> Choose File
                  </label>
                  {docFile && <span className="text-xs text-brand-charcoal font-semibold truncate max-w-[150px]">{docFile.name}</span>}
                </div>
              </div>

              <button
                type="submit"
                disabled={actionLoading || !docFile}
                className="btn-tactile-green w-full text-xs font-semibold py-2.5 mt-2"
              >
                {actionLoading ? 'Uploading...' : 'Submit Document'}
              </button>
            </form>

            {/* Document status history */}
            <div className="card-tactile flex flex-col gap-4">
              <h3 className="font-display font-bold text-sm text-brand-charcoal">Submission Status</h3>
              <div className="flex flex-col gap-3">
                {user?.organization?.verification_status === 'approved' ? (
                  <div className="border border-brand-green/30 bg-brand-green/5 text-brand-green p-4 rounded text-xs flex items-start gap-2">
                    <ShieldCheck className="w-4.5 h-4.5 mt-0.5" />
                    <div className="flex flex-col text-left gap-0.5">
                      <strong>Partner Fully Verified</strong>
                      <span>All uploaded credentials have been verified. You can browse and claim live donations.</span>
                    </div>
                  </div>
                ) : (
                  <div className="border border-brand-amber/30 bg-brand-amber/5 text-brand-amber p-4 rounded text-xs flex items-start gap-2">
                    <AlertCircle className="w-4.5 h-4.5 mt-0.5" />
                    <div className="flex flex-col text-left gap-0.5">
                      <strong>Verification Pending ({user?.organization?.verification_status})</strong>
                      <span>Please upload your Tax Exemption (501c3) or operating license. Administrative verification takes up to 24 hours.</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==========================================================
          DETAILS MODAL / SUBMIT CLAIM FORM
          ========================================================== */}
      {selectedDonation && (
        <div className="fixed inset-0 bg-brand-charcoal/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-white border border-brand-stone-dark rounded p-6 shadow-xl flex flex-col gap-4 relative text-left">
            <button
              onClick={() => setSelectedDonation(null)}
              className="absolute top-4 right-4 text-brand-stone-dark hover:text-brand-charcoal cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
            
            <h3 className="font-display font-bold text-lg text-brand-charcoal">
              {selectedDonation.title}
            </h3>
            
            <span className="text-[10px] uppercase font-bold text-brand-stone-dark bg-brand-stone px-2 py-0.5 rounded w-max">
              {selectedDonation.category}
            </span>

            <div className="text-xs text-brand-charcoal/80 flex flex-col gap-2 bg-brand-stone-light border border-brand-stone-dark rounded p-4">
              <div><strong>Description:</strong> {selectedDonation.description || 'No description provided.'}</div>
              <div><strong>Pickup Location Address:</strong> {selectedDonation.address}</div>
              <div><strong>Prepared Time:</strong> {new Date(selectedDonation.prepared_at).toLocaleString()}</div>
              <div><strong>Expires:</strong> {new Date(selectedDonation.expires_at).toLocaleString()}</div>
            </div>

            <form onSubmit={handleClaimSubmit} className="flex flex-col gap-4 mt-2">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/70">
                  Requested Portion Quantity (Available: {selectedDonation.quantity} {selectedDonation.unit})
                </label>
                <input
                  type="number"
                  min="0.1"
                  max={selectedDonation.quantity}
                  step="any"
                  required
                  value={requestedQty}
                  onChange={(e) => setRequestedQty(parseFloat(e.target.value))}
                  className="input-tactile text-sm"
                />
              </div>

              <button
                type="submit"
                disabled={actionLoading || user?.status !== 'active'}
                className="btn-tactile-green py-2.5 text-xs font-semibold disabled:opacity-50"
              >
                {user?.status !== 'active' ? 'Account Pending Verification' : actionLoading ? 'Submitting request...' : 'Confirm Food Claim Request'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* ==========================================================
          DELIVERY VERIFICATION MODAL OVERLAY
          ========================================================== */}
      {verifyingClaim && (
        <div className="fixed inset-0 bg-brand-charcoal/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white border border-brand-stone-dark rounded p-6 shadow-xl flex flex-col gap-4 relative">
            <button
              onClick={() => setVerifyingClaim(null)}
              className="absolute top-4 right-4 text-brand-stone-dark hover:text-brand-charcoal cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
            
            <h3 className="font-display font-bold text-base text-brand-charcoal text-left">
              Confirm Delivery Handover
            </h3>
            <p className="text-xs text-brand-charcoal/70 text-left -mt-1">
              Verify claims code for delivery of <strong>{verifyingClaim.requested_quantity} portions</strong> of "{verifyingClaim.donation?.title}".
            </p>

            <QRScanner
              onScanSuccess={handleDeliveryVerify}
              placeholderText="Enter secure delivery code..."
            />
          </div>
        </div>
      )}
    </Layout>
  );
};
