import React, { useEffect, useState } from 'react';
import { api, mediaUrl } from '../services/api';
import { Layout } from '../components/Layout';
import { DonutChart, AreaChart } from '../components/SVGCharts';
import { 
  AlertCircle, CheckCircle, ShieldAlert, Users, 
  Download, Check, X, FileText, Lock, Unlock, MessageSquare
} from 'lucide-react';

interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'restaurant' | 'ngo';
  status: 'active' | 'pending' | 'suspended' | 'rejected' | 'deactivated';
  created_at: string;
}

interface Organization {
  id: number;
  name: string;
  address: string;
  verification_status: 'pending' | 'approved' | 'rejected';
  is_verified: boolean;
  website?: string;
  description?: string;
}

interface OrgDocument {
  id: number;
  organization_id: number;
  doc_type: string;
  file_name: string;
  file_path: string;
  uploaded_at: string;
}

interface Complaint {
  id: number;
  reporter_id: number;
  reporter_name: string;
  reported_user_id?: number;
  reported_user_name?: string;
  donation_id?: number;
  donation_title?: string;
  complaint_type: string;
  description: string;
  status: 'pending' | 'resolved' | 'dismissed';
  resolution_notes?: string;
  created_at: string;
}

interface AuditLog {
  id: number;
  actor_id?: number;
  actor_name?: string;
  action: string;
  target_table?: string;
  target_id?: number;
  timestamp: string;
}

