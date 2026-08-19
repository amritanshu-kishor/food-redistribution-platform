import React, { useEffect, useState, useRef } from 'react';
import { Html5QrcodeScanner } from 'html5-qrcode';

interface QRScannerProps {
  onScanSuccess: (code: string) => void;
  onScanError?: (error: any) => void;
  placeholderText?: string;
}

export const QRScanner: React.FC<QRScannerProps> = ({
  onScanSuccess,
  onScanError,
  placeholderText = "Enter secure code manually..."
}) => {
  const [manualCode, setManualCode] = useState('');
  const [scanning, setScanning] = useState(false);
  const scannerRef = useRef<Html5QrcodeScanner | null>(null);

  useEffect(() => {
    if (scanning) {
      // Instantiate the QR reader on the target div
      scannerRef.current = new Html5QrcodeScanner(
        "qr-reader-viewport",
        { 
          fps: 10, 
          qrbox: { width: 220, height: 220 },
          aspectRatio: 1.0 
        },
        /* verbose= */ false
      );

      scannerRef.current.render(
        (decodedText) => {
          onScanSuccess(decodedText);
          stopScanning();
        },
        (error) => {
          if (onScanError) onScanError(error);
        }
      );
    }

    return () => {
      stopScanning();
    };
  }, [scanning]);

  const stopScanning = () => {
    if (scannerRef.current) {
      scannerRef.current.clear().catch((err) => 
        console.error("Html5Qrcode clear failure:", err)
      );
      scannerRef.current = null;
    }
    setScanning(false);
  };

  const handleManualVerify = (e: React.FormEvent) => {
    e.preventDefault();
    if (manualCode.trim()) {
      onScanSuccess(manualCode.trim());
      setManualCode('');
    }
  };

  return (
    <div className="w-full p-6 border border-brand-stone-dark rounded bg-white flex flex-col items-center gap-4">
      {scanning ? (
        <div className="w-full max-w-sm flex flex-col items-center gap-4">
          <div id="qr-reader-viewport" className="w-full border border-brand-stone-dark rounded overflow-hidden"></div>
          <button
            onClick={stopScanning}
            className="btn-tactile-secondary text-xs uppercase tracking-wider w-full"
          >
            Cancel Camera Scan
          </button>
        </div>
      ) : (
        <div className="w-full flex flex-col items-center gap-4">
          {/* Active Camera Scan Button */}
          <button
            onClick={() => setScanning(true)}
            className="btn-tactile-green w-full max-w-xs flex items-center justify-center gap-2 py-3"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h.01M16 12h.01M8 12h.01M12 16h.01M16 16h.01M8 16h.01" />
            </svg>
            Scan QR Code with Camera
          </button>

          {/* Fallback Divider */}
          <div className="flex items-center gap-2 w-full max-w-xs my-1">
            <hr className="flex-grow border-brand-stone-dark/30" />
            <span className="text-[10px] text-brand-stone-dark uppercase tracking-wider font-semibold">Or type code</span>
            <hr className="flex-grow border-brand-stone-dark/30" />
          </div>

          {/* Manual Input Fallback */}
          <form onSubmit={handleManualVerify} className="w-full max-w-xs flex gap-2">
            <input
              type="text"
              value={manualCode}
              onChange={(e) => setManualCode(e.target.value)}
              placeholder={placeholderText}
              className="input-tactile text-sm flex-grow"
            />
            <button
              type="submit"
              disabled={!manualCode.trim()}
              className="btn-tactile text-sm disabled:opacity-50"
            >
              Verify
            </button>
          </form>
        </div>
      )}
    </div>
  );
};
