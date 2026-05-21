import { useCallback, useEffect, useRef } from 'react';

interface BottomSheetProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  height?: string;
}

export default function BottomSheet({ open, onClose, title, children, height = '50vh' }: BottomSheetProps) {
  const startYRef = useRef(0);
  const sheetRef = useRef<HTMLDivElement>(null);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    startYRef.current = e.touches[0].clientY;
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    const delta = e.touches[0].clientY - startYRef.current;
    if (delta > 60) {
      onClose();
    }
  }, [onClose]);

  useEffect(() => {
    if (open) {
      const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
      window.addEventListener('keydown', handler);
      return () => window.removeEventListener('keydown', handler);
    }
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={onClose} />
      <div
        ref={sheetRef}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        className="fixed bottom-0 left-0 right-0 z-50 bg-slate-800 border-t border-slate-700 rounded-t-xl md:hidden"
        style={{ maxHeight: height, height }}
      >
        <div className="flex items-center justify-center pt-2 pb-1">
          <div className="w-10 h-1 bg-slate-600 rounded-full" />
        </div>
        {title && (
          <div className="px-4 py-2 border-b border-slate-700">
            <h3 className="text-sm font-semibold text-slate-300">{title}</h3>
          </div>
        )}
        <div className="overflow-y-auto" style={{ maxHeight: `calc(${height} - 3rem)` }}>
          {children}
        </div>
      </div>
    </>
  );
}
