import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix default marker icon broken by webpack bundling
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

interface Donation {
  id: number;
  title: string;
  category: string;
  quantity: number;
  unit: string;
  expires_at: string;
  address: string;
  latitude?: number;
  longitude?: number;
  status: string;
}

interface DonationsMapProps {
  donations: Donation[];
  onClaimClick: (donation: Donation) => void;
}

function getUrgencyColor(expiresAt: string): string {
  const hoursLeft = (new Date(expiresAt).getTime() - Date.now()) / 3600000;
  if (hoursLeft <= 3) return '#ef4444';
  if (hoursLeft <= 6) return '#f59e0b';
  return '#22c55e';
}

export const DonationsMap: React.FC<DonationsMapProps> = ({ donations, onClaimClick }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<L.Marker[]>([]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const withCoords = donations.filter(d => d.latitude && d.longitude);
    const centerLat = withCoords.length > 0 ? withCoords[0].latitude! : 20.5937;
    const centerLon = withCoords.length > 0 ? withCoords[0].longitude! : 78.9629;

    const map = L.map(containerRef.current, {
      center: [centerLat, centerLon],
      zoom: withCoords.length > 0 ? 11 : 5,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current) return;

    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];

    const bounds: [number, number][] = [];

    donations.forEach(donation => {
      if (!donation.latitude || !donation.longitude) return;

      const color = getUrgencyColor(donation.expires_at);
      const hoursLeft = Math.max(
        0,
        Math.round((new Date(donation.expires_at).getTime() - Date.now()) / 3600000 * 10) / 10
      );

      const icon = L.divIcon({
        className: '',
        html: `<div style="background:${color};width:14px;height:14px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);cursor:pointer;"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });

      const marker = L.marker([donation.latitude, donation.longitude], { icon });

      const popupContent = `
        <div style="font-family:system-ui;min-width:200px;padding:4px">
          <div style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;color:#6b7280;margin-bottom:4px">${donation.category}</div>
          <div style="font-size:14px;font-weight:700;color:#111827;margin-bottom:6px;line-height:1.3">${donation.title}</div>
          <div style="font-size:11px;color:#374151;margin-bottom:2px">&#x1F4E6; ${donation.quantity} ${donation.unit}</div>
          <div style="font-size:11px;color:${color};font-weight:600;margin-bottom:8px">&#x23F1; Expires in ${hoursLeft} hrs</div>
          <button
            id="claim-btn-${donation.id}"
            style="background:#16a34a;color:white;border:none;padding:6px 14px;border-radius:4px;font-size:11px;font-weight:700;cursor:pointer;width:100%;"
          >Claim Portions</button>
        </div>
      `;

      const popup = L.popup({ closeButton: true, maxWidth: 240 }).setContent(popupContent);
      marker.bindPopup(popup);

      marker.on('popupopen', () => {
        setTimeout(() => {
          const btn = document.getElementById(`claim-btn-${donation.id}`);
          if (btn) {
            btn.onclick = () => {
              onClaimClick(donation);
              mapRef.current?.closePopup();
            };
          }
        }, 50);
      });

      marker.addTo(mapRef.current!);
      markersRef.current.push(marker);
      bounds.push([donation.latitude, donation.longitude]);
    });

    if (bounds.length > 1) {
      mapRef.current.fitBounds(bounds, { padding: [40, 40] });
    } else if (bounds.length === 1) {
      mapRef.current.setView(bounds[0], 13);
    }
  }, [donations, onClaimClick]);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-4 text-[10px] font-semibold text-brand-charcoal/70">
        <span className="flex items-center gap-1">
          <span style={{ background: '#22c55e' }} className="w-3 h-3 rounded-full inline-block border-2 border-white shadow" />
          &gt; 6 hrs left
        </span>
        <span className="flex items-center gap-1">
          <span style={{ background: '#f59e0b' }} className="w-3 h-3 rounded-full inline-block border-2 border-white shadow" />
          3–6 hrs left
        </span>
        <span className="flex items-center gap-1">
          <span style={{ background: '#ef4444' }} className="w-3 h-3 rounded-full inline-block border-2 border-white shadow" />
          &lt; 3 hrs (urgent)
        </span>
      </div>
      <div
        ref={containerRef}
        className="w-full rounded border border-brand-stone-dark overflow-hidden"
        style={{ height: '480px', zIndex: 1 }}
      />
      <p className="text-[10px] text-brand-stone-dark">
        {donations.filter(d => d.latitude && d.longitude).length} donations shown on map. Click a pin to view details and claim.
      </p>
    </div>
  );
};
