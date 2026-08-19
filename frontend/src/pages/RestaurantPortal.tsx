import React, { useEffect, useState } from 'react';
import { api, mediaUrl } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { navigateTo } from '../services/router';
import { Layout } from '../components/Layout';
import { DonutChart, AreaChart } from '../components/SVGCharts';
import { QRScanner } from '../components/QRScanner';
import { MapPicker } from '../components/MapPicker';
import { 
  AlertCircle, CheckCircle, Clock, Plus, Upload, Trash, Edit, Check, X, MapPin, 
  ShieldCheck, Heart, Activity
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
  status: 'DRAFT' | 'AVAILABLE' | 'REQUESTED' | 'ACCEPTED' | 'PICKUP_PENDING' | 'PICKED_UP' | 'COMPLETED' | 'CANCELLED' | 'EXPIRED' | 'REJECTED' | 'PICKUP_FAILED';
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

export const RestaurantPortal: React.FC<{ path: string }> = ({ path }) => {
  const { user, refreshProfile } = useAuth();
  
  // Data State
  const [donations, setDonations] = useState<Donation[]>([]);
  const [incomingClaims, setIncomingClaims] = useState<Allocation[]>([]);
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form states
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('Prepared Meals');
  const [quantity, setQuantity] = useState(1);
  const [unit, setUnit] = useState('portions');
  const [preparedAt, setPreparedAt] = useState('');
  const [expiresAt, setExpiresAt] = useState('');
  const [pickupStart, setPickupStart] = useState('');
  const [pickupEnd, setPickupEnd] = useState('');
  const [address, setAddress] = useState(user?.organization?.address || '');
  const [latitude, setLatitude] = useState<number | ''>('');
  const [longitude, setLongitude] = useState<number | ''>('');
  
  // Edit mode
  const [editId, setEditId] = useState<number | null>(null);
  
  // File upload state
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [docType, setDocType] = useState('business_license');
  const [docFile, setDocFile] = useState<File | null>(null);

  // Scanning Modal
  const [scanningAllocation, setScanningAllocation] = useState<Allocation | null>(null);

  const clearForm = () => {
    setTitle('');
    setDescription('');
    setCategory('Prepared Meals');
    setQuantity(1);
    setUnit('portions');
    setPreparedAt('');
    setExpiresAt('');
    setPickupStart('');
    setPickupEnd('');
    setAddress(user?.organization?.address || '');
    setLatitude('');
    setLongitude('');
    setEditId(null);
    setImageFile(null);
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (path === '/restaurant') {
        // Fetch listings, incoming claims, and metrics
        const listResp = await api.get('/donations/my/listings');
        setDonations(listResp.data);

        const claimsResp = await api.get('/allocations/my/incoming');
        setIncomingClaims(claimsResp.data.filter((c: Allocation) => c.status === 'REQUESTED' || c.status === 'ACCEPTED'));
        
        // Metrics compilation (mocked aggregates if endpoint is admin-only, but let's query my analytics)
        const categories = listResp.data.reduce((acc: any, curr: Donation) => {
          acc[curr.category] = (acc[curr.category] || 0) + curr.quantity;
          return acc;
        }, {});
        const categoryPoints = Object.keys(categories).map(k => ({ label: k, value: categories[k] }));
        
        setAnalyticsData({
          categoryPoints,
          totalListings: listResp.data.length,
          completedListings: listResp.data.filter((d: Donation) => d.status === 'COMPLETED').length,
          activeListings: listResp.data.filter((d: Donation) => d.status === 'AVAILABLE' || d.status === 'REQUESTED').length
        });
      } else if (path === '/restaurant/donations' || path === '/restaurant/history') {
        const listResp = await api.get('/donations/my/listings');
        setDonations(listResp.data);
      } else if (path === '/restaurant/analytics') {
        const listResp = await api.get('/donations/my/listings');
        const categories = listResp.data.reduce((acc: any, curr: Donation) => {
          acc[curr.category] = (acc[curr.category] || 0) + curr.quantity;
          return acc;
        }, {});
        const categoryPoints = Object.keys(categories).map(k => ({ label: k, value: categories[k] }));
        
        const timeline = listResp.data.map((d: Donation) => ({
          label: new Date(d.created_at).toLocaleDateString(),
          value: d.quantity
        })).slice(-10);

        setAnalyticsData({ categoryPoints, timeline });
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load restaurant data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    clearForm();
  }, [path]);

  // Geolocation
  const detectLocation = () => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude);
        setLongitude(pos.coords.longitude);
      },
      () => setError("Failed to detect location coordinates.")
    );
  };

  // Submit Donation Creation/Editing
  const handleDonationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    setError(null);
    setSuccess(null);

    const donationData = {
      title,
      description: description || undefined,
      category,
      quantity,
      unit,
      prepared_at: new Date(preparedAt).toISOString(),
      expires_at: new Date(expiresAt).toISOString(),
      pickup_start: new Date(pickupStart).toISOString(),
      pickup_end: new Date(pickupEnd).toISOString(),
      address,
      latitude: latitude !== '' ? latitude : undefined,
      longitude: longitude !== '' ? longitude : undefined
    };

    try {
      let savedDonation;
      if (editId) {
        const resp = await api.put(`/donations/${editId}`, donationData);
        savedDonation = resp.data;
        setSuccess("Donation listing edited successfully!");
      } else {
        const resp = await api.post('/donations/', donationData);
        savedDonation = resp.data;
        setSuccess("Donation draft created successfully!");
      }

      // Handle Image Upload if selected
      if (imageFile && savedDonation.id) {
        const imageForm = new FormData();
        imageForm.append('file', imageFile);
        await api.post(`/donations/${savedDonation.id}/image`, imageForm, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      }

      clearForm();
      navigateTo('/restaurant/donations');
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to submit donation details.");
    } finally {
      setActionLoading(false);
    }
  };

  // Transition draft/inactive donation to AVAILABLE
  const handlePublish = async (id: number) => {
    setActionLoading(true);
    try {
      await api.put(`/donations/${id}`, { status: 'AVAILABLE' });
      setSuccess("Donation published. It is now available for NGOs to claim!");
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Publishing failed.");
    } finally {
      setActionLoading(false);
    }
  };

  // Transition donation to CANCELLED
  const handleCancelDonation = async (id: number) => {
    if (!window.confirm("Are you sure you want to cancel this donation? This action is permanent.")) return;
    setActionLoading(true);
    try {
      await api.put(`/donations/${id}`, { status: 'CANCELLED' });
      setSuccess("Donation cancelled successfully.");
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Cancellation failed.");
    } finally {
      setActionLoading(false);
    }
  };

  // Claim Request approval/rejection
  const handleClaimStatus = async (id: number, approve: boolean) => {
    setActionLoading(true);
    try {
      const endpoint = `/allocations/${id}/${approve ? 'accept' : 'reject'}`;
      await api.post(endpoint);
      setSuccess(`NGO Claim request ${approve ? 'Approved' : 'Declined'} successfully.`);
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Claim update failed.");
    } finally {
      setActionLoading(false);
    }
  };

  // QR Scanning verify handler
  const handleQRVerify = async (code: string) => {
    if (!scanningAllocation) return;
    setActionLoading(true);
    setError(null);
    try {
      const response = await api.post('/qr/verify', {
        scanned_code: code,
        event_type: 'PICKUP' // Restaurant scans code to hand over food
      });
      if (response.data.status === 'SUCCESS') {
        setSuccess("QR Pickup verified successfully! Food handed over to NGO.");
        setScanningAllocation(null);
        loadData();
      } else {
        setError(response.data.message || "QR verification failed.");
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
      setSuccess("Verification document uploaded. Admins will review shortly.");
      setDocFile(null);
      refreshProfile();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Document upload failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const startEdit = (donation: Donation) => {
    setTitle(donation.title);
    setDescription(donation.description || '');
    setCategory(donation.category);
    setQuantity(donation.quantity);
    setUnit(donation.unit);
    
    // Parse datetimes to matches local datetime-local format
    const localPrep = donation.prepared_at.slice(0, 16);
    const localExp = donation.expires_at.slice(0, 16);
    const localStart = donation.pickup_start.slice(0, 16);
    const localEnd = donation.pickup_end.slice(0, 16);
    
    setPreparedAt(localPrep);
    setExpiresAt(localExp);
    setPickupStart(localStart);
    setPickupEnd(localEnd);
    setAddress(donation.address);
    setLatitude(donation.latitude || '');
    setLongitude(donation.longitude || '');
    setEditId(donation.id);
    navigateTo('/restaurant/create');
  };

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
      {/* Alert states */}
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
      {path === '/restaurant' && (
        <>
          {/* Dashboard Header Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="card-tactile flex items-center gap-4">
              <div className="p-3 bg-brand-green/10 text-brand-green rounded">
                <Heart className="w-6 h-6" />
              </div>
              <div className="flex flex-col text-left">
                <span className="text-[10px] text-brand-stone-dark uppercase tracking-wider font-bold">Total Posted</span>
                <span className="text-2xl font-bold">{analyticsData?.totalListings || 0} Donations</span>
              </div>
            </div>
            <div className="card-tactile flex items-center gap-4">
              <div className="p-3 bg-brand-green/10 text-brand-green rounded">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div className="flex flex-col text-left">
                <span className="text-[10px] text-brand-stone-dark uppercase tracking-wider font-bold">Completed Donations</span>
                <span className="text-2xl font-bold">{analyticsData?.completedListings || 0} Distributions</span>
              </div>
            </div>
            <div className="card-tactile flex items-center gap-4">
              <div className="p-3 bg-brand-green/10 text-brand-green rounded">
                <Activity className="w-6 h-6" />
              </div>
              <div className="flex flex-col text-left">
                <span className="text-[10px] text-brand-stone-dark uppercase tracking-wider font-bold">Active Listings</span>
                <span className="text-2xl font-bold">{analyticsData?.activeListings || 0} Live Listings</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
            {/* Incoming Requests Panel */}
            <div className="lg:col-span-2 flex flex-col gap-4">
              <h2 className="font-display font-bold text-lg text-left">Incoming NGO Claim Requests</h2>
              <div className="flex flex-col gap-4">
                {incomingClaims.length === 0 ? (
                  <div className="card-tactile text-center text-xs text-brand-stone-dark py-12">
                    No active incoming requests or pickups pending.
                  </div>
                ) : (
                  incomingClaims.map((claim) => (
                    <div key={claim.id} className="card-tactile flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                      <div className="flex flex-col text-left gap-1">
                        <span className="text-[9px] bg-brand-green/10 text-brand-green px-2 py-0.5 rounded-full w-max font-bold uppercase tracking-wider">
                          {claim.status}
                        </span>
                        <h4 className="font-display font-bold text-sm text-brand-charcoal">{claim.receiver_name}</h4>
                        <p className="text-xs text-brand-charcoal/70">
                          Requesting <strong>{claim.requested_quantity} portions</strong> of "{claim.donation?.title}"
                        </p>
                      </div>

                      <div className="flex gap-2 w-full sm:w-auto">
                        {claim.status === 'REQUESTED' && (
                          <>
                            <button
                              onClick={() => handleClaimStatus(claim.id, true)}
                              disabled={actionLoading}
                              className="btn-tactile-green text-xs px-3 py-1.5 flex items-center gap-1.5"
                            >
                              <Check className="w-3.5 h-3.5" /> Approve
                            </button>
                            <button
                              onClick={() => handleClaimStatus(claim.id, false)}
                              disabled={actionLoading}
                              className="btn-tactile-red text-xs px-3 py-1.5 flex items-center gap-1.5"
                            >
                              <X className="w-3.5 h-3.5" /> Decline
                            </button>
                          </>
                        )}
                        {claim.status === 'ACCEPTED' && (
                          <button
                            onClick={() => setScanningAllocation(claim)}
                            className="btn-tactile text-xs px-3 py-1.5 flex items-center gap-1.5"
                          >
                            Verify QR Pickup
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Side summary charts */}
            <div className="flex flex-col gap-4">
              <h2 className="font-display font-bold text-lg text-left">Category Breakdown</h2>
              <div className="card-tactile flex justify-center items-center h-64">
                {analyticsData?.categoryPoints && analyticsData.categoryPoints.length > 0 ? (
                  <DonutChart data={analyticsData.categoryPoints} />
                ) : (
                  <span className="text-xs text-brand-stone-dark">No category distribution data.</span>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* ==========================================================
          VIEW: CREATE / EDIT DONATION
          ========================================================== */}
      {path === '/restaurant/create' && (
        <div className="max-w-2xl mx-auto w-full flex flex-col gap-6">
          <h2 className="font-display font-bold text-xl text-left border-b border-brand-stone-dark pb-2">
            {editId ? 'Modify Food Donation Listing' : 'Post Excess Food Donation'}
          </h2>

          <form onSubmit={handleDonationSubmit} className="card-tactile flex flex-col gap-5">
            <div className="flex flex-col gap-1 text-left">
              <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Donation Title</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Assorted Fresh Sandwiches, Veggie Stew, etc."
                className="input-tactile text-xs"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1 text-left">
                <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="input-tactile text-xs"
                >
                  <option value="Prepared Meals">Prepared Meals</option>
                  <option value="Produce">Produce / Veggies</option>
                  <option value="Bakery">Bakery & Grains</option>
                  <option value="Dairy">Dairy Products</option>
                  <option value="Meat & Poultry">Meat & Poultry</option>
                  <option value="Beverages">Beverages</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="flex flex-col gap-1 text-left">
                  <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Quantity</label>
                  <input
                    type="number"
                    min="0.1"
                    step="any"
                    required
                    value={quantity}
                    onChange={(e) => setQuantity(parseFloat(e.target.value))}
                    className="input-tactile text-xs"
                  />
                </div>
                <div className="flex flex-col gap-1 text-left">
                  <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Unit</label>
                  <input
                    type="text"
                    required
                    value={unit}
                    onChange={(e) => setUnit(e.target.value)}
                    placeholder="portions, kg, boxes"
                    className="input-tactile text-xs"
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1 text-left">
                <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Prepared At</label>
                <input
                  type="datetime-local"
                  required
                  value={preparedAt}
                  onChange={(e) => setPreparedAt(e.target.value)}
                  className="input-tactile text-xs"
                />
              </div>
              <div className="flex flex-col gap-1 text-left">
                <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Expires At</label>
                <input
                  type="datetime-local"
                  required
                  value={expiresAt}
                  onChange={(e) => setExpiresAt(e.target.value)}
                  className="input-tactile text-xs"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1 text-left">
                <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Pickup Window Start</label>
                <input
                  type="datetime-local"
                  required
                  value={pickupStart}
                  onChange={(e) => setPickupStart(e.target.value)}
                  className="input-tactile text-xs"
                />
              </div>
              <div className="flex flex-col gap-1 text-left">
                <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Pickup Window End</label>
                <input
                  type="datetime-local"
                  required
                  value={pickupEnd}
                  onChange={(e) => setPickupEnd(e.target.value)}
                  className="input-tactile text-xs"
                />
              </div>
            </div>

            <div className="flex flex-col gap-1 text-left">
              <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Pickup Address</label>
              <input
                type="text"
                required
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                className="input-tactile text-xs"
              />
            </div>

            {/* GPS Quick-Fill */}
            <div className="flex justify-end">
              <button
                type="button"
                onClick={detectLocation}
                className="text-[10px] font-bold text-brand-green hover:underline flex items-center gap-1 cursor-pointer"
              >
                <MapPin className="w-3.5 h-3.5" /> Use My GPS Location
              </button>
            </div>

            {/* Interactive Map Picker */}
            <MapPicker
              latitude={latitude}
              longitude={longitude}
              onLocationChange={(lat, lon) => { setLatitude(lat); setLongitude(lon); }}
            />

            <div className="flex flex-col gap-1 text-left">
              <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Include allergens, storage instructions, etc."
                rows={3}
                className="input-tactile text-xs"
              />
            </div>

            {/* Food Image upload */}
            <div className="flex flex-col gap-1 text-left">
              <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Food Image Photo</label>
              <div className="flex items-center gap-4">
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setImageFile(e.target.files ? e.target.files[0] : null)}
                  className="hidden"
                  id="image-file-input"
                />
                <label
                  htmlFor="image-file-input"
                  className="btn-tactile-secondary text-xs flex items-center gap-1.5 cursor-pointer py-2 px-3"
                >
                  <Upload className="w-3.5 h-3.5" /> {imageFile ? 'Change Photo' : 'Upload Photo'}
                </label>
                {imageFile && <span className="text-xs text-brand-charcoal font-semibold">{imageFile.name}</span>}
              </div>
            </div>

            <div className="flex gap-4 mt-2">
              <button
                type="submit"
                disabled={actionLoading}
                className="btn-tactile-green flex-grow py-2.5 text-xs font-semibold"
              >
                {actionLoading ? 'Saving...' : editId ? 'Save Modifications' : 'Create Listing Draft'}
              </button>
              <button
                type="button"
                onClick={() => { clearForm(); navigateTo('/restaurant/donations'); }}
                className="btn-tactile-secondary py-2.5 text-xs"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ==========================================================
          VIEW: ACTIVE LISTINGS
          ========================================================== */}
      {path === '/restaurant/donations' && (
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h2 className="font-display font-bold text-lg text-left">Active Listings Manager</h2>
            <button
              onClick={() => { clearForm(); navigateTo('/restaurant/create'); }}
              className="btn-tactile-green text-xs flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" /> Create New Listing
            </button>
          </div>

          <div className="flex flex-col gap-4">
            {donations.filter(d => ['DRAFT', 'AVAILABLE', 'REQUESTED', 'ACCEPTED', 'PICKUP_PENDING'].includes(d.status)).length === 0 ? (
              <div className="card-tactile text-center text-xs text-brand-stone-dark py-12">
                No active listings found. Draft a donation to start.
              </div>
            ) : (
              donations.filter(d => ['DRAFT', 'AVAILABLE', 'REQUESTED', 'ACCEPTED', 'PICKUP_PENDING'].includes(d.status)).map((donation) => (
                <div key={donation.id} className="card-tactile flex flex-col sm:flex-row justify-between gap-6">
                  <div className="flex gap-4 text-left">
                    {donation.image_path ? (
                      <img
                        src={mediaUrl(donation.image_path)}
                        alt={donation.title}
                        className="w-20 h-20 rounded object-cover border border-brand-stone-dark flex-shrink-0"
                      />
                    ) : (
                      <div className="w-20 h-20 rounded bg-brand-green/10 text-brand-green flex items-center justify-center flex-shrink-0">
                        <Heart className="w-6 h-6" />
                      </div>
                    )}
                    <div className="flex flex-col gap-1">
                      <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase w-max ${
                        donation.status === 'AVAILABLE' ? 'bg-brand-green/10 text-brand-green' : 'bg-brand-amber/15 text-brand-amber'
                      }`}>
                        {donation.status}
                      </span>
                      <h3 className="font-display font-bold text-sm text-brand-charcoal">{donation.title}</h3>
                      <p className="text-xs text-brand-charcoal/70">
                        Quantity: <strong>{donation.quantity} {donation.unit}</strong> | Category: {donation.category}
                      </p>
                      <span className="text-[10px] text-brand-stone-dark flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" /> Expiration: {new Date(donation.expires_at).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <div className="flex sm:flex-col justify-end items-end gap-2">
                    {donation.status === 'DRAFT' && (
                      <button
                        onClick={() => handlePublish(donation.id)}
                        disabled={actionLoading}
                        className="btn-tactile-green text-xs w-full sm:w-28 py-1.5 flex items-center justify-center gap-1.5"
                      >
                        Publish Live
                      </button>
                    )}
                    <button
                      onClick={() => startEdit(donation)}
                      className="btn-tactile-secondary text-xs w-full sm:w-28 py-1.5 flex items-center justify-center gap-1.5"
                    >
                      <Edit className="w-3.5 h-3.5" /> Edit Details
                    </button>
                    <button
                      onClick={() => handleCancelDonation(donation.id)}
                      className="btn-tactile-secondary border-brand-red/30 hover:bg-brand-red/5 text-brand-red text-xs w-full sm:w-28 py-1.5 flex items-center justify-center gap-1.5"
                    >
                      <Trash className="w-3.5 h-3.5" /> Cancel Food
                    </button>
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
      {path === '/restaurant/history' && (
        <div className="flex flex-col gap-4 text-left">
          <h2 className="font-display font-bold text-lg">Platform Redistribution Logs</h2>
          <div className="card-tactile overflow-x-auto p-0">
            <table className="w-full text-xs font-semibold">
              <thead>
                <tr className="bg-brand-stone border-b border-brand-stone-dark/80 text-brand-stone-dark text-left">
                  <th className="p-4">Listing ID</th>
                  <th className="p-4">Donation Title</th>
                  <th className="p-4">Quantity</th>
                  <th className="p-4">Final Status</th>
                  <th className="p-4">Posted Date</th>
                  <th className="p-4">Expiration</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-stone-dark/30 font-medium">
                {donations.filter(d => ['COMPLETED', 'CANCELLED', 'EXPIRED', 'REJECTED', 'PICKUP_FAILED'].includes(d.status)).length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-brand-stone-dark text-xs">
                      No historical listings logged.
                    </td>
                  </tr>
                ) : (
                  donations.filter(d => ['COMPLETED', 'CANCELLED', 'EXPIRED', 'REJECTED', 'PICKUP_FAILED'].includes(d.status)).map((d) => (
                    <tr key={d.id} className="hover:bg-brand-stone/20">
                      <td className="p-4 font-bold">#{d.id}</td>
                      <td className="p-4">{d.title}</td>
                      <td className="p-4">{d.quantity} {d.unit}</td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          d.status === 'COMPLETED' ? 'bg-brand-green/10 text-brand-green' : 'bg-brand-red/10 text-brand-red'
                        }`}>
                          {d.status}
                        </span>
                      </td>
                      <td className="p-4">{new Date(d.created_at).toLocaleDateString()}</td>
                      <td className="p-4">{new Date(d.expires_at).toLocaleString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ==========================================================
          VIEW: ANALYTICS
          ========================================================== */}
      {path === '/restaurant/analytics' && (
        <div className="flex flex-col gap-8 text-left">
          <h2 className="font-display font-bold text-lg">My Environmental & Social Impact</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="card-tactile flex flex-col gap-4">
              <h3 className="font-display font-bold text-xs uppercase tracking-wider text-brand-stone-dark">Redistribution Activity Timeline</h3>
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
          VIEW: PROFILE / VERIFICATION DOCUMENTS
          ========================================================== */}
      {path === '/restaurant/profile' && (
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
                  <option value="business_license">Business License / Registration</option>
                  <option value="food_permit">Food Safety Permit</option>
                  <option value="tax_exemption">Tax Exemption Certification</option>
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
                    id="doc-file-input"
                  />
                  <label
                    htmlFor="doc-file-input"
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
                      <span>All uploaded credentials have been verified. You can post live donations.</span>
                    </div>
                  </div>
                ) : (
                  <div className="border border-brand-amber/30 bg-brand-amber/5 text-brand-amber p-4 rounded text-xs flex items-start gap-2">
                    <AlertCircle className="w-4.5 h-4.5 mt-0.5" />
                    <div className="flex flex-col text-left gap-0.5">
                      <strong>Verification Pending ({user?.organization?.verification_status})</strong>
                      <span>Please upload your food permit or business license. Administrative verification takes up to 24 hours.</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==========================================================
          QR SCANNING MODAL OVERLAY
          ========================================================== */}
      {scanningAllocation && (
        <div className="fixed inset-0 bg-brand-charcoal/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white border border-brand-stone-dark rounded p-6 shadow-xl flex flex-col gap-4 relative">
            <button
              onClick={() => setScanningAllocation(null)}
              className="absolute top-4 right-4 text-brand-stone-dark hover:text-brand-charcoal cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
            
            <h3 className="font-display font-bold text-base text-brand-charcoal text-left">
              Confirm Food Handover
            </h3>
            <p className="text-xs text-brand-charcoal/70 text-left -mt-1">
              Verify claims code for <strong>{scanningAllocation.receiver_name}</strong> ({scanningAllocation.requested_quantity} portions).
            </p>

            <QRScanner
              onScanSuccess={handleQRVerify}
              placeholderText="Enter secure NGO claim token..."
            />
          </div>
        </div>
      )}
    </Layout>
  );
};
