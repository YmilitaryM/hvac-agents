import { useEffect } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  maxWidth?: string;
  maxHeight?: string;
}

export default function Modal({ open, onClose, title, children, maxWidth = 'max-w-md', maxHeight = '' }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-0 md:p-4" onClick={onClose}>
      <div
        className={`bg-slate-800 border border-slate-700 w-full h-full md:h-auto md:rounded-lg ${maxWidth} ${maxHeight || 'md:max-h-[85vh]'} flex flex-col`}
        onClick={e => e.stopPropagation()}
      >
        {title && (
          <div className="flex items-center justify-between px-4 md:px-6 py-3 md:py-4 border-b border-slate-700 shrink-0">
            <h3 className="text-lg font-bold">{title}</h3>
            <button onClick={onClose} className="text-slate-400 hover:text-white text-xl leading-none">&times;</button>
          </div>
        )}
        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          {children}
        </div>
      </div>
    </div>
  );
}