export const AdminPortal: React.FC<{ path: string }> = ({ path }) => {
  
  // Data States
  const [metrics, setMetrics] = useState<any>(null);
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [documents, setDocuments] = useState<OrgDocument[]>([]);
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Complaints Resolution Modal
  const [resolvingComplaint, setResolvingComplaint] = useState<Complaint | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState('');

  // Report download selections
  const [reportType, setReportType] = useState('donations');
  const [reportFormat, setReportFormat] = useState('pdf');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (path === '/admin') {
        const metResp = await api.get('/admin/dashboard/metrics');
        setMetrics(metResp.data);
      } else if (path === '/admin/users') {
        const usersResp = await api.get('/admin/users');
        setUsers(usersResp.data);
      } else if (path === '/admin/verifications') {
        const orgsResp = await api.get('/admin/organizations');
        setOrgs(orgsResp.data);
        const docsResp = await api.get('/admin/documents');
        setDocuments(docsResp.data);
      } else if (path === '/admin/complaints') {
        const compResp = await api.get('/admin/complaints');
        setComplaints(compResp.data);
      } else if (path === '/admin/audit') {
        const auditResp = await api.get('/admin/audit-logs');
        setAuditLogs(auditResp.data);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load administrative console data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    setResolvingComplaint(null);
    setResolutionNotes('');
  }, [path]);

  // Suspend/Reactivate user status
  const handleUserStatusToggle = async (userId: number, currentStatus: string) => {
    setActionLoading(true);
    setError(null);
    setSuccess(null);
    const newStatus = currentStatus === 'suspended' ? 'active' : 'suspended';
    try {
      await api.put(`/admin/users/${userId}/status?status_choice=${newStatus}`);
      setSuccess(`User account status updated to: ${newStatus.toUpperCase()}`);
      const usersResp = await api.get('/admin/users');
      setUsers(usersResp.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Status transition failed.");
    } finally {
      setActionLoading(false);
    }
  };

  // Verify Organization Approve/Reject
  const handleOrgVerification = async (orgId: number, approve: boolean) => {
    setActionLoading(true);
    setError(null);
    setSuccess(null);
    const verifyChoice = approve ? 'approved' : 'rejected';
    try {
      await api.put(`/admin/organizations/${orgId}/verify?status_choice=${verifyChoice}`);
      setSuccess(`Organization status has been verified as: ${verifyChoice.toUpperCase()}`);
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Verification change failed.");
    } finally {
      setActionLoading(false);
    }
  };

  // Submit Complaint Resolution
  const handleResolveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolvingComplaint) return;
    setActionLoading(true);
    setError(null);
    try {
      await api.put(`/admin/complaints/${resolvingComplaint.id}/resolve`, {
        resolution_notes: resolutionNotes,
        status: 'resolved'
      });
      setSuccess("Complaint resolved successfully.");
      setResolvingComplaint(null);
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to resolve complaint.");
    } finally {
      setActionLoading(false);
    }
  };

  // Downloadauthenticated report as a blob
  const handleReportDownload = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await api.get(
        `/admin/reports/download?report_type=${reportType}&report_format=${reportFormat}`,
        { responseType: 'blob' }
      );
      
      const blob = new Blob([response.data], { 
        type: reportFormat === 'pdf' ? 'application/pdf' : 'text/csv' 
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${reportType}_report_${new Date().toISOString().slice(0,10)}.${reportFormat}`);
      document.body.appendChild(link);
      link.click();
      
      setSuccess("Platform report downloaded successfully.");
    } catch (err: any) {
      setError("Failed to generate and download report file.");
    } finally {
      setActionLoading(false);
    }
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
      
      {/* Alert panels */}
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
          VIEW: DASHBOARD METRICS
          ========================================================== */}
      {path === '/admin' && (
        <>
          {/* Quick Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="card-tactile flex items-center gap-4">
              <div className="p-3 bg-brand-green/10 text-brand-green rounded">
                <Users className="w-6 h-6" />
              </div>
              <div className="flex flex-col text-left">
                <span className="text-[10px] text-brand-stone-dark uppercase tracking-wider font-bold">Total Donors</span>
                <span className="text-xl font-bold">{metrics?.restaurants_count || 0} Restaurants</span>
              </div>
            </div>
            <div className="card-tactile flex items-center gap-4">
              <div className="p-3 bg-brand-green/10 text-brand-green rounded">
                <Users className="w-6 h-6" />
              </div>
              <div className="flex flex-col text-left">
                <span className="text-[10px] text-brand-stone-dark uppercase tracking-wider font-bold">Total Recipients</span>
                <span className="text-xl font-bold">{metrics?.ngos_count || 0} NGOs</span>
              </div>
            </div>
            <div className="card-tactile flex items-center gap-4">
              <div className="p-3 bg-brand-amber/10 text-brand-amber rounded">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div className="flex flex-col text-left">
                <span className="text-[10px] text-brand-stone-dark uppercase tracking-wider font-bold">Pending Review</span>
                <span className="text-xl font-bold">{metrics?.pending_orgs || 0} Orgs</span>
              </div>
            </div>
            <div className="card-tactile flex items-center gap-4">
              <div className="p-3 bg-brand-green/10 text-brand-green rounded">
                <Check className="w-6 h-6" />
              </div>
              <div className="flex flex-col text-left">
                <span className="text-[10px] text-brand-stone-dark uppercase tracking-wider font-bold">Total Redistributed</span>
                <span className="text-xl font-bold">{metrics?.total_redistributed || 0} portions</span>
              </div>
            </div>
          </div>

          {/* Graphics Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="card-tactile flex flex-col gap-4 text-left">
              <h3 className="font-display font-bold text-xs uppercase tracking-wider text-brand-stone-dark">Redistribution Volume Timeline</h3>
              <div className="h-64 flex justify-center items-center">
                {metrics?.activity_timeline && metrics.activity_timeline.length > 0 ? (
                  <AreaChart 
                    data={metrics.activity_timeline.map((x: any) => ({ label: x.date, value: x.donations }))} 
                  />
                ) : (
                  <span className="text-xs text-brand-stone-dark">Timeline history not available.</span>
                )}
              </div>
            </div>

            <div className="card-tactile flex flex-col gap-4 text-left">
              <h3 className="font-display font-bold text-xs uppercase tracking-wider text-brand-stone-dark">Redistributed Food by Categories</h3>
              <div className="h-64 flex justify-center items-center">
                {metrics?.categories_distribution && metrics.categories_distribution.length > 0 ? (
                  <DonutChart 
                    data={metrics.categories_distribution.map((x: any) => ({ label: x.category, value: x.count }))} 
                  />
                ) : (
                  <span className="text-xs text-brand-stone-dark">No category data logged.</span>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* ==========================================================
          VIEW: USER MANAGEMENT
          ========================================================== */}
      {path === '/admin/users' && (
        <div className="flex flex-col gap-4 text-left">
          <h2 className="font-display font-bold text-lg">Platform Users Management</h2>
          <div className="card-tactile overflow-x-auto p-0">
            <table className="w-full text-xs font-semibold">
              <thead>
                <tr className="bg-brand-stone border-b border-brand-stone-dark/80 text-brand-stone-dark text-left">
                  <th className="p-4">User ID</th>
                  <th className="p-4">Full Name</th>
                  <th className="p-4">Email</th>
                  <th className="p-4">Role</th>
                  <th className="p-4">Status</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-stone-dark/30 font-medium">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-brand-stone/20">
                    <td className="p-4 font-bold">#{u.id}</td>
                    <td className="p-4 font-bold text-brand-charcoal">{u.full_name}</td>
                    <td className="p-4">{u.email}</td>
                    <td className="p-4 font-semibold uppercase">{u.role}</td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        u.status === 'active' 
                          ? 'bg-brand-green/10 text-brand-green' 
                          : u.status === 'suspended' 
                            ? 'bg-brand-red/10 text-brand-red' 
                            : 'bg-brand-amber/15 text-brand-amber'
                      }`}>
                        {u.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      {u.role !== 'admin' && (
                        <div className="flex justify-end gap-2">
                          {u.status === 'pending' && (
                            <button
                              onClick={() => handleUserStatusToggle(u.id, 'suspended')}
                              disabled={actionLoading}
                              className="btn-tactile-green text-[10px] px-3 py-1 flex items-center gap-1.5"
                            >
                              <Unlock className="w-3 h-3" /> Verify & activate
                            </button>
                          )}
                          {u.status !== 'pending' && (
                            <button
                              onClick={() => handleUserStatusToggle(u.id, u.status)}
                              disabled={actionLoading}
                              className={`btn-tactile-secondary text-[10px] px-3 py-1 flex items-center gap-1.5 ${
                                u.status === 'suspended' ? 'hover:bg-brand-green/15 text-brand-green' : 'hover:bg-brand-red/10 text-brand-red'
                              }`}
                            >
                              {u.status === 'suspended' ? (
                                <><Unlock className="w-3 h-3" /> Reactivate</>
                              ) : (
                                <><Lock className="w-3 h-3" /> Suspend</>
                              )}
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ==========================================================
          VIEW: ORGANIZATIONS VERIFICATION REVIEW
          ========================================================== */}
      {path === '/admin/verifications' && (
        <div className="flex flex-col gap-6 text-left font-sans">
          <h2 className="font-display font-bold text-lg">Partner Organizations Verification Queue</h2>
          
          <div className="grid grid-cols-1 gap-6">
            {orgs.length === 0 ? (
              <div className="card-tactile text-center text-xs text-brand-stone-dark py-12">
                No organizations registered on the platform.
              </div>
            ) : (
              [...orgs].sort((a, b) => Number(a.verification_status !== 'pending') - Number(b.verification_status !== 'pending')).map((org) => {
                const orgDocs = documents.filter(d => d.organization_id === org.id);
                
                return (
                  <div key={org.id} className="card-tactile flex flex-col gap-4">
                    
                    {/* Header Details */}
                    <div className="flex justify-between items-start border-b border-brand-stone/40 pb-3">
                      <div className="flex flex-col gap-0.5 text-left">
                        <div className="flex items-center gap-2">
                          <h3 className="font-display font-bold text-base text-brand-charcoal">{org.name}</h3>
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase ${
                            org.verification_status === 'approved' ? 'bg-brand-green/10 text-brand-green' :
                            org.verification_status === 'rejected' ? 'bg-brand-red/10 text-brand-red' :
                            'bg-brand-amber/15 text-brand-amber'
                          }`}>
                            {org.verification_status}
                          </span>
                        </div>
                        <span className="text-[10px] text-brand-stone-dark">{org.address}</span>
                      </div>
                      
                      <div className="flex gap-2">
                        {org.verification_status === 'pending' && (
                          <>
                            <button
                              onClick={() => handleOrgVerification(org.id, true)}
                              disabled={actionLoading}
                              className="btn-tactile-green text-xs px-3 py-1.5 flex items-center gap-1"
                            >
                              <Check className="w-3.5 h-3.5" /> Approve Partner
                            </button>
                            <button
                              onClick={() => handleOrgVerification(org.id, false)}
                              disabled={actionLoading}
                              className="btn-tactile-red text-xs px-3 py-1.5 flex items-center gap-1"
                            >
                              <X className="w-3.5 h-3.5" /> Reject
                            </button>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Desc and Docs */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-brand-charcoal/80">
                      <div className="flex flex-col gap-2">
                        <strong>Description & mission details:</strong>
                        <p className="leading-relaxed bg-brand-stone/20 rounded p-3 border border-brand-stone-dark/30 font-medium">
                          {org.description || 'No organization profile details provided.'}
                        </p>
                      </div>

                      <div className="flex flex-col gap-2">
                        <strong>Uploaded Verification Documents:</strong>
                        <div className="flex flex-col gap-2">
                          {orgDocs.length === 0 ? (
                            <span className="text-xs text-brand-stone-dark italic font-medium">No documents uploaded.</span>
                          ) : (
                            orgDocs.map((doc) => (
                              <a
                                key={doc.id}
                                href={mediaUrl(doc.file_path)}
                                target="_blank"
                                rel="noreferrer"
                                className="flex items-center justify-between border border-brand-stone-dark rounded p-2.5 bg-brand-stone-light hover:bg-brand-stone/40 transition"
                              >
                                <span className="font-semibold text-brand-charcoal flex items-center gap-2">
                                  <FileText className="w-4 h-4 text-brand-green" />
                                  {doc.doc_type.toUpperCase()} ({doc.file_name})
                                </span>
                                <span className="text-[10px] text-brand-green font-bold uppercase hover:underline">View File</span>
                              </a>
                            ))
                          )}
                        </div>
                      </div>
                    </div>

                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* ==========================================================
          VIEW: SUPPORT COMPLAINTS
          ========================================================== */}
      {path === '/admin/complaints' && (
        <div className="flex flex-col gap-4 text-left font-sans">
          <h2 className="font-display font-bold text-lg">Reported Complaints & Disputes</h2>
          <div className="card-tactile overflow-x-auto p-0">
            <table className="w-full text-xs font-semibold">
              <thead>
                <tr className="bg-brand-stone border-b border-brand-stone-dark/80 text-brand-stone-dark text-left">
                  <th className="p-4">ID</th>
                  <th className="p-4">Reporter</th>
                  <th className="p-4">Category</th>
                  <th className="p-4">Description</th>
                  <th className="p-4">State</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-stone-dark/30 font-medium">
                {complaints.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-brand-stone-dark text-xs">
                      No complaints lodged.
                    </td>
                  </tr>
                ) : (
                  complaints.map((c) => (
                    <tr key={c.id} className="hover:bg-brand-stone/20">
                      <td className="p-4 font-bold">#{c.id}</td>
                      <td className="p-4 font-bold text-brand-charcoal">{c.reporter_name}</td>
                      <td className="p-4 uppercase">{c.complaint_type}</td>
                      <td className="p-4 max-w-sm truncate">{c.description}</td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          c.status === 'resolved' ? 'bg-brand-green/10 text-brand-green' : 'bg-brand-red/10 text-brand-red'
                        }`}>
                          {c.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        {c.status === 'pending' && (
                          <button
                            onClick={() => { setResolvingComplaint(c); setResolutionNotes(''); }}
                            className="btn-tactile text-[10px] px-2.5 py-1 flex items-center gap-1 ml-auto"
                          >
                            <MessageSquare className="w-3.5 h-3.5" /> Resolve Issue
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ==========================================================
          VIEW: SECURITY AUDIT TIMELINE
          ========================================================== */}
      {path === '/admin/audit' && (
        <div className="flex flex-col gap-4 text-left font-sans">
          <h2 className="font-display font-bold text-lg">System Security Audit Trail</h2>
          <div className="card-tactile flex flex-col gap-4 max-h-[500px] overflow-y-auto">
            {auditLogs.length === 0 ? (
              <span className="text-xs text-brand-stone-dark italic font-medium py-12 text-center">No security logs recorded.</span>
            ) : (
              auditLogs.map((log) => (
                <div key={log.id} className="flex gap-4 border-l-2 border-brand-green/30 pl-4 py-1.5 hover:bg-brand-stone/10 transition">
                  <div className="flex-shrink-0 text-[10px] font-bold text-brand-stone-dark mt-0.5">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </div>
                  <div className="flex-grow flex flex-col gap-0.5">
                    <span className="text-xs font-bold text-brand-charcoal">
                      Action: {log.action.replace(/_/g, ' ').toUpperCase()}
                    </span>
                    <span className="text-[10px] text-brand-charcoal/70">
                      Actor: <strong>{log.actor_name || 'System'}</strong> | Target Table: {log.target_table || '-'} | ID: {log.target_id || '-'}
                    </span>
                  </div>
                  <div className="text-[9px] text-brand-stone-dark font-medium self-center">
                    {new Date(log.timestamp).toLocaleDateString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ==========================================================
          VIEW: IMPACT REPORTS DOWNLOADER
          ========================================================== */}
      {path === '/admin/reports' && (
        <div className="max-w-md mx-auto w-full flex flex-col gap-6 text-left font-sans">
          <h2 className="font-display font-bold text-xl border-b border-brand-stone-dark pb-2">
            Compile & Download Platform Impact Reports
          </h2>

          <form onSubmit={handleReportDownload} className="card-tactile flex flex-col gap-5">
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Report Data Type</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value)}
                className="input-tactile text-xs"
              >
                <option value="donations">Donations & Claims Redistribution Volume</option>
                <option value="users">Registered Platform Partners Audit</option>
                <option value="audit">System Security Audit Logs Feed</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Report Format</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-xs font-semibold cursor-pointer">
                  <input
                    type="radio"
                    name="reportFormat"
                    value="pdf"
                    checked={reportFormat === 'pdf'}
                    onChange={() => setReportFormat('pdf')}
                    className="w-4 h-4 text-brand-green"
                  />
                  <span>PDF Document Report</span>
                </label>
                <label className="flex items-center gap-2 text-xs font-semibold cursor-pointer">
                  <input
                    type="radio"
                    name="reportFormat"
                    value="csv"
                    checked={reportFormat === 'csv'}
                    onChange={() => setReportFormat('csv')}
                    className="w-4 h-4 text-brand-green"
                  />
                  <span>CSV Spreadsheet Table</span>
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={actionLoading}
              className="btn-tactile-green py-2.5 text-xs font-semibold flex items-center justify-center gap-2 mt-2"
            >
              <Download className="w-4 h-4" /> 
              <span>{actionLoading ? 'Compiling Report file...' : 'Generate & Download Report'}</span>
            </button>
          </form>
        </div>
      )}

      {/* ==========================================================
          COMPLAINT RESOLUTION DIALOG MODAL
          ========================================================== */}
      {resolvingComplaint && (
        <div className="fixed inset-0 bg-brand-charcoal/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={handleResolveSubmit} className="w-full max-w-md bg-white border border-brand-stone-dark rounded p-6 shadow-xl flex flex-col gap-4 text-left">
            <h3 className="font-display font-bold text-base text-brand-charcoal">
              Resolve Complaint #{resolvingComplaint.id}
            </h3>
            
            <div className="text-xs text-brand-charcoal/70 bg-brand-stone-light p-3 border border-brand-stone-dark rounded flex flex-col gap-1 leading-relaxed">
              <span><strong>Type:</strong> {resolvingComplaint.complaint_type}</span>
              <span><strong>Reporter:</strong> {resolvingComplaint.reporter_name}</span>
              <span><strong>Details:</strong> {resolvingComplaint.description}</span>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">Resolution Notes</label>
              <textarea
                required
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                placeholder="Details of investigation and final resolution decision..."
                rows={4}
                className="input-tactile text-xs"
              />
            </div>

            <div className="flex gap-3 justify-end mt-2">
              <button
                type="submit"
                disabled={actionLoading}
                className="btn-tactile-green text-xs"
              >
                {actionLoading ? 'Resolving...' : 'Confirm Resolution'}
              </button>
              <button
                type="button"
                onClick={() => setResolvingComplaint(null)}
                className="btn-tactile-secondary text-xs"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

    </Layout>
  );
};
