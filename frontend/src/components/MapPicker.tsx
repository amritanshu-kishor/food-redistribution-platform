import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix default marker icons broken by webpack
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

interface MapPickerProps {
  latitude: number | '';
  longitude: number | '';
  onLocationChange: (lat: number, lon: number) => void;
}

export const MapPicker: React.FC<MapPickerProps> = ({ latitude, longitude, onLocationChange }) => {
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const defaultLat = typeof latitude === 'number' ? latitude : 20.5937;
    const defaultLon = typeof longitude === 'number' ? longitude : 78.9629;

    const map = L.map(containerRef.current, {
      center: [defaultLat, defaultLon],
      zoom: typeof latitude === 'number' ? 14 : 5,
      zoomControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);

    if (typeof latitude === 'number' && typeof longitude === 'number') {
      const marker = L.marker([latitude, longitude], { draggable: true }).addTo(map);
      marker.on('dragend', () => {
        const pos = marker.getLatLng();
        onLocationChange(Math.round(pos.lat * 100000) / 100000, Math.round(pos.lng * 100000) / 100000);
      });
      markerRef.current = marker;
    }

    map.on('click', (e: L.LeafletMouseEvent) => {
      const { lat, lng } = e.latlng;
      const rounded = { lat: Math.round(lat * 100000) / 100000, lng: Math.round(lng * 100000) / 100000 };
      if (markerRef.current) {
        markerRef.current.setLatLng([rounded.lat, rounded.lng]);
      } else {
        const marker = L.marker([rounded.lat, rounded.lng], { draggable: true }).addTo(map);
        marker.on('dragend', () => {
          const pos = marker.getLatLng();
          onLocationChange(Math.round(pos.lat * 100000) / 100000, Math.round(pos.lng * 100000) / 100000);
        });
        markerRef.current = marker;
      }
      onLocationChange(rounded.lat, rounded.lng);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  }, []);

  // Sync marker when props change externally (e.g. GPS button)
  useEffect(() => {
    if (!mapRef.current) return;
    if (typeof latitude === 'number' && typeof longitude === 'number') {
      if (markerRef.current) {
        markerRef.current.setLatLng([latitude, longitude]);
      } else {
        const marker = L.marker([latitude, longitude], { draggable: true }).addTo(mapRef.current);
        marker.on('dragend', () => {
          const pos = marker.getLatLng();
          onLocationChange(Math.round(pos.lat * 100000) / 100000, Math.round(pos.lng * 100000) / 100000);
        });
        markerRef.current = marker;
      }
      mapRef.current.setView([latitude, longitude], 15);
    }
  }, [latitude, longitude]);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider font-bold text-brand-charcoal/80">
          Pickup Location on Map
        </span>
        <span className="text-[10px] text-brand-stone-dark">
          {typeof latitude === 'number' && typeof longitude === 'number'
            ? `${latitude}, ${longitude}`
            : 'Click map to place pin'}
        </span>
      </div>
      <div
        ref={containerRef}
        className="w-full rounded border border-brand-stone-dark overflow-hidden"
        style={{ height: '280px', zIndex: 1 }}
      />
      <p className="text-[10px] text-brand-stone-dark leading-relaxed">
        Click anywhere on the map to set the pickup pin, or drag the marker to adjust. Use the GPS button above to auto-detect your current location.
      </p>
    </div>
  );
};
